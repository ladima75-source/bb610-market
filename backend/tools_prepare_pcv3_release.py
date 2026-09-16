from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db import DB_PATH, connect
from backend.catalog_provider import load_catalog
from backend.services import product_cards_v3 as cards
from backend.services.catalog_cms import create_product
from backend.services.product_cards_v3_master import find_master_for_card, source_metadata
from backend.services.product_cards_v3_media import _is_resolvable

ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = ROOT / 'var' / 'release-backups'
REPORT_ROOT = ROOT / 'var' / 'reports'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _norm(value: Any) -> str:
    s = str(value or '').strip().lower().replace('ё', 'е')
    s = re.sub(r'[^0-9a-zа-яіїєґ+.-]+', ' ', s, flags=re.I)
    return ' '.join(s.split())


def _pack_key(value: Any) -> str:
    if isinstance(value, dict):
        if value.get('value') is not None and value.get('unit'):
            return _pack_key(f"{value.get('value')} {value.get('unit')}")
        return ''
    s = str(value or '').strip().lower().replace(',', '.').replace('*', '')
    s = re.sub(r'\s+', ' ', s)
    for pat, unit in (
        (r'(\d+(?:\.\d+)?)\s*(?:мл|ml)\b', 'ml'),
        (r'(\d+(?:\.\d+)?)\s*(?:кг|kg)\b', 'kg'),
        (r'(\d+(?:\.\d+)?)\s*(?:г|g)\b', 'g'),
        (r'(\d+(?:\.\d+)?)\s*(?:л|l)\b', 'l'),
        (r'(\d+(?:\.\d+)?)\s*(?:шт|pcs?|pieces?)\b', 'pcs'),
    ):
        m = re.search(pat, s, flags=re.I)
        if m:
            num = m.group(1)
            if num.endswith('.0'):
                num = num[:-2]
            return f'{num}{unit}'
    return _norm(s)


def _volume(value: Any) -> tuple[float | None, str]:
    key = _pack_key(value)
    m = re.fullmatch(r'(\d+(?:\.\d+)?)(ml|kg|g|l|pcs)', key)
    if not m:
        return None, 'pcs'
    return float(m.group(1)), m.group(2)


def _image_path(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get('local') or value.get('path') or value.get('url')
    return str(value or '').strip()


def _media_id(path: str) -> str:
    return 'med_release_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:18]


def _technical_sku(product_id: str, sku_id: str) -> str:
    token = hashlib.sha1(f'{product_id}|{sku_id}'.encode('utf-8')).hexdigest()[:14].upper()
    return f'BB610-{token}'


def _load_db_inventory() -> tuple[dict[str, dict], dict[str, dict]]:
    data = load_catalog()
    products: dict[str, dict] = {}
    skus: dict[str, dict] = {}

    for p in data.get('products', []) or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get('id') or '').strip()
        if pid:
            products[pid] = deepcopy(p)

    for s in data.get('skus', []) or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get('id') or s.get('sku') or '').strip()
        if sid:
            skus[sid] = deepcopy(s)

    with connect() as con:
        for row in con.execute('SELECT product_id,slug,content_json,published,created_at,updated_at FROM product_content').fetchall():
            pid = str(row['product_id'])
            try:
                content = json.loads(row['content_json'] or '{}')
            except Exception:
                content = {}
            merged = deepcopy(products.get(pid, {}))
            if isinstance(content, dict):
                merged.update(content)
            merged['id'] = pid
            merged['slug'] = row['slug'] or merged.get('slug') or pid
            merged['published'] = bool(row['published'])
            products[pid] = merged

        for row in con.execute('SELECT sku,product_id,variant,volume_value,volume_unit,image,currency,created_at,updated_at FROM dynamic_skus').fetchall():
            sid = str(row['sku'])
            skus[sid] = {
                'id': sid,
                'sku': sid,
                'product_id': row['product_id'],
                'variant': row['variant'],
                'volume_weight': {'value': row['volume_value'], 'unit': row['volume_unit']} if row['volume_value'] is not None else None,
                'image': row['image'],
                'currency': row['currency'],
                'runtime_dynamic': True,
            }
    return products, skus


def _product_indexes(products: dict[str, dict]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    by_slug: dict[str, list[str]] = {}
    by_name: dict[str, list[str]] = {}
    for pid, p in products.items():
        for raw in (pid, p.get('slug')):
            key = str(raw or '').strip().lower()
            if key:
                by_slug.setdefault(key, []).append(pid)
        for raw in (p.get('name'), p.get('official_name'), p.get('title')):
            key = _norm(raw)
            if key:
                by_name.setdefault(key, []).append(pid)
    return by_slug, by_name


def _sku_rows_for_product(skus: dict[str, dict], product_id: str) -> list[dict]:
    return [row for row in skus.values() if str(row.get('product_id') or '') == product_id]


def _sku_pack(row: dict) -> str:
    for value in (row.get('variant'), row.get('package'), row.get('label'), row.get('volume_weight')):
        key = _pack_key(value)
        if key:
            return key
    return ''


def _resolve_product(card: dict, products: dict[str, dict], by_slug: dict[str, list[str]], by_name: dict[str, list[str]]) -> tuple[str, str]:
    slug = str(card.get('slug') or '').strip().lower()
    content = card.get('content') or {}
    title = _norm(content.get('title'))

    slug_hits = list(dict.fromkeys(by_slug.get(slug, []))) if slug else []
    if len(slug_hits) == 1:
        return slug_hits[0], 'existing-exact-slug'
    if len(slug_hits) > 1:
        raise RuntimeError(f'{card.get("product_id")}: ambiguous commerce product slug {slug}: {slug_hits}')

    title_hits = list(dict.fromkeys(by_name.get(title, []))) if title else []
    if len(title_hits) == 1:
        return title_hits[0], 'existing-exact-title'
    if len(title_hits) > 1:
        raise RuntimeError(f'{card.get("product_id")}: ambiguous commerce product title {content.get("title")}: {title_hits}')

    if not slug:
        raise RuntimeError(f'{card.get("product_id")}: cannot create commerce draft without slug')
    if slug in products:
        raise RuntimeError(f'{card.get("product_id")}: commerce product id collision for {slug}')
    return slug, 'create-draft-product'


def _snapshot_tables() -> dict[str, dict[str, str]]:
    specs = {
        'product_content': 'product_id',
        'dynamic_skus': 'sku',
        'sku_commerce': 'sku',
    }
    out: dict[str, dict[str, str]] = {}
    with connect() as con:
        for table, key in specs.items():
            rows = con.execute(f'SELECT * FROM {table}').fetchall()
            table_map: dict[str, str] = {}
            for row in rows:
                obj = dict(row)
                table_map[str(obj.get(key))] = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            out[table] = table_map
    return out


def _assert_preexisting_unchanged(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> None:
    for table, rows in before.items():
        current = after.get(table, {})
        for key, value in rows.items():
            if current.get(key) != value:
                raise RuntimeError(f'pre-existing commerce row changed: {table}/{key}')


def _backup_db(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(DB_PATH))
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def build_plan() -> dict:
    products, commerce_skus = _load_db_inventory()
    by_slug, by_name = _product_indexes(products)
    cmap = cards.commerce_map()
    mappings = {str(x.get('product_id') or ''): deepcopy(x) for x in cmap.get('products', []) if isinstance(x, dict)}
    used_sku_keys = set(commerce_skus)
    planned_sku_keys: set[str] = set()
    plan_items: list[dict] = []
    failures: list[str] = []

    full_cards: list[dict] = []
    for summary in cards.list_cards():
        card = cards.get(str(summary.get('product_id') or ''))
        if isinstance(card, dict):
            full_cards.append(card)

    for card in full_cards:
        pid = str(card.get('product_id') or '')
        source = source_metadata(find_master_for_card(card))
        if not source.get('verified'):
            failures.append(f'{pid}: MASTER source not verified')
            continue

        mapping = mappings.get(pid)
        if mapping:
            commerce_product = str(mapping.get('existing_product_key') or '').strip()
            if not commerce_product:
                failures.append(f'{pid}: mapping has empty existing_product_key')
                continue
            product_action = 'keep-mapped-product'
        else:
            try:
                commerce_product, product_action = _resolve_product(card, products, by_slug, by_name)
            except Exception as exc:
                failures.append(str(exc))
                continue

        existing_rows = _sku_rows_for_product(commerce_skus, commerce_product)
        pack_index: dict[str, list[str]] = {}
        for row in existing_rows:
            key = _sku_pack(row)
            sid = str(row.get('id') or row.get('sku') or '').strip()
            if key and sid:
                pack_index.setdefault(key, []).append(sid)

        current_links = {}
        if mapping:
            for link in mapping.get('skus') or []:
                if isinstance(link, dict) and link.get('sku_id') and link.get('existing_commerce_sku_key'):
                    current_links[str(link['sku_id'])] = str(link['existing_commerce_sku_key'])

        sku_plans: list[dict] = []
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if sku.get('enabled') is False:
                continue
            sku_id = str(sku.get('sku_id') or '')
            package = str(sku.get('package') or sku.get('label') or '').strip()
            key = _pack_key(package)
            linked = current_links.get(sku_id)
            code = str(sku.get('sku_code') or '').strip()

            if linked and linked in commerce_skus and str(commerce_skus[linked].get('product_id') or '') == commerce_product:
                commerce_key, action = linked, 'keep-link'
            elif code and code in commerce_skus and str(commerce_skus[code].get('product_id') or '') == commerce_product:
                commerce_key, action = code, 'bind-existing-code'
            else:
                hits = list(dict.fromkeys(pack_index.get(key, []))) if key else []
                if len(hits) == 1:
                    commerce_key, action = hits[0], 'bind-exact-pack'
                elif len(hits) > 1:
                    failures.append(f'{pid}/{sku_id}: ambiguous exact package {package}: {hits}')
                    continue
                else:
                    commerce_key = code if code and code not in used_sku_keys and code not in planned_sku_keys else _technical_sku(pid, sku_id)
                    if commerce_key in used_sku_keys or commerce_key in planned_sku_keys:
                        failures.append(f'{pid}/{sku_id}: planned SKU collision {commerce_key}')
                        continue
                    action = 'create-draft-sku'
                    planned_sku_keys.add(commerce_key)

            source_row = commerce_skus.get(commerce_key, {})
            image = _image_path(source_row.get('image'))
            sku_plans.append({
                'sku_id': sku_id,
                'package': package,
                'commerce_key': commerce_key,
                'action': action,
                'image': image,
            })

        plan_items.append({
            'product_id': pid,
            'slug': card.get('slug'),
            'title': (card.get('content') or {}).get('title') or '',
            'product_action': product_action,
            'commerce_product': commerce_product,
            'product_image': _image_path(products.get(commerce_product, {}).get('image')),
            'sku_plans': sku_plans,
        })

    if failures:
        raise RuntimeError('release plan preflight failed:\n' + '\n'.join(failures[:100]))

    return {
        'cards': full_cards,
        'items': plan_items,
        'products': products,
        'commerce_skus': commerce_skus,
        'commerce_map': cmap,
    }


def _insert_draft_sku(product_id: str, sku_key: str, package: str) -> None:
    volume_value, volume_unit = _volume(package)
    now = _now()
    with connect() as con:
        if con.execute('SELECT 1 FROM dynamic_skus WHERE sku=?', (sku_key,)).fetchone():
            return
        con.execute(
            'INSERT INTO dynamic_skus(sku,product_id,variant,volume_value,volume_unit,image,currency,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (sku_key, product_id, package or '1 шт', volume_value, volume_unit, None, 'UAH', now, now),
        )
        con.execute(
            'INSERT OR IGNORE INTO sku_commerce(sku,price,sale_price,availability,stock_qty,enabled,updated_at) VALUES(?,?,?,?,?,?,?)',
            (sku_key, None, None, 'unknown', None, 0, now),
        )
        con.commit()


def _ensure_media(card: dict, sku: dict, path: str) -> bool:
    if sku.get('primary_media_id') or not path or not _is_resolvable(path):
        return False
    sm = card.get('sku_media') or {}
    media = sm.setdefault('media', [])
    by_path = {str(x.get('path') or ''): x for x in media if isinstance(x, dict)}
    entry = by_path.get(path)
    if not entry:
        entry = {
            'media_id': _media_id(path),
            'path': path,
            'alt': f"{(card.get('content') or {}).get('title') or ''} {sku.get('package') or ''}".strip(),
            'kind': 'product',
            'sort_order': len(media),
        }
        media.append(entry)
    sku['primary_media_id'] = entry['media_id']
    return True


def apply_plan(plan: dict) -> dict:
    stamp = _stamp()
    backup_dir = BACKUP_ROOT / f'pcv3-release-prep-{stamp}'
    backup_dir.mkdir(parents=True, exist_ok=True)
    _backup_db(backup_dir / 'bb610-orders.sqlite3')
    shutil.copytree(cards.BASE, backup_dir / 'product_cards_v3')

    before_db = _snapshot_tables()
    cmap = deepcopy(plan['commerce_map'])
    cmap.setdefault('schema_version', '1.0')
    cmap.setdefault('products', [])
    mapping_by_pid = {str(x.get('product_id') or ''): x for x in cmap['products'] if isinstance(x, dict)}

    created_products = 0
    created_skus = 0
    added_bindings = 0
    filled_sku_codes = 0
    filled_primary_media = 0
    changed_cards = 0

    for item in plan['items']:
        pid = item['product_id']
        card = cards.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f'{pid}: card disappeared before apply')
        content = card.get('content') or {}
        commerce_product = item['commerce_product']

        if item['product_action'] == 'create-draft-product':
            created = create_product({
                'id': commerce_product,
                'slug': commerce_product,
                'name': content.get('title') or commerce_product,
                'brand': content.get('brand') or '',
                'category_id': content.get('category') or 'other',
                'short_description': content.get('short_description') or '',
                'published': False,
            })
            if not created:
                raise RuntimeError(f'{pid}: failed to create draft commerce product {commerce_product}')
            created_products += 1

        mapping = mapping_by_pid.get(pid)
        if not mapping:
            mapping = {'product_id': pid, 'existing_product_key': commerce_product, 'skus': []}
            cmap['products'].append(mapping)
            mapping_by_pid[pid] = mapping
        elif str(mapping.get('existing_product_key') or '') != commerce_product:
            raise RuntimeError(f'{pid}: commerce product changed during apply')

        links = {str(x.get('sku_id') or ''): x for x in mapping.get('skus') or [] if isinstance(x, dict)}
        card_changed = False
        v3_by_id = {
            str(x.get('sku_id') or ''): x
            for x in (card.get('sku_media') or {}).get('skus') or []
            if isinstance(x, dict)
        }

        for sp in item['sku_plans']:
            sku_id = sp['sku_id']
            commerce_key = sp['commerce_key']
            if sp['action'] == 'create-draft-sku':
                _insert_draft_sku(commerce_product, commerce_key, sp['package'])
                created_skus += 1

            link = links.get(sku_id)
            if not link:
                mapping.setdefault('skus', []).append({'sku_id': sku_id, 'existing_commerce_sku_key': commerce_key})
                links[sku_id] = mapping['skus'][-1]
                added_bindings += 1
            elif str(link.get('existing_commerce_sku_key') or '') != commerce_key:
                raise RuntimeError(f'{pid}/{sku_id}: existing commerce link conflict')

            v3sku = v3_by_id.get(sku_id)
            if not v3sku:
                raise RuntimeError(f'{pid}/{sku_id}: v3 SKU missing during apply')
            if not str(v3sku.get('sku_code') or '').strip():
                v3sku['sku_code'] = commerce_key
                filled_sku_codes += 1
                card_changed = True

            image = sp.get('image') or item.get('product_image') or ''
            if _ensure_media(card, v3sku, image):
                filled_primary_media += 1
                card_changed = True

        cards.validate(card)
        if card_changed:
            cards.put(pid, card)
            changed_cards += 1

    _save_json(cards.COMMERCE_MAP, cmap)

    after_db = _snapshot_tables()
    _assert_preexisting_unchanged(before_db, after_db)

    unsafe_drafts: list[str] = []
    with connect() as con:
        for item in plan['items']:
            if item['product_action'] == 'create-draft-product':
                row = con.execute('SELECT published FROM product_content WHERE product_id=?', (item['commerce_product'],)).fetchone()
                if not row or bool(row['published']):
                    unsafe_drafts.append(f"published product {item['commerce_product']}")
            for sp in item['sku_plans']:
                if sp['action'] != 'create-draft-sku':
                    continue
                row = con.execute('SELECT price,sale_price,availability,stock_qty,enabled FROM sku_commerce WHERE sku=?', (sp['commerce_key'],)).fetchone()
                if not row or row['price'] is not None or row['sale_price'] is not None or row['stock_qty'] is not None or row['availability'] != 'unknown' or bool(row['enabled']):
                    unsafe_drafts.append(f"unsafe SKU {sp['commerce_key']}")
    if unsafe_drafts:
        raise RuntimeError('unsafe draft commerce state: ' + ', '.join(unsafe_drafts[:20]))

    return {
        'timestamp_utc': stamp,
        'backup_dir': str(backup_dir),
        'created_draft_products': created_products,
        'created_draft_skus': created_skus,
        'added_sku_bindings': added_bindings,
        'filled_v3_sku_codes': filled_sku_codes,
        'filled_primary_media': filled_primary_media,
        'changed_v3_cards': changed_cards,
        'preexisting_commerce_unchanged': True,
        'new_drafts_safe': True,
    }


def audit() -> dict:
    total = mapped = sku_total = sku_bound = photo_total = published = priced_products = sellable_products = 0
    cmap = cards.commerce_map()
    map_by_pid = {str(x.get('product_id') or ''): x for x in cmap.get('products', []) if isinstance(x, dict)}

    products, _ = _load_db_inventory()
    with connect() as con:
        commerce_rows = {
            str(r['sku']): dict(r)
            for r in con.execute('SELECT sku,price,sale_price,availability,stock_qty,enabled FROM sku_commerce').fetchall()
        }

    for summary in cards.list_cards():
        card = cards.get(str(summary.get('product_id') or ''))
        if not isinstance(card, dict):
            continue
        total += 1
        mapping = map_by_pid.get(str(card.get('product_id') or ''))
        if mapping:
            mapped += 1
        links = {
            str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
            for x in (mapping or {}).get('skus') or [] if isinstance(x, dict)
        }
        enabled_skus = [x for x in (card.get('sku_media') or {}).get('skus') or [] if x.get('enabled') is not False]
        media_ids = {str(x.get('media_id') or '') for x in (card.get('sku_media') or {}).get('media') or [] if isinstance(x, dict)}
        sku_total += len(enabled_skus)
        sku_bound += sum(1 for x in enabled_skus if links.get(str(x.get('sku_id') or '')))
        photo_total += sum(1 for x in enabled_skus if x.get('primary_media_id') in media_ids)

        commerce_product = str((mapping or {}).get('existing_product_key') or '')
        product = products.get(commerce_product) or {}
        if mapping and bool(product.get('published', True if commerce_product in products and 'published' not in product else False)):
            published += 1

        rows = [commerce_rows.get(key) for key in links.values()]
        rows = [x for x in rows if x]
        if any((r.get('sale_price') if r.get('sale_price') is not None else r.get('price')) not in (None, 0) for r in rows):
            priced_products += 1
        if any(
            bool(r.get('enabled')) and
            (r.get('sale_price') if r.get('sale_price') is not None else r.get('price')) not in (None, 0) and
            r.get('availability') in {'in_stock', 'preorder', 'backorder'}
            for r in rows
        ):
            sellable_products += 1

    return {
        'total_cards': total,
        'mapped_products': mapped,
        'enabled_v3_skus': sku_total,
        'bound_v3_skus': sku_bound,
        'sku_with_primary_photo': photo_total,
        'published_products': published,
        'products_with_price': priced_products,
        'sellable_products': sellable_products,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description='Prepare PCV3 release structure safely: exact commerce bindings, disabled drafts and exact inherited media.')
    ap.add_argument('--apply-safe', action='store_true', help='Apply only reversible structural changes. Never publishes/enables/sets price or stock.')
    args = ap.parse_args()

    plan = build_plan()
    planned_products = sum(1 for x in plan['items'] if x['product_action'] == 'create-draft-product')
    planned_skus = sum(1 for x in plan['items'] for s in x['sku_plans'] if s['action'] == 'create-draft-sku')
    planned_bindings = sum(1 for x in plan['items'] for s in x['sku_plans'] if s['action'] != 'keep-link')
    before = audit()

    result = None
    if args.apply_safe:
        result = apply_plan(plan)
    after = audit()

    report = {
        'schema_version': '1.0',
        'mode': 'APPLY_SAFE' if args.apply_safe else 'DRY_RUN',
        'planned_draft_products': planned_products,
        'planned_draft_skus': planned_skus,
        'planned_binding_changes': planned_bindings,
        'before': before,
        'after': after,
        'apply': result,
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_ROOT / f'pcv3-release-prep-{_stamp()}.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('BB610 PCV3 RELEASE PREP')
    print('MODE:', report['mode'])
    print('PLAN DRAFT PRODUCTS:', planned_products)
    print('PLAN DRAFT SKU:', planned_skus)
    print('PLAN BINDINGS:', planned_bindings)
    if result:
        print('CREATED DRAFT PRODUCTS:', result['created_draft_products'])
        print('CREATED DRAFT SKU:', result['created_draft_skus'])
        print('ADDED SKU BINDINGS:', result['added_sku_bindings'])
        print('FILLED V3 SKU CODES:', result['filled_v3_sku_codes'])
        print('FILLED PRIMARY MEDIA:', result['filled_primary_media'])
        print('PREEXISTING COMMERCE UNCHANGED:', 'PASS' if result['preexisting_commerce_unchanged'] else 'FAIL')
        print('NEW DRAFTS SAFE:', 'PASS' if result['new_drafts_safe'] else 'FAIL')
        print('BACKUP:', result['backup_dir'])
    print('COVERAGE PRODUCTS:', f"{after['mapped_products']}/{after['total_cards']}")
    print('COVERAGE SKU BINDINGS:', f"{after['bound_v3_skus']}/{after['enabled_v3_skus']}")
    print('PHOTO COVERAGE:', f"{after['sku_with_primary_photo']}/{after['enabled_v3_skus']}")
    print('PUBLISHED PRODUCTS:', after['published_products'])
    print('PRODUCTS WITH PRICE:', after['products_with_price'])
    print('SELLABLE PRODUCTS:', after['sellable_products'])
    print('REPORT:', report_path)


if __name__ == '__main__':
    main()
