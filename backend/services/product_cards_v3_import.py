from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import product_cards_v3 as pcv3
from .catalog_import_xlsx import read_xlsx, write_xlsx

ROOT = Path(__file__).resolve().parents[2]
VAR = ROOT / 'var' / 'product-card-v3-import'
SESSIONS = VAR / 'sessions'
BACKUPS = VAR / 'backups'
HISTORY_FILE = VAR / 'history.json'
for _p in (SESSIONS, BACKUPS):
    _p.mkdir(parents=True, exist_ok=True)

HEADERS = [
    'product_id', 'slug', 'product_enabled', 'title', 'brand', 'category',
    'short_description', 'description', 'benefits_json', 'how_it_works',
    'application', 'composition', 'characteristics_json', 'seo_title',
    'seo_description', 'sku_id', 'sku_code', 'sku_label', 'package',
    'sku_enabled', 'primary_media_id', 'gallery_media_ids_json', 'media_json'
]

TRUE_VALUES = {'1', 'true', 'yes', 'on', 'так', 'y'}
FALSE_VALUES = {'0', 'false', 'no', 'off', 'ні', 'нет', 'n'}


def _txt(value: Any) -> str:
    return '' if value is None else str(value).strip()


def _bool(value: Any, default: bool | None = None) -> bool | None:
    raw = _txt(value).lower()
    if not raw:
        return default
    if raw in TRUE_VALUES:
        return True
    if raw in FALSE_VALUES:
        return False
    raise ValueError(f'Невідоме boolean значення: {value}')


def _json(value: Any, default: Any) -> Any:
    raw = _txt(value)
    if not raw:
        return deepcopy(default)
    try:
        return json.loads(raw)
    except Exception as exc:
        raise ValueError(f'Некоректний JSON: {exc}') from exc


def _norm_pack(value: Any) -> str:
    s = _txt(value).lower().replace('*', '').replace(',', '.')
    s = re.sub(r'\s+', ' ', s)
    pats = (
        (r'(\d+(?:\.\d+)?)\s*(?:мл|ml)\b', 'ml'),
        (r'(\d+(?:\.\d+)?)\s*(?:кг|kg)\b', 'kg'),
        (r'(\d+(?:\.\d+)?)\s*(?:г|g)\b', 'g'),
        (r'(\d+(?:\.\d+)?)\s*(?:л|l)\b', 'l'),
        (r'(\d+(?:\.\d+)?)\s*(?:шт|pcs?|pieces?)\b', 'pcs'),
    )
    for pat, unit in pats:
        m = re.search(pat, s, flags=re.I)
        if m:
            return f'{float(m.group(1)):g}{unit}'
    return re.sub(r'[^0-9a-zа-яіїєґ]+', '', s, flags=re.I)


def _slugify(value: Any) -> str:
    s = _txt(value).lower()
    tr = str.maketrans({
        'а':'a','б':'b','в':'v','г':'h','ґ':'g','д':'d','е':'e','ё':'e','є':'ie','ж':'zh','з':'z','и':'y','і':'i','ї':'i','й':'i',
        'к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
        'щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'iu','я':'ia'
    })
    s = s.translate(tr)
    s = re.sub(r'[^a-z0-9._-]+', '-', s)
    return re.sub(r'-+', '-', s).strip('-._')[:160]


def _generated_product_id(slug: str) -> str:
    token = hashlib.sha256(('pcv3-import|' + slug).encode('utf-8')).hexdigest()[:16]
    return f'prd_imp_{token}'


def _generated_sku_id(product_id: str, sku_code: str, package: str) -> str:
    seed = f'pcv3-import|{product_id}|{sku_code}|{_norm_pack(package)}'
    token = hashlib.sha256(seed.encode('utf-8')).hexdigest()[:18]
    return f'sku_imp_{token}'


def _csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    return ('\ufeff' + buf.getvalue()).encode('utf-8')


def parse_upload(filename: str, raw: bytes) -> list[dict]:
    ext = Path(filename or '').suffix.lower()
    if ext == '.csv':
        text = raw.decode('utf-8-sig', 'replace')
        rows = list(csv.DictReader(io.StringIO(text)))
    elif ext == '.xlsx':
        rows = read_xlsx(raw)
    else:
        raise ValueError('Для Product Card v3 підтримуються CSV або XLSX')
    if not rows:
        raise ValueError('Файл не містить рядків даних')
    return [{str(k).strip(): v for k, v in row.items()} for row in rows]


def template_rows() -> list[dict]:
    return [{
        'product_id': '',
        'slug': 'example-product',
        'product_enabled': '1',
        'title': 'Приклад товару',
        'brand': 'Brand',
        'category': 'fertilizer',
        'short_description': 'Короткий опис',
        'description': 'Повний опис товару',
        'benefits_json': '[{"title":"Перевага","text":"Опис переваги"}]',
        'how_it_works': '',
        'application': '',
        'composition': '',
        'characteristics_json': '[{"label":"Форма","value":"порошок"}]',
        'seo_title': '',
        'seo_description': '',
        'sku_id': '',
        'sku_code': 'EXAMPLE-1KG',
        'sku_label': '1 кг',
        'package': '1 кг',
        'sku_enabled': '1',
        'primary_media_id': '',
        'gallery_media_ids_json': '[]',
        'media_json': '[]',
    }]


def template_csv() -> bytes:
    return _csv_bytes(template_rows())


def template_xlsx() -> bytes:
    return write_xlsx(template_rows(), HEADERS)


def export_rows() -> list[dict]:
    out: list[dict] = []
    for summary in pcv3.list_cards():
        pid = str(summary.get('product_id') or '')
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            continue
        content = card.get('content') or {}
        sm = card.get('sku_media') or {}
        media_json = json.dumps(sm.get('media') or [], ensure_ascii=False, separators=(',', ':'))
        for sku in sm.get('skus') or []:
            if not isinstance(sku, dict):
                continue
            out.append({
                'product_id': pid,
                'slug': card.get('slug', ''),
                'product_enabled': '1' if card.get('enabled') else '0',
                'title': content.get('title', ''),
                'brand': content.get('brand', ''),
                'category': content.get('category', ''),
                'short_description': content.get('short_description', ''),
                'description': content.get('description', ''),
                'benefits_json': json.dumps(content.get('benefits') or [], ensure_ascii=False, separators=(',', ':')),
                'how_it_works': content.get('how_it_works', ''),
                'application': content.get('application', ''),
                'composition': content.get('composition', ''),
                'characteristics_json': json.dumps(content.get('characteristics') or [], ensure_ascii=False, separators=(',', ':')),
                'seo_title': (content.get('seo') or {}).get('title', ''),
                'seo_description': (content.get('seo') or {}).get('description', ''),
                'sku_id': sku.get('sku_id', ''),
                'sku_code': sku.get('sku_code', ''),
                'sku_label': sku.get('label', ''),
                'package': sku.get('package', ''),
                'sku_enabled': '1' if sku.get('enabled') else '0',
                'primary_media_id': sku.get('primary_media_id') or '',
                'gallery_media_ids_json': json.dumps(sku.get('gallery_media_ids') or [], ensure_ascii=False, separators=(',', ':')),
                'media_json': media_json,
            })
    return out


def export_csv() -> bytes:
    return _csv_bytes(export_rows())


def export_xlsx() -> bytes:
    return write_xlsx(export_rows(), HEADERS)


def _existing_state() -> tuple[dict[str, dict], dict[str, str], dict[str, str]]:
    cards: dict[str, dict] = {}
    slugs: dict[str, str] = {}
    global_skus: dict[str, str] = {}
    for summary in pcv3.list_cards():
        pid = str(summary.get('product_id') or '')
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            continue
        cards[pid] = card
        slug = str(card.get('slug') or '').strip().lower()
        if slug:
            slugs[slug] = pid
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if isinstance(sku, dict) and sku.get('sku_id'):
                global_skus[str(sku['sku_id'])] = pid
    return cards, slugs, global_skus


def _consistent(rows: list[tuple[int, dict]], field: str, errors: list[dict]) -> str:
    values = [(_txt(r.get(field)), row_no) for row_no, r in rows if _txt(r.get(field))]
    unique = []
    for value, row_no in values:
        if value not in [x[0] for x in unique]:
            unique.append((value, row_no))
    if len(unique) > 1:
        errors.append({'row': unique[1][1], 'field': field, 'message': 'Різні значення одного товару в різних SKU-рядках'})
    return unique[0][0] if unique else ''


def _build_plan(rows: list[dict]) -> dict:
    cards, slug_map, global_skus = _existing_state()
    errors: list[dict] = []
    indexed = [(i, {k: _txt(v) for k, v in row.items()}) for i, row in enumerate(rows, start=2)]

    groups: dict[str, list[tuple[int, dict]]] = {}
    for row_no, row in indexed:
        title = row.get('title', '')
        slug = row.get('slug', '') or _slugify(title)
        pid = row.get('product_id', '')
        if not pid and not slug:
            errors.append({'row': row_no, 'field': 'slug', 'message': 'Потрібен product_id або slug/title'})
            continue
        key = f'pid:{pid}' if pid else f'slug:{slug.lower()}'
        row['_resolved_slug'] = slug.lower()
        groups.setdefault(key, []).append((row_no, row))

    plans: list[dict] = []
    planned_slugs: set[str] = set()
    planned_skus: dict[str, str] = {}

    for group_rows in groups.values():
        first_no, first = group_rows[0]
        provided_pid = _consistent(group_rows, 'product_id', errors)
        slug = _consistent(group_rows, 'slug', errors) or first.get('_resolved_slug') or _slugify(_consistent(group_rows, 'title', errors))
        slug = slug.lower().strip()
        title = _consistent(group_rows, 'title', errors)

        existing: dict | None = None
        if provided_pid:
            existing = cards.get(provided_pid)
            if existing is None:
                existing = None
            elif slug and str(existing.get('slug') or '').lower() != slug:
                # slug may intentionally be edited, but it must not collide with another card.
                other = slug_map.get(slug)
                if other and other != provided_pid:
                    errors.append({'row': first_no, 'field': 'slug', 'message': f'slug вже використовується товаром {other}'})
        elif slug in slug_map:
            existing = cards.get(slug_map[slug])

        if existing is None:
            pid = provided_pid or _generated_product_id(slug)
            if provided_pid and not pcv3.PRODUCT_ID_RE.fullmatch(provided_pid):
                errors.append({'row': first_no, 'field': 'product_id', 'message': 'Некоректний product_id'})
            if not title:
                errors.append({'row': first_no, 'field': 'title', 'message': 'Назва обов’язкова для нового товару'})
            if not slug or not pcv3.SLUG_RE.fullmatch(slug):
                errors.append({'row': first_no, 'field': 'slug', 'message': 'Некоректний slug; використовуйте латиницю, цифри, . _ -'})
            if pid in cards:
                errors.append({'row': first_no, 'field': 'product_id', 'message': 'product_id вже існує'})
            if slug in slug_map or slug in planned_slugs:
                errors.append({'row': first_no, 'field': 'slug', 'message': 'slug вже існує'})
            base_card = {
                'schema_version': '3.0', 'product_id': pid, 'slug': slug, 'enabled': True,
                'content': {
                    'title': title or 'Новий товар', 'brand': '', 'category': '', 'short_description': '', 'description': '',
                    'benefits': [], 'how_it_works': '', 'application': '', 'composition': '', 'characteristics': [],
                    'seo': {'title': '', 'description': ''}
                },
                'sku_media': {'skus': [], 'media': []}
            }
            action = 'create'
        else:
            pid = str(existing['product_id'])
            base_card = deepcopy(existing)
            action = 'update'
            if slug and slug != str(base_card.get('slug') or '').lower():
                other = slug_map.get(slug)
                if other and other != pid:
                    errors.append({'row': first_no, 'field': 'slug', 'message': f'slug вже використовується товаром {other}'})
                else:
                    base_card['slug'] = slug

        planned_slugs.add(str(base_card.get('slug') or slug))

        content = base_card['content']
        scalar_fields = {
            'title': 'title', 'brand': 'brand', 'category': 'category',
            'short_description': 'short_description', 'description': 'description',
            'how_it_works': 'how_it_works', 'application': 'application', 'composition': 'composition'
        }
        for src, dst in scalar_fields.items():
            value = _consistent(group_rows, src, errors)
            if value:
                content[dst] = value

        enabled_raw = _consistent(group_rows, 'product_enabled', errors)
        if enabled_raw:
            try:
                base_card['enabled'] = bool(_bool(enabled_raw, base_card.get('enabled', True)))
            except ValueError as exc:
                errors.append({'row': first_no, 'field': 'product_enabled', 'message': str(exc)})

        for src, dst, default in (
            ('benefits_json', 'benefits', []),
            ('characteristics_json', 'characteristics', []),
        ):
            raw = _consistent(group_rows, src, errors)
            if raw:
                try:
                    content[dst] = _json(raw, default)
                except ValueError as exc:
                    errors.append({'row': first_no, 'field': src, 'message': str(exc)})

        seo_title = _consistent(group_rows, 'seo_title', errors)
        seo_description = _consistent(group_rows, 'seo_description', errors)
        if seo_title:
            content['seo']['title'] = seo_title
        if seo_description:
            content['seo']['description'] = seo_description

        media_raw = _consistent(group_rows, 'media_json', errors)
        if media_raw:
            try:
                media = _json(media_raw, [])
                if not isinstance(media, list):
                    raise ValueError('media_json має бути JSON-масивом')
                base_card['sku_media']['media'] = media
            except ValueError as exc:
                errors.append({'row': first_no, 'field': 'media_json', 'message': str(exc)})

        existing_skus = base_card['sku_media'].get('skus') or []
        by_id = {str(x.get('sku_id')): x for x in existing_skus if isinstance(x, dict) and x.get('sku_id')}
        by_code: dict[str, list[dict]] = {}
        by_pack: dict[str, list[dict]] = {}
        for sku in existing_skus:
            if not isinstance(sku, dict):
                continue
            code = _txt(sku.get('sku_code'))
            if code:
                by_code.setdefault(code.lower(), []).append(sku)
            pkey = _norm_pack(sku.get('package') or sku.get('label'))
            if pkey:
                by_pack.setdefault(pkey, []).append(sku)

        sku_changes: list[dict] = []
        for row_no, row in group_rows:
            sid = row.get('sku_id', '')
            code = row.get('sku_code', '')
            package = row.get('package', '') or row.get('sku_label', '')
            label = row.get('sku_label', '') or package
            sku: dict | None = None
            sku_action = 'create'

            if sid:
                sku = by_id.get(sid)
                owner = global_skus.get(sid)
                if sku is None and owner and owner != pid:
                    errors.append({'row': row_no, 'field': 'sku_id', 'message': f'sku_id належить іншому товару {owner}'})
                    continue
                if sku is not None:
                    sku_action = 'update'
            elif code and len(by_code.get(code.lower(), [])) == 1:
                sku = by_code[code.lower()][0]
                sid = str(sku['sku_id'])
                sku_action = 'update'
            elif package and len(by_pack.get(_norm_pack(package), [])) == 1:
                sku = by_pack[_norm_pack(package)][0]
                sid = str(sku['sku_id'])
                sku_action = 'update'

            if sku is None:
                if not sid:
                    if not code and not package:
                        errors.append({'row': row_no, 'field': 'sku_id', 'message': 'Для нового SKU потрібен sku_code або package'})
                        continue
                    sid = _generated_sku_id(pid, code, package)
                if not pcv3.SKU_ID_RE.fullmatch(sid):
                    errors.append({'row': row_no, 'field': 'sku_id', 'message': 'Некоректний sku_id'})
                    continue
                if sid in planned_skus and planned_skus[sid] != pid:
                    errors.append({'row': row_no, 'field': 'sku_id', 'message': 'sku_id дублюється між товарами у файлі'})
                    continue
                sku = {
                    'sku_id': sid,
                    'sku_code': code,
                    'label': label,
                    'package': package,
                    'primary_media_id': None,
                    'gallery_media_ids': [],
                    'sort_order': len(existing_skus),
                    'enabled': True,
                }
                existing_skus.append(sku)
                by_id[sid] = sku
            planned_skus[sid] = pid

            if code:
                sku['sku_code'] = code
            if label:
                sku['label'] = label
            if package:
                sku['package'] = package
            enabled = row.get('sku_enabled', '')
            if enabled:
                try:
                    sku['enabled'] = bool(_bool(enabled, sku.get('enabled', True)))
                except ValueError as exc:
                    errors.append({'row': row_no, 'field': 'sku_enabled', 'message': str(exc)})
            primary = row.get('primary_media_id', '')
            if primary:
                sku['primary_media_id'] = primary
            galleries_raw = row.get('gallery_media_ids_json', '')
            if galleries_raw:
                try:
                    galleries = _json(galleries_raw, [])
                    if not isinstance(galleries, list) or any(not isinstance(x, str) for x in galleries):
                        raise ValueError('gallery_media_ids_json має бути JSON-масивом рядків')
                    sku['gallery_media_ids'] = galleries
                except ValueError as exc:
                    errors.append({'row': row_no, 'field': 'gallery_media_ids_json', 'message': str(exc)})
            sku_changes.append({'row': row_no, 'sku_id': sid, 'sku_code': sku.get('sku_code', ''), 'package': sku.get('package', ''), 'action': sku_action})

        for idx, sku in enumerate(existing_skus):
            if isinstance(sku, dict):
                sku['sort_order'] = idx
        base_card['sku_media']['skus'] = existing_skus

        try:
            pcv3.validate(base_card)
        except Exception as exc:
            errors.append({'row': first_no, 'field': 'card', 'message': str(exc)})

        plans.append({
            'product_id': pid,
            'slug': base_card.get('slug', slug),
            'title': (base_card.get('content') or {}).get('title', ''),
            'action': action,
            'sku_changes': sku_changes,
            'card': base_card,
        })

    return {'errors': errors, 'products': plans}


def _summary(plan: dict) -> dict:
    products = plan.get('products') or []
    sku_changes = [s for p in products for s in p.get('sku_changes') or []]
    return {
        'products': len(products),
        'create_products': sum(p.get('action') == 'create' for p in products),
        'update_products': sum(p.get('action') == 'update' for p in products),
        'sku_rows': len(sku_changes),
        'create_skus': sum(s.get('action') == 'create' for s in sku_changes),
        'update_skus': sum(s.get('action') == 'update' for s in sku_changes),
    }


def preview(filename: str, raw: bytes) -> dict:
    rows = parse_upload(filename, raw)
    plan = _build_plan(rows)
    token = uuid.uuid4().hex
    session = SESSIONS / token
    session.mkdir(parents=True, exist_ok=False)
    (session / 'rows.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    (session / 'meta.json').write_text(json.dumps({'filename': filename, 'created_at': time.time()}, ensure_ascii=False), encoding='utf-8')
    changes = []
    for product in plan.get('products') or []:
        for sku in product.get('sku_changes') or []:
            changes.append({
                'row': sku.get('row'), 'product_id': product.get('product_id'), 'slug': product.get('slug'),
                'title': product.get('title'), 'product_action': product.get('action'),
                'sku_id': sku.get('sku_id'), 'sku_code': sku.get('sku_code'),
                'package': sku.get('package'), 'sku_action': sku.get('action')
            })
    return {
        'token': token,
        'rows': len(rows),
        'valid': not plan['errors'],
        'errors': plan['errors'],
        'summary': _summary(plan),
        'changes': changes[:500],
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


def _backup() -> str:
    backup_id = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    dest = BACKUPS / backup_id
    shutil.copytree(pcv3.BASE, dest)
    return backup_id


def _restore(backup_id: str) -> None:
    src = BACKUPS / backup_id
    if not src.exists() or not src.is_dir():
        raise ValueError('Backup Product Card v3 не знайдено')
    tmp = pcv3.BASE.with_name(pcv3.BASE.name + '.restore-tmp')
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(src, tmp)
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    tmp.replace(pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply(token: str) -> dict:
    session = SESSIONS / token
    if not session.exists():
        raise ValueError('Preview token не знайдено')
    rows = json.loads((session / 'rows.json').read_text(encoding='utf-8'))
    plan = _build_plan(rows)
    if plan['errors']:
        raise ValueError('Файл має помилки; повторіть Preview')

    commerce_before = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else None
    backup_id = _backup()
    applied = 0
    try:
        for item in plan['products']:
            card = item['card']
            if item['action'] == 'create':
                pcv3.create(card)
            else:
                pcv3.put(item['product_id'], card)
            applied += 1
        commerce_after = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else None
        if commerce_before != commerce_after:
            raise RuntimeError('Commerce map змінився під час імпорту; виконано rollback')
    except Exception:
        _restore(backup_id)
        raise

    meta = json.loads((session / 'meta.json').read_text(encoding='utf-8'))
    summary = _summary(plan)
    event = {
        'time': time.time(), 'action': 'product_card_v3_import', 'filename': meta.get('filename', ''),
        'backup': backup_id, **summary
    }
    _history(event)
    return {'backup': backup_id, 'applied_products': applied, **summary, 'commerce_unchanged': True}


def rollback(backup_id: str) -> dict:
    current_backup = _backup()
    _restore(backup_id)
    _history({'time': time.time(), 'action': 'product_card_v3_rollback', 'backup': current_backup, 'restored': backup_id})
    return {'restored': backup_id, 'safety_backup': current_backup}
