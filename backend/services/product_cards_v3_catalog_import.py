from __future__ import annotations

import csv
import io
import json
import re
import shutil
import sqlite3
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from ..db import DB_PATH, connect
from . import catalog_cms
from . import product_cards_v3 as pcv3
from . import product_cards_v3_import as cards_import
from .catalog_import_xlsx import write_xlsx

ROOT = Path(__file__).resolve().parents[2]
VAR = ROOT / 'var' / 'product-card-v3-catalog-import'
SESSIONS = VAR / 'sessions'
BACKUPS = VAR / 'backups'
HISTORY_FILE = VAR / 'history.json'
CATALOG_MASTER = ROOT / 'data' / 'catalog.master.json'
for _p in (SESSIONS, BACKUPS):
    _p.mkdir(parents=True, exist_ok=True)

COMMERCE_HEADERS = [
    'commerce_product_key', 'commerce_sku_key', 'price', 'sale_price',
    'availability', 'stock_qty', 'sale_enabled'
]
HEADERS = [*cards_import.HEADERS, *COMMERCE_HEADERS]
VALID_AVAILABILITY = {'unknown', 'in_stock', 'out_of_stock', 'preorder', 'backorder'}
TRUE_VALUES = {'1', 'true', 'yes', 'on', 'так', 'y'}
FALSE_VALUES = {'0', 'false', 'no', 'off', 'ні', 'нет', 'n'}
CLEAR_VALUES = {'__clear__', 'clear', 'null', 'none'}


def _txt(value: Any) -> str:
    return '' if value is None else str(value).strip()


def _bool(value: Any) -> bool:
    raw = _txt(value).lower()
    if raw in TRUE_VALUES:
        return True
    if raw in FALSE_VALUES:
        return False
    raise ValueError(f'Невідоме boolean значення: {value}')


def _float(value: Any) -> float:
    raw = _txt(value).replace(',', '.')
    try:
        out = float(raw)
    except Exception as exc:
        raise ValueError(f'Некоректне число: {value}') from exc
    if out < 0:
        raise ValueError('Значення не може бути від’ємним')
    return out


def _int(value: Any) -> int:
    number = _float(value)
    if int(number) != number:
        raise ValueError('Залишок має бути цілим числом')
    return int(number)


def _csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=HEADERS, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, '') for key in HEADERS})
    return ('\ufeff' + buf.getvalue()).encode('utf-8')


def _mapping_doc() -> dict:
    doc = pcv3.commerce_map()
    if not isinstance(doc, dict):
        doc = {}
    out = deepcopy(doc)
    out.setdefault('schema_version', '1.0')
    if not isinstance(out.get('products'), list):
        out['products'] = []
    return out


def _mapping_index(doc: dict) -> tuple[dict[str, dict], dict[tuple[str, str], str]]:
    products: dict[str, dict] = {}
    skus: dict[tuple[str, str], str] = {}
    for item in doc.get('products') or []:
        if not isinstance(item, dict):
            continue
        pid = _txt(item.get('product_id'))
        if not pid:
            continue
        products[pid] = item
        for link in item.get('skus') or []:
            if not isinstance(link, dict):
                continue
            sid = _txt(link.get('sku_id'))
            ckey = _txt(link.get('existing_commerce_sku_key'))
            if sid and ckey:
                skus[(pid, sid)] = ckey
    return products, skus


def _save_mapping(doc: dict) -> None:
    path = pcv3.COMMERCE_MAP
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def _upsert_mapping(doc: dict, product_id: str, product_key: str, sku_id: str, sku_key: str) -> None:
    row = next((x for x in doc.get('products') or [] if isinstance(x, dict) and x.get('product_id') == product_id), None)
    if row is None:
        row = {'product_id': product_id, 'existing_product_key': product_key, 'skus': []}
        doc.setdefault('products', []).append(row)
    if product_key:
        row['existing_product_key'] = product_key
    if not isinstance(row.get('skus'), list):
        row['skus'] = []
    link = next((x for x in row['skus'] if isinstance(x, dict) and x.get('sku_id') == sku_id), None)
    if link is None:
        link = {'sku_id': sku_id, 'existing_commerce_sku_key': sku_key}
        row['skus'].append(link)
    elif sku_key:
        link['existing_commerce_sku_key'] = sku_key


def _commerce_product_key_from_slug(slug: str) -> str:
    key = re.sub(r'[^a-z0-9-]+', '-', _txt(slug).lower()).strip('-')
    return re.sub(r'-+', '-', key)[:120] or ('import-' + uuid.uuid4().hex[:10])


def _commerce_sku_key(sku_code: str, sku_id: str) -> str:
    candidate = _txt(sku_code).upper()
    if re.fullmatch(r'[A-Z0-9._-]{3,128}', candidate):
        return candidate
    candidate = _txt(sku_id).upper()
    if re.fullmatch(r'[A-Z0-9._-]{3,128}', candidate):
        return candidate
    return 'IMP-' + uuid.uuid4().hex[:16].upper()


def _catalog_state() -> tuple[set[str], dict[str, str], dict[str, dict]]:
    product_ids: set[str] = set()
    sku_owner: dict[str, str] = {}
    commerce: dict[str, dict] = {}
    try:
        raw = json.loads(CATALOG_MASTER.read_text(encoding='utf-8'))
        if isinstance(raw, dict):
            for p in raw.get('products') or []:
                if isinstance(p, dict) and p.get('id'):
                    product_ids.add(str(p['id']))
            for s in raw.get('skus') or []:
                if not isinstance(s, dict):
                    continue
                sid = _txt(s.get('id') or s.get('sku'))
                pid = _txt(s.get('product_id'))
                if sid:
                    sku_owner[sid] = pid
    except Exception:
        pass
    try:
        with connect() as con:
            for row in con.execute('SELECT product_id FROM product_content').fetchall():
                product_ids.add(str(row['product_id']))
            for row in con.execute('SELECT sku,product_id FROM dynamic_skus').fetchall():
                sku_owner[str(row['sku'])] = str(row['product_id'])
            for row in con.execute('SELECT sku,price,sale_price,availability,stock_qty,enabled FROM sku_commerce').fetchall():
                commerce[str(row['sku'])] = dict(row)
    except Exception:
        pass
    return product_ids, sku_owner, commerce


def _prepare_rows(rows: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for row in rows:
        out = dict(row)
        pid = _txt(out.get('product_id'))
        if pid and not _txt(out.get('slug')):
            current = pcv3.get(pid)
            if isinstance(current, dict) and current.get('slug'):
                out['slug'] = current['slug']
        prepared.append(out)
    return prepared


def _commerce_values(row: dict, errors: list[dict], row_no: int) -> dict:
    out: dict[str, Any] = {}
    raw = _txt(row.get('price'))
    if raw:
        try:
            out['price'] = _float(raw)
        except ValueError as exc:
            errors.append({'row': row_no, 'field': 'price', 'message': str(exc)})
    raw = _txt(row.get('sale_price'))
    if raw:
        if raw.lower() in CLEAR_VALUES:
            out['sale_price'] = None
            out['sale_price_set'] = True
        else:
            try:
                out['sale_price'] = _float(raw)
                out['sale_price_set'] = True
            except ValueError as exc:
                errors.append({'row': row_no, 'field': 'sale_price', 'message': str(exc)})
    raw = _txt(row.get('availability'))
    if raw:
        if raw not in VALID_AVAILABILITY:
            errors.append({'row': row_no, 'field': 'availability', 'message': 'Допустимо: unknown, in_stock, out_of_stock, preorder, backorder'})
        else:
            out['availability'] = raw
    raw = _txt(row.get('stock_qty'))
    if raw:
        if raw.lower() in CLEAR_VALUES:
            out['stock_qty'] = None
            out['stock_qty_set'] = True
        else:
            try:
                out['stock_qty'] = _int(raw)
                out['stock_qty_set'] = True
            except ValueError as exc:
                errors.append({'row': row_no, 'field': 'stock_qty', 'message': str(exc)})
    raw = _txt(row.get('sale_enabled'))
    if raw:
        try:
            out['enabled'] = _bool(raw)
        except ValueError as exc:
            errors.append({'row': row_no, 'field': 'sale_enabled', 'message': str(exc)})
    return out


def _has_commerce_input(row: dict) -> bool:
    return any(_txt(row.get(k)) for k in COMMERCE_HEADERS)


def _build_plan(rows: list[dict]) -> dict:
    rows = _prepare_rows(rows)
    card_plan = cards_import._build_plan(rows)
    errors = list(card_plan.get('errors') or [])
    row_by_no = {i: {str(k): _txt(v) for k, v in row.items()} for i, row in enumerate(rows, start=2)}
    mapping = _mapping_doc()
    map_products, map_skus = _mapping_index(mapping)
    product_ids, sku_owner, commerce = _catalog_state()

    commerce_items: list[dict] = []
    binding_changes = 0
    create_product_keys: set[str] = set()
    create_sku_keys: set[str] = set()

    for product in card_plan.get('products') or []:
        pid = str(product.get('product_id') or '')
        p_action = str(product.get('action') or '')
        current_map = map_products.get(pid) or {}
        current_product_key = _txt(current_map.get('existing_product_key'))
        relevant_rows = [row_by_no.get(int(s.get('row') or 0), {}) for s in product.get('sku_changes') or []]
        provided_product_keys = sorted({_txt(r.get('commerce_product_key')) for r in relevant_rows if _txt(r.get('commerce_product_key'))})
        if len(provided_product_keys) > 1:
            errors.append({'row': product.get('sku_changes', [{}])[0].get('row', 0), 'field': 'commerce_product_key', 'message': 'Для одного товару вказані різні commerce_product_key'})
        product_key = provided_product_keys[0] if provided_product_keys else current_product_key
        needs_commerce = any(_has_commerce_input(r) for r in relevant_rows)

        if not product_key and needs_commerce:
            if p_action == 'create':
                product_key = _commerce_product_key_from_slug(str(product.get('slug') or ''))
            else:
                first_row = product.get('sku_changes', [{}])[0].get('row', 0)
                errors.append({'row': first_row, 'field': 'commerce_product_key', 'message': 'Існуюча картка не має commerce binding. Вкажіть commerce_product_key явно.'})

        product_exists = bool(product_key and product_key in product_ids)
        create_product = bool(product_key and not product_exists and p_action == 'create')
        if product_key and not product_exists and p_action != 'create':
            first_row = product.get('sku_changes', [{}])[0].get('row', 0)
            errors.append({'row': first_row, 'field': 'commerce_product_key', 'message': f'Commerce product {product_key} не знайдено'})
        if create_product:
            create_product_keys.add(product_key)

        if product_key and product_key != current_product_key:
            binding_changes += 1

        for sku_change in product.get('sku_changes') or []:
            row_no = int(sku_change.get('row') or 0)
            row = row_by_no.get(row_no, {})
            sid = str(sku_change.get('sku_id') or '')
            sku_action = str(sku_change.get('action') or '')
            current_sku_key = map_skus.get((pid, sid), '')
            explicit_sku_key = _txt(row.get('commerce_sku_key'))
            sku_key = explicit_sku_key or current_sku_key
            values = _commerce_values(row, errors, row_no)
            row_needs_commerce = bool(values or explicit_sku_key or _txt(row.get('commerce_product_key')))

            if not sku_key and row_needs_commerce:
                if sku_action == 'create':
                    sku_key = _commerce_sku_key(_txt(row.get('sku_code')), sid)
                else:
                    errors.append({'row': row_no, 'field': 'commerce_sku_key', 'message': 'Існуючий SKU не має commerce binding. Вкажіть commerce_sku_key явно.'})

            owner = sku_owner.get(sku_key) if sku_key else None
            create_sku = False
            if sku_key and not owner:
                if sku_action == 'create' and product_key:
                    if not re.fullmatch(r'[A-Z0-9._-]{3,128}', sku_key):
                        errors.append({'row': row_no, 'field': 'commerce_sku_key', 'message': 'Для нового commerce SKU використовуйте A-Z, 0-9, . _ -'})
                    else:
                        create_sku = True
                        create_sku_keys.add(sku_key)
                else:
                    errors.append({'row': row_no, 'field': 'commerce_sku_key', 'message': f'Commerce SKU {sku_key} не знайдено'})
            elif owner and product_key and owner != product_key:
                errors.append({'row': row_no, 'field': 'commerce_sku_key', 'message': f'Commerce SKU {sku_key} належить товару {owner}, а не {product_key}'})

            if sku_key and sku_key != current_sku_key:
                binding_changes += 1

            before = commerce.get(sku_key, {}) if sku_key else {}
            commerce_items.append({
                'row': row_no,
                'product_id': pid,
                'title': product.get('title', ''),
                'product_action': p_action,
                'sku_id': sid,
                'sku_code': sku_change.get('sku_code', ''),
                'package': sku_change.get('package', ''),
                'sku_action': sku_action,
                'commerce_product_key': product_key,
                'commerce_sku_key': sku_key,
                'create_commerce_product': create_product,
                'create_commerce_sku': create_sku,
                'values': values,
                'price_before': before.get('price'),
                'sale_price_before': before.get('sale_price'),
                'availability_before': before.get('availability'),
                'stock_before': before.get('stock_qty'),
                'enabled_before': bool(before.get('enabled')) if before else None,
            })

    return {
        'errors': errors,
        'products': card_plan.get('products') or [],
        'commerce_items': commerce_items,
        'binding_changes': binding_changes,
        'create_commerce_products': len(create_product_keys),
        'create_commerce_skus': len(create_sku_keys),
    }


def _summary(plan: dict) -> dict:
    products = plan.get('products') or []
    sku_changes = [s for p in products for s in p.get('sku_changes') or []]
    commerce_items = plan.get('commerce_items') or []
    return {
        'products': len(products),
        'create_products': sum(p.get('action') == 'create' for p in products),
        'update_products': sum(p.get('action') == 'update' for p in products),
        'sku_rows': len(sku_changes),
        'create_skus': sum(s.get('action') == 'create' for s in sku_changes),
        'update_skus': sum(s.get('action') == 'update' for s in sku_changes),
        'commerce_rows': sum(bool(x.get('values')) for x in commerce_items),
        'create_commerce_products': plan.get('create_commerce_products', 0),
        'create_commerce_skus': plan.get('create_commerce_skus', 0),
        'binding_changes': plan.get('binding_changes', 0),
    }


def template_rows() -> list[dict]:
    base = cards_import.template_rows()[0]
    rows: list[dict] = []
    for sku_code, label, price in (
        ('EXAMPLE-100G', '100 г', '100'),
        ('EXAMPLE-1KG', '1 кг', '300'),
        ('EXAMPLE-5KG', '5 кг', '900'),
    ):
        row = dict(base)
        row.update({
            'sku_id': '', 'sku_code': sku_code, 'sku_label': label, 'package': label,
            'commerce_product_key': 'example-product', 'commerce_sku_key': sku_code,
            'price': price, 'sale_price': '', 'availability': 'in_stock',
            'stock_qty': '', 'sale_enabled': '0'
        })
        rows.append(row)
    return rows


def template_csv() -> bytes:
    return _csv_bytes(template_rows())


def template_xlsx() -> bytes:
    return write_xlsx(template_rows(), HEADERS)


def export_rows() -> list[dict]:
    mapping = _mapping_doc()
    map_products, map_skus = _mapping_index(mapping)
    _, _, commerce = _catalog_state()
    out: list[dict] = []
    for row in cards_import.export_rows():
        r = dict(row)
        pid = _txt(r.get('product_id'))
        sid = _txt(r.get('sku_id'))
        product_key = _txt((map_products.get(pid) or {}).get('existing_product_key'))
        sku_key = map_skus.get((pid, sid), '')
        c = commerce.get(sku_key, {}) if sku_key else {}
        r.update({
            'commerce_product_key': product_key,
            'commerce_sku_key': sku_key,
            'price': '' if c.get('price') is None else c.get('price'),
            'sale_price': '' if c.get('sale_price') is None else c.get('sale_price'),
            'availability': c.get('availability', ''),
            'stock_qty': '' if c.get('stock_qty') is None else c.get('stock_qty'),
            'sale_enabled': '' if not c else ('1' if c.get('enabled') else '0'),
        })
        out.append(r)
    return out


def export_csv() -> bytes:
    return _csv_bytes(export_rows())


def export_xlsx() -> bytes:
    return write_xlsx(export_rows(), HEADERS)


def parse_upload(filename: str, raw: bytes) -> list[dict]:
    return cards_import.parse_upload(filename, raw)


def preview(filename: str, raw: bytes) -> dict:
    rows = parse_upload(filename, raw)
    plan = _build_plan(rows)
    token = uuid.uuid4().hex
    session = SESSIONS / token
    session.mkdir(parents=True, exist_ok=False)
    (session / 'rows.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    (session / 'meta.json').write_text(json.dumps({'filename': filename, 'created_at': time.time()}, ensure_ascii=False), encoding='utf-8')
    changes: list[dict] = []
    for item in plan.get('commerce_items') or []:
        values = item.get('values') or {}
        changes.append({
            'row': item.get('row'),
            'product_id': item.get('product_id'),
            'title': item.get('title'),
            'product_action': item.get('product_action'),
            'sku_id': item.get('sku_id'),
            'sku_code': item.get('sku_code'),
            'package': item.get('package'),
            'sku_action': item.get('sku_action'),
            'commerce_product_key': item.get('commerce_product_key'),
            'commerce_sku_key': item.get('commerce_sku_key'),
            'commerce_action': 'create' if item.get('create_commerce_sku') else ('update' if values else 'bind/keep'),
            'price_before': item.get('price_before'),
            'price_after': values.get('price', item.get('price_before')),
            'sale_price_before': item.get('sale_price_before'),
            'sale_price_after': values.get('sale_price', item.get('sale_price_before')) if values.get('sale_price_set') else item.get('sale_price_before'),
            'availability_before': item.get('availability_before'),
            'availability_after': values.get('availability', item.get('availability_before')),
            'stock_before': item.get('stock_before'),
            'stock_after': values.get('stock_qty', item.get('stock_before')) if values.get('stock_qty_set') else item.get('stock_before'),
        })
    return {
        'token': token,
        'rows': len(rows),
        'valid': not plan['errors'],
        'errors': plan['errors'],
        'summary': _summary(plan),
        'changes': changes[:1000],
    }


def _history(add: dict | None = None) -> list[dict]:
    items: list[dict] = []
    if HISTORY_FILE.exists():
        try:
            loaded = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
            if isinstance(loaded, list):
                items = loaded
        except Exception:
            pass
    if add:
        items.insert(0, add)
        HISTORY_FILE.write_text(json.dumps(items[:100], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return items


def history() -> list[dict]:
    return _history()


def _sqlite_backup(dest: Path) -> None:
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


def _sqlite_restore(src_path: Path) -> None:
    if not src_path.exists():
        raise ValueError('SQLite backup не знайдено')
    src = sqlite3.connect(str(src_path))
    try:
        dst = sqlite3.connect(str(DB_PATH))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _backup() -> str:
    backup_id = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    dest = BACKUPS / backup_id
    dest.mkdir(parents=True, exist_ok=False)
    cards_dest = dest / 'product_cards_v3'
    if pcv3.BASE.exists():
        shutil.copytree(pcv3.BASE, cards_dest)
    else:
        cards_dest.mkdir()
    _sqlite_backup(dest / 'bb610.sqlite3')
    return backup_id


def _restore(backup_id: str) -> None:
    src = BACKUPS / backup_id
    cards_src = src / 'product_cards_v3'
    db_src = src / 'bb610.sqlite3'
    if not cards_src.exists() or not db_src.exists():
        raise ValueError('Backup unified import не знайдено або пошкоджено')
    tmp = pcv3.BASE.with_name(pcv3.BASE.name + '.restore-tmp')
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(cards_src, tmp)
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    tmp.replace(pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)
    _sqlite_restore(db_src)


def _apply_commerce_item(item: dict) -> None:
    product_key = _txt(item.get('commerce_product_key'))
    sku_key = _txt(item.get('commerce_sku_key'))
    if not product_key or not sku_key:
        return
    if item.get('create_commerce_product') and not catalog_cms.admin_detail(product_key):
        created = catalog_cms.create_product({
            'id': product_key,
            'slug': product_key,
            'name': item.get('title') or product_key,
            'brand': '',
            'category_id': 'nutrition',
            'published': False,
        })
        if not created or created.get('id') != product_key:
            raise RuntimeError(f'Не вдалося створити commerce product {product_key}')
    if item.get('create_commerce_sku'):
        detail = catalog_cms.admin_detail(product_key)
        if not detail:
            raise RuntimeError(f'Commerce product {product_key} не існує')
        body = {
            'sku': sku_key,
            'variant': item.get('package') or '1 шт',
            'currency': 'UAH',
            'availability': 'unknown',
            'enabled': False,
        }
        values = item.get('values') or {}
        if 'price' in values:
            body['price'] = values['price']
        if values.get('sale_price_set'):
            body['sale_price'] = values.get('sale_price')
        if 'availability' in values:
            body['availability'] = values['availability']
        if values.get('stock_qty_set'):
            body['stock_qty'] = values.get('stock_qty')
        if 'enabled' in values:
            body['enabled'] = values['enabled']
        catalog_cms.create_sku(product_key, body)
        return
    values = item.get('values') or {}
    if values:
        body: dict[str, Any] = {}
        if 'price' in values:
            body['price'] = values['price']
        if values.get('sale_price_set'):
            body['sale_price'] = values.get('sale_price')
            if values.get('sale_price') is None:
                body['clear_sale_price'] = True
        if 'availability' in values:
            body['availability'] = values['availability']
        if values.get('stock_qty_set'):
            body['stock_qty'] = values.get('stock_qty')
            if values.get('stock_qty') is None:
                body['clear_stock_qty'] = True
        if 'enabled' in values:
            body['enabled'] = values['enabled']
        updated = catalog_cms.update_catalog_sku(product_key, sku_key, body)
        if updated is None:
            raise RuntimeError(f'Не знайдено commerce SKU {sku_key} у товарі {product_key}')


def _verify(plan: dict) -> None:
    for product in plan.get('products') or []:
        card = pcv3.get(str(product.get('product_id') or ''))
        if not isinstance(card, dict):
            raise RuntimeError(f'Product Card v3 не збережено: {product.get("product_id")}')
        pcv3.validate(card)
    mapping = _mapping_doc()
    map_products, map_skus = _mapping_index(mapping)
    _, sku_owner, commerce = _catalog_state()
    for item in plan.get('commerce_items') or []:
        product_key = _txt(item.get('commerce_product_key'))
        sku_key = _txt(item.get('commerce_sku_key'))
        if not product_key or not sku_key:
            continue
        pid = str(item.get('product_id') or '')
        sid = str(item.get('sku_id') or '')
        if _txt((map_products.get(pid) or {}).get('existing_product_key')) != product_key:
            raise RuntimeError(f'Не збережено product commerce binding для {pid}')
        if map_skus.get((pid, sid), '') != sku_key:
            raise RuntimeError(f'Не збережено SKU commerce binding для {sid}')
        if sku_owner.get(sku_key) != product_key:
            raise RuntimeError(f'Commerce SKU {sku_key} прив’язаний не до {product_key}')
        values = item.get('values') or {}
        if not values:
            continue
        current = commerce.get(sku_key)
        if not current:
            raise RuntimeError(f'Commerce row {sku_key} не знайдено після Apply')
        if 'price' in values and current.get('price') != values['price']:
            raise RuntimeError(f'Price verify failed for {sku_key}')
        if values.get('sale_price_set') and current.get('sale_price') != values.get('sale_price'):
            raise RuntimeError(f'Sale price verify failed for {sku_key}')
        if 'availability' in values and current.get('availability') != values['availability']:
            raise RuntimeError(f'Availability verify failed for {sku_key}')
        if values.get('stock_qty_set') and current.get('stock_qty') != values.get('stock_qty'):
            raise RuntimeError(f'Stock verify failed for {sku_key}')
        if 'enabled' in values and bool(current.get('enabled')) != bool(values['enabled']):
            raise RuntimeError(f'Sale enabled verify failed for {sku_key}')


def apply(token: str) -> dict:
    session = SESSIONS / token
    if not session.exists():
        raise ValueError('Preview token не знайдено')
    rows = json.loads((session / 'rows.json').read_text(encoding='utf-8'))
    plan = _build_plan(rows)
    if plan['errors']:
        raise ValueError('Файл має помилки; повторіть Preview')

    backup_id = _backup()
    applied_products = 0
    try:
        for item in plan.get('products') or []:
            card = item['card']
            if item['action'] == 'create':
                pcv3.create(card)
            else:
                pcv3.put(item['product_id'], card)
            applied_products += 1

        for item in plan.get('commerce_items') or []:
            _apply_commerce_item(item)

        mapping = _mapping_doc()
        for item in plan.get('commerce_items') or []:
            product_key = _txt(item.get('commerce_product_key'))
            sku_key = _txt(item.get('commerce_sku_key'))
            if product_key and sku_key:
                _upsert_mapping(
                    mapping,
                    str(item.get('product_id') or ''),
                    product_key,
                    str(item.get('sku_id') or ''),
                    sku_key,
                )
        _save_mapping(mapping)
        _verify(plan)
    except Exception:
        _restore(backup_id)
        raise

    meta = json.loads((session / 'meta.json').read_text(encoding='utf-8'))
    summary = _summary(plan)
    event = {
        'time': time.time(),
        'action': 'product_card_v3_catalog_import',
        'filename': meta.get('filename', ''),
        'backup': backup_id,
        **summary,
    }
    _history(event)
    return {'backup': backup_id, 'applied_products': applied_products, **summary, 'verified': True}


def rollback(backup_id: str) -> dict:
    current_backup = _backup()
    _restore(backup_id)
    _history({
        'time': time.time(),
        'action': 'product_card_v3_catalog_rollback',
        'backup': current_backup,
        'restored': backup_id,
    })
    return {'restored': backup_id, 'safety_backup': current_backup}
