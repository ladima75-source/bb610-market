from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from backend.db import connect
from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import find_master_for_card, source_metadata
from backend.services.product_cards_v3_media import _is_resolvable
from backend.tools_prepare_pcv3_release import _load_db_inventory, _snapshot_tables

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'var' / 'reports'
BACKUP_ROOT = ROOT / 'var' / 'release-backups'
LEGACY_FILES = [
    ROOT / 'data' / 'catalog.master.json',
    ROOT / 'data' / 'product_cards.master.json',
    ROOT / 'data' / 'product-cards.master.json',
]
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.avif', '.svg'}
SELLABLE = {'in_stock', 'preorder', 'backorder'}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _norm(value: Any) -> str:
    s = str(value or '').strip().lower().replace('ё', 'е')
    s = re.sub(r'[^0-9a-zа-яіїєґ]+', ' ', s, flags=re.I)
    return ' '.join(s.split())


def _pack_key(value: Any) -> str:
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
    return _norm(s).replace(' ', '')


def _media_id(path: str) -> str:
    return 'med_recover_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:18]


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return deepcopy(default)


def _iter_dicts(value: Any) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _image_strings(value: Any, out: set[str]) -> None:
    if isinstance(value, str):
        raw = value.split('?', 1)[0].strip()
        if raw and Path(raw).suffix.lower() in IMAGE_EXTS and _is_resolvable(value):
            out.add(value.strip())
    elif isinstance(value, dict):
        for child in value.values():
            _image_strings(child, out)
    elif isinstance(value, list):
        for child in value:
            _image_strings(child, out)


def _record_identity(record: dict) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    names: set[str] = set()
    for key in ('id', 'product_id', 'slug'):
        raw = str(record.get(key) or '').strip().lower()
        if raw:
            ids.add(raw)
    for key in ('name', 'official_name', 'title', 'display_name'):
        val = _norm(record.get(key))
        if val:
            names.add(val)
    v2 = record.get('product_card_v2')
    if isinstance(v2, dict):
        for key in ('name', 'official_name', 'title', 'display_name'):
            val = _norm(v2.get(key))
            if val:
                names.add(val)
    return ids, names


def _legacy_records() -> list[dict]:
    records: list[dict] = []
    seen: set[str] = set()
    for path in LEGACY_FILES:
        if not path.exists():
            continue
        obj = _load(path, None)
        if obj is None:
            continue
        for record in _iter_dicts(obj):
            ids, names = _record_identity(record)
            if not ids and not names:
                continue
            images: set[str] = set()
            _image_strings(record, images)
            if not images:
                continue
            marker = json.dumps({'ids': sorted(ids), 'names': sorted(names), 'images': sorted(images)}, ensure_ascii=False, sort_keys=True)
            if marker in seen:
                continue
            seen.add(marker)
            records.append({'ids': ids, 'names': names, 'images': sorted(images), 'file': path.name})
    return records


def _legacy_candidates(card: dict, commerce_product: str, records: list[dict]) -> list[dict]:
    pid = str(card.get('product_id') or '').strip().lower()
    slug = str(card.get('slug') or '').strip().lower()
    title = _norm((card.get('content') or {}).get('title'))
    ids = {x for x in (pid, slug, commerce_product.strip().lower()) if x}
    names = {x for x in (title,) if x}
    matches: list[dict] = []
    for record in records:
        if ids.intersection(record['ids']) or names.intersection(record['names']):
            matches.append(record)
    return matches


def _path_contains_pack(path: str, pack: str) -> bool:
    key = _pack_key(pack)
    if not key:
        return False
    raw = re.sub(r'[^0-9a-zа-яіїєґ]+', '', path.lower(), flags=re.I)
    return key in raw


def _choose_legacy_image(card: dict, sku: dict, commerce_product: str, records: list[dict]) -> tuple[str, str, list[str]]:
    matches = _legacy_candidates(card, commerce_product, records)
    images: list[str] = []
    for rec in matches:
        for path in rec['images']:
            if path not in images:
                images.append(path)
    if not images:
        return '', 'none', []

    pack = str(sku.get('package') or sku.get('label') or '')
    pack_hits = [x for x in images if _path_contains_pack(x, pack)]
    if len(pack_hits) == 1:
        return pack_hits[0], 'legacy-exact-product+pack', images
    if len(images) == 1:
        return images[0], 'legacy-exact-product-singleton', images
    return '', 'legacy-ambiguous', images


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


def _commerce_state() -> dict[str, dict]:
    with connect() as con:
        return {
            str(r['sku']): dict(r)
            for r in con.execute('SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce').fetchall()
        }


def _effective_price(row: dict | None) -> float | None:
    if not row:
        return None
    value = row.get('sale_price') if row.get('sale_price') is not None else row.get('price')
    return value if isinstance(value, (int, float)) else None


def _backup_cards(stamp: str) -> Path:
    dest = BACKUP_ROOT / f'pcv3-media-readiness-{stamp}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cards.BASE, dest / 'product_cards_v3')
    return dest


def run(*, apply_media: bool) -> dict:
    stamp = _stamp()
    before_db = _snapshot_tables()
    commerce_map_before = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b''
    products, db_skus = _load_db_inventory()
    commerce = _commerce_state()
    cmap = cards.commerce_map()
    map_by_pid = {str(x.get('product_id') or ''): x for x in cmap.get('products', []) if isinstance(x, dict)}
    legacy = _legacy_records()
    backup = _backup_cards(stamp) if apply_media else None

    media_applied = 0
    media_candidates = 0
    ambiguous_media = 0
    changed_cards = 0

    for summary in cards.list_cards():
        pid = str(summary.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            continue
        mapping = map_by_pid.get(pid) or {}
        commerce_product = str(mapping.get('existing_product_key') or '')
        links = {
            str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
            for x in mapping.get('skus') or [] if isinstance(x, dict)
        }
        card_changed = False
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if sku.get('enabled') is False or sku.get('primary_media_id'):
                continue
            sid = str(sku.get('sku_id') or '')
            commerce_key = links.get(sid, '')
            path = ''
            method = ''
            row = db_skus.get(commerce_key) or {}
            direct = str(row.get('image') or '').strip()
            if direct and _is_resolvable(direct):
                path, method = direct, 'commerce-sku-exact'
            else:
                product_image = products.get(commerce_product, {}).get('image')
                if isinstance(product_image, dict):
                    product_image = product_image.get('local') or product_image.get('path') or product_image.get('url')
                product_image = str(product_image or '').strip()
                if product_image and _is_resolvable(product_image):
                    path, method = product_image, 'commerce-product-exact'
                else:
                    path, method, candidates = _choose_legacy_image(card, sku, commerce_product, legacy)
                    if method == 'legacy-ambiguous':
                        ambiguous_media += 1
            if path:
                media_candidates += 1
                if apply_media and _ensure_media(card, sku, path):
                    media_applied += 1
                    card_changed = True
        if card_changed:
            cards.validate(card)
            cards.put(pid, card)
            changed_cards += 1

    after_db = _snapshot_tables()
    if before_db != after_db:
        raise RuntimeError('commerce/database rows changed during media completion')
    commerce_map_after = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b''
    if commerce_map_before != commerce_map_after:
        raise RuntimeError('commerce_map.json changed during media completion')

    rows: list[dict] = []
    product_summary: dict[str, dict] = {}
    photo_total = photo_ok = 0
    price_ok = enabled_ok = sellable_ok = published_ok = release_ready_skus = 0

    products, _ = _load_db_inventory()
    commerce = _commerce_state()
    for summary in cards.list_cards():
        pid = str(summary.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            continue
        content = card.get('content') or {}
        source_verified = bool(source_metadata(find_master_for_card(card)).get('verified'))
        mapping = map_by_pid.get(pid) or {}
        commerce_product = str(mapping.get('existing_product_key') or '')
        product = products.get(commerce_product) or {}
        published = bool(product.get('published', True if commerce_product and commerce_product in products and 'published' not in product else False))
        links = {
            str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
            for x in mapping.get('skus') or [] if isinstance(x, dict)
        }
        media_ids = {
            str(x.get('media_id') or '')
            for x in (card.get('sku_media') or {}).get('media') or [] if isinstance(x, dict)
        }
        ps = {
            'product_id': pid,
            'title': str(content.get('title') or ''),
            'brand': str(content.get('brand') or ''),
            'source_verified': source_verified,
            'published': published,
            'sku_total': 0,
            'sku_with_photo': 0,
            'sku_with_price': 0,
            'sku_sellable': 0,
            'sku_release_ready': 0,
            'blockers': set(),
        }
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if sku.get('enabled') is False:
                continue
            sid = str(sku.get('sku_id') or '')
            key = links.get(sid, '')
            crow = commerce.get(key)
            has_photo = sku.get('primary_media_id') in media_ids
            price = _effective_price(crow)
            has_price = bool(price is not None and price > 0)
            enabled = bool(crow and crow.get('enabled'))
            availability = str((crow or {}).get('availability') or 'unknown')
            sellable = enabled and has_price and availability in SELLABLE
            ready = source_verified and has_photo and published and sellable
            blockers = []
            if not source_verified:
                blockers.append('source')
            if not has_photo:
                blockers.append('photo')
            if not has_price:
                blockers.append('price')
            if not enabled:
                blockers.append('disabled')
            if availability not in SELLABLE:
                blockers.append('availability')
            if not published:
                blockers.append('publication')
            rows.append({
                'product_id': pid,
                'title': str(content.get('title') or ''),
                'brand': str(content.get('brand') or ''),
                'sku_id': sid,
                'sku_code': str(sku.get('sku_code') or ''),
                'package': str(sku.get('package') or sku.get('label') or ''),
                'commerce_product': commerce_product,
                'commerce_sku': key,
                'source_verified': source_verified,
                'photo': has_photo,
                'price': price,
                'enabled': enabled,
                'availability': availability,
                'published': published,
                'release_ready': ready,
                'blockers': ','.join(blockers),
            })
            photo_total += 1
            photo_ok += int(has_photo)
            price_ok += int(has_price)
            enabled_ok += int(enabled)
            sellable_ok += int(sellable)
            published_ok += int(published)
            release_ready_skus += int(ready)
            ps['sku_total'] += 1
            ps['sku_with_photo'] += int(has_photo)
            ps['sku_with_price'] += int(has_price)
            ps['sku_sellable'] += int(sellable)
            ps['sku_release_ready'] += int(ready)
            ps['blockers'].update(blockers)
        product_summary[pid] = ps

    product_rows = []
    for ps in product_summary.values():
        product_rows.append({**ps, 'blockers': ','.join(sorted(ps['blockers']))})

    report = {
        'schema_version': '1.0',
        'timestamp_utc': stamp,
        'mode': 'APPLY_MEDIA_SAFE' if apply_media else 'DRY_RUN',
        'commerce_unchanged': True,
        'media_candidates': media_candidates,
        'media_applied': media_applied,
        'ambiguous_media': ambiguous_media,
        'changed_cards': changed_cards,
        'backup_dir': str(backup) if backup else '',
        'summary': {
            'products': len(product_rows),
            'sku_total': photo_total,
            'sku_with_photo': photo_ok,
            'photo_remainder': photo_total - photo_ok,
            'sku_with_price': price_ok,
            'sku_enabled': enabled_ok,
            'sku_sellable': sellable_ok,
            'sku_published_product': published_ok,
            'sku_release_ready': release_ready_skus,
            'products_release_ready': sum(1 for x in product_rows if x['sku_total'] and x['sku_release_ready'] == x['sku_total']),
            'products_with_any_ready_sku': sum(1 for x in product_rows if x['sku_release_ready'] > 0),
            'products_needing_photo': sum(1 for x in product_rows if x['sku_with_photo'] < x['sku_total']),
            'products_needing_price': sum(1 for x in product_rows if x['sku_with_price'] < x['sku_total']),
        },
        'products': product_rows,
        'skus': rows,
    }

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_ROOT / f'pcv3-media-readiness-{stamp}.json'
    csv_path = REPORT_ROOT / f'pcv3-media-readiness-{stamp}.csv'
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fields = ['product_id','title','brand','sku_id','sku_code','package','commerce_product','commerce_sku','source_verified','photo','price','enabled','availability','published','release_ready','blockers']
    with csv_path.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    report['json_report'] = str(json_path)
    report['csv_report'] = str(csv_path)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description='Exact-media recovery + commerce readiness audit for all Product Card v3 SKU.')
    ap.add_argument('--apply-safe-media', action='store_true', help='Apply only exact/resolvable existing media. Never changes commerce, prices, stock, publication or SKU enablement.')
    args = ap.parse_args()
    r = run(apply_media=args.apply_safe_media)
    s = r['summary']
    print('BB610 PCV3 MEDIA + COMMERCE READINESS')
    print('MODE:', r['mode'])
    print('MEDIA CANDIDATES:', r['media_candidates'])
    print('MEDIA APPLIED:', r['media_applied'])
    print('AMBIGUOUS MEDIA LEFT FOR REVIEW:', r['ambiguous_media'])
    print('COMMERCE WRITES: 0')
    print('COMMERCE UNCHANGED:', 'PASS' if r['commerce_unchanged'] else 'FAIL')
    print('PRODUCTS:', s['products'])
    print('SKU TOTAL:', s['sku_total'])
    print('PHOTO COVERAGE:', f"{s['sku_with_photo']}/{s['sku_total']}")
    print('PHOTO REMAINDER:', s['photo_remainder'])
    print('SKU WITH PRICE:', f"{s['sku_with_price']}/{s['sku_total']}")
    print('SKU SELLABLE:', f"{s['sku_sellable']}/{s['sku_total']}")
    print('SKU RELEASE READY:', f"{s['sku_release_ready']}/{s['sku_total']}")
    print('PRODUCTS FULLY RELEASE READY:', f"{s['products_release_ready']}/{s['products']}")
    print('PRODUCTS WITH ANY READY SKU:', f"{s['products_with_any_ready_sku']}/{s['products']}")
    print('PRODUCTS NEEDING PHOTO:', s['products_needing_photo'])
    print('PRODUCTS NEEDING PRICE:', s['products_needing_price'])
    print('JSON REPORT:', r['json_report'])
    print('CSV REPORT:', r['csv_report'])
    if r['backup_dir']:
        print('BACKUP:', r['backup_dir'])
    print('RESULT: PASS')


if __name__ == '__main__':
    main()
