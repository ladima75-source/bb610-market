from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from backend.services.catalog_cms import admin_detail as catalog_detail, admin_list_products
from backend.services.product_cards_v3 import validate

ROOT = Path(__file__).resolve().parents[1]
LEGACY_FILES = [
    ROOT / 'data' / 'product_cards.master.json',
    ROOT / 'data' / 'product-cards.master.json',
]
V3 = ROOT / 'data' / 'product_cards_v3'
PRODUCTS = V3 / 'products'
INDEX = V3 / 'index.json'
COMMERCE_MAP = V3 / 'commerce_map.json'
MANIFEST = V3 / 'migration_manifest.json'

TARGETS = [
    'Kendal',
    'Megafol',
    'MASTER 15-5-30+2',
    'MASTER 13-40-13',
    'MASTER 20-20-20',
    'MASTER 3-11-38',
    'MASTER 18-18-18',
    'MASTER 17-6-18',
    'PLANTAFOL 30-10-10',
    'PLANTAFOL 10-54-10',
    'PLANTAFOL 20-20-20',
    'PLANTAFOL 5-15-45',
    'PLANTAFOL 0-25-50',
    'Nova PeKacid 0-60-20',
]

ALIASES = {
    'Megafol': ['MEGAFOL', 'MEGAFOL™'],
    'Nova PeKacid 0-60-20': ['NOVA PEKACID 0-60-20', 'PEKACID 0-60-20', 'NOVAPEKACID 0-60-20'],
}


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return deepcopy(default)


def _save(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def _collection(obj: Any) -> list[dict]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ('products', 'cards', 'items'):
            value = obj.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict):
                return [x for x in value.values() if isinstance(x, dict)]
        return [x for x in obj.values() if isinstance(x, dict)]
    return []


def _norm(value: Any) -> str:
    text = str(value or '').upper().replace('™', '').replace('®', '')
    text = re.sub(r'[^A-Z0-9А-ЯІЇЄҐ+.-]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _slug(value: Any) -> str:
    text = str(value or '').lower().replace('™', '').replace('®', '')
    text = re.sub(r'[^a-z0-9._-]+', '-', text).strip('-')
    return text[:160] or 'product'


def _text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return '\n'.join(x for x in (_text(v) for v in value) if x)
    if isinstance(value, dict):
        for key in ('text', 'body', 'description', 'intro', 'note', 'value'):
            result = _text(value.get(key))
            if result:
                return result
    return ''


def _legacy_cards() -> list[dict]:
    cards: list[dict] = []
    for path in LEGACY_FILES:
        if path.exists():
            cards.extend(_collection(_load(path, [])))
    if not cards:
        raise RuntimeError('Legacy product card master not found or empty')
    return cards


def _identity_values(card: dict) -> list[str]:
    values = []
    for key in ('slug', 'id', 'product_id', 'code', 'name', 'official_name', 'title'):
        if card.get(key):
            values.append(str(card.get(key)))
    v2 = card.get('product_card_v2')
    if isinstance(v2, dict):
        for key in ('name', 'display_name', 'title'):
            if v2.get(key):
                values.append(str(v2.get(key)))
    return values


def _find_legacy(cards: list[dict], target: str) -> dict:
    wanted = {_norm(target), *(_norm(x) for x in ALIASES.get(target, []))}
    matches = [c for c in cards if any(_norm(v) in wanted for v in _identity_values(c))]
    uniq = []
    seen = set()
    for card in matches:
        marker = json.dumps(card, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            uniq.append(card)
    if len(uniq) != 1:
        raise RuntimeError(f'{target}: expected exactly one legacy card, found {len(uniq)}')
    return uniq[0]


def _find_catalog_product(target: str, legacy: dict) -> tuple[dict, dict]:
    rows = admin_list_products()
    wanted = {_norm(target), *(_norm(x) for x in ALIASES.get(target, []))}

    # First prefer exact legacy identity when it is an actual catalog product id.
    for key in ('product_id', 'id', 'slug'):
        raw = str(legacy.get(key) or '').strip()
        if raw:
            detail = catalog_detail(raw)
            if detail:
                return next((x for x in rows if x.get('id') == raw), {'id': raw, 'slug': detail.get('slug', raw), 'name': detail.get('name', raw)}), detail

    matches = [r for r in rows if _norm(r.get('name')) in wanted or _norm(r.get('slug')) in wanted or _norm(r.get('id')) in wanted]
    if len(matches) != 1:
        raise RuntimeError(f'{target}: expected exactly one catalog product, found {len(matches)}')
    detail = catalog_detail(matches[0]['id'])
    if not detail:
        raise RuntimeError(f'{target}: catalog detail not found for {matches[0]["id"]}')
    return matches[0], detail


def _sha(prefix: str, value: str, n: int = 18) -> str:
    return prefix + hashlib.sha1(value.encode('utf-8')).hexdigest()[:n]


def _benefits(card: dict, v2: dict) -> list[dict]:
    src = v2.get('why', card.get('why_product', card.get('benefits', [])))
    out: list[dict] = []
    if isinstance(src, dict):
        text = _text(src.get('text') or src.get('body'))
        if text:
            out.append({'title': _text(src.get('title')) or 'Перевага', 'text': text})
    elif isinstance(src, list):
        for item in src:
            if isinstance(item, dict):
                title = _text(item.get('title'))
                text = _text(item.get('text') or item.get('body') or item.get('description'))
                if title or text:
                    out.append({'title': title, 'text': text})
            else:
                text = _text(item)
                if text:
                    out.append({'title': '', 'text': text})
    else:
        text = _text(src)
        if text:
            out.append({'title': '', 'text': text})
    return out


def _characteristics(card: dict, v2: dict) -> list[dict]:
    src = v2.get('characteristics')
    if not src:
        src = v2.get('specs', card.get('characteristics', card.get('specs', [])))
    rows = src.get('rows', []) if isinstance(src, dict) else src
    out: list[dict] = []
    if isinstance(rows, list):
        for item in rows:
            if isinstance(item, dict):
                label = _text(item.get('label') or item.get('name') or item.get('title'))
                value = _text(item.get('value') or item.get('text') or item.get('description'))
                if label or value:
                    out.append({'label': label, 'value': value})
            else:
                text = _text(item)
                if text:
                    out.append({'label': '', 'value': text})
    elif _text(rows):
        out.append({'label': 'Характеристики', 'value': _text(rows)})
    if not out and isinstance(src, dict):
        text = _text(src.get('intro') or src.get('text'))
        if text:
            out.append({'label': 'Характеристики', 'value': text})
    return out


def _application(card: dict, v2: dict) -> str:
    src = v2.get('application', card.get('application', ''))
    if not isinstance(src, dict):
        return _text(src)
    chunks = []
    intro = _text(src.get('intro') or src.get('text'))
    if intro:
        chunks.append(intro)
    rows = src.get('rows')
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                left = _text(row.get('label') or row.get('culture') or row.get('title'))
                right = _text(row.get('value') or row.get('rate') or row.get('text'))
                line = ': '.join(x for x in (left, right) if x)
                if line:
                    chunks.append(line)
            elif _text(row):
                chunks.append(_text(row))
    note = _text(src.get('note') or src.get('market_note'))
    if note:
        chunks.append(note)
    return '\n'.join(chunks)


def _how(card: dict, v2: dict) -> str:
    for value in (v2.get('how_it_works'), card.get('how_it_works'), card.get('how_works'), card.get('how')):
        text = _text(value)
        if text:
            return text
    return ''


def _composition(card: dict, v2: dict, catalog: dict) -> str:
    for value in (v2.get('composition'), card.get('composition'), catalog.get('composition')):
        text = _text(value)
        if text:
            return text
    return ''


def _product_image(card: dict, catalog: dict) -> str:
    for src in (card, catalog):
        value = src.get('image') if isinstance(src, dict) else None
        if isinstance(value, dict):
            value = value.get('local') or value.get('path') or value.get('url')
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _sku_image(sku: dict) -> str:
    value = sku.get('image')
    if isinstance(value, dict):
        value = value.get('local') or value.get('path') or value.get('url')
    return value.strip() if isinstance(value, str) else ''


def _media_entry(path: str, title: str, order: int) -> dict:
    return {
        'media_id': _sha('med_', path),
        'path': path,
        'alt': title,
        'kind': 'product',
        'sort_order': order,
    }


def _build(target: str, legacy: dict, catalog_row: dict, catalog: dict) -> tuple[dict, dict, dict]:
    v2 = legacy.get('product_card_v2') if isinstance(legacy.get('product_card_v2'), dict) else {}
    product_id = _sha('prd_', 'pcv3|batch01|' + target)
    title = _text(v2.get('name') or v2.get('display_name') or legacy.get('official_name') or legacy.get('name') or catalog.get('official_name') or catalog.get('name')) or target
    slug = str(catalog_row.get('slug') or catalog.get('slug') or legacy.get('slug') or _slug(target)).strip().lower()
    brand = _text(v2.get('brand') or legacy.get('brand') or catalog.get('brand'))
    category = _text(legacy.get('category_label') or legacy.get('category') or catalog.get('category_label') or catalog.get('category_id'))
    short = _text(v2.get('short_description') or v2.get('lead') or v2.get('subtitle') or legacy.get('short_description') or catalog.get('short_description'))
    description = _text(v2.get('full_description') or legacy.get('description') or catalog.get('description'))

    media: list[dict] = []
    media_by_path: dict[str, str] = {}
    skus: list[dict] = []
    map_skus: list[dict] = []
    catalog_skus = [x for x in (catalog.get('skus') or []) if isinstance(x, dict)]
    fallback_image = _product_image(legacy, catalog)

    if not catalog_skus:
        raise RuntimeError(f'{target}: catalog product has no SKU; refusing to guess commerce mapping')

    for i, sku in enumerate(catalog_skus):
        commerce_key = str(sku.get('id') or sku.get('sku') or '').strip()
        if not commerce_key:
            raise RuntimeError(f'{target}: SKU #{i + 1} has no commerce key')
        path = _sku_image(sku) or fallback_image
        primary = None
        if path:
            if path not in media_by_path:
                entry = _media_entry(path, title, len(media))
                media.append(entry)
                media_by_path[path] = entry['media_id']
            primary = media_by_path[path]
        sku_id = _sha('sku_', product_id + '|' + commerce_key)
        label = _text(sku.get('variant') or sku.get('label') or sku.get('name') or commerce_key)
        package = _text(sku.get('variant') or sku.get('volume_weight') or sku.get('pack') or label)
        skus.append({
            'sku_id': sku_id,
            'sku_code': commerce_key,
            'label': label,
            'package': package,
            'primary_media_id': primary,
            'gallery_media_ids': [],
            'sort_order': i,
            'enabled': True,
        })
        map_skus.append({'sku_id': sku_id, 'existing_commerce_sku_key': commerce_key})

    card = {
        'schema_version': '3.0',
        'product_id': product_id,
        'slug': slug,
        'enabled': True,
        'content': {
            'title': title,
            'brand': brand,
            'category': category,
            'short_description': short,
            'description': description,
            'benefits': _benefits(legacy, v2),
            'how_it_works': _how(legacy, v2),
            'application': _application(legacy, v2),
            'composition': _composition(legacy, v2, catalog),
            'characteristics': _characteristics(legacy, v2),
            'seo': {
                'title': _text((v2.get('seo') or {}).get('title') if isinstance(v2.get('seo'), dict) else ''),
                'description': _text((v2.get('seo') or {}).get('description') if isinstance(v2.get('seo'), dict) else ''),
            },
        },
        'sku_media': {'skus': skus, 'media': media},
    }
    validate(card)

    cmap = {
        'product_id': product_id,
        'existing_product_key': str(catalog_row.get('id') or catalog.get('id') or '').strip(),
        'skus': map_skus,
    }
    report = {
        'name': target,
        'product_id': product_id,
        'slug': slug,
        'legacy_identity': {
            'id': legacy.get('id'),
            'product_id': legacy.get('product_id'),
            'slug': legacy.get('slug'),
            'source_row': (legacy.get('import_meta') or {}).get('organic_planet_source_row') if isinstance(legacy.get('import_meta'), dict) else None,
        },
        'existing_product_key': cmap['existing_product_key'],
        'sku_count': len(skus),
        'commerce_sku_keys': [x['existing_commerce_sku_key'] for x in map_skus],
        'media_paths': [x['path'] for x in media],
        'verification': 'GENERATED_AWAITING_MANUAL_VERIFY',
    }
    return card, cmap, report


def main() -> None:
    cards = _legacy_cards()
    products: list[dict] = []
    mappings: list[dict] = []
    reports: list[dict] = []

    for target in TARGETS:
        legacy = _find_legacy(cards, target)
        catalog_row, catalog = _find_catalog_product(target, legacy)
        card, cmap, report = _build(target, legacy, catalog_row, catalog)
        products.append(card)
        mappings.append(cmap)
        reports.append(report)

    ids = [x['product_id'] for x in products]
    slugs = [x['slug'] for x in products]
    if len(set(ids)) != len(TARGETS) or len(set(slugs)) != len(TARGETS):
        raise RuntimeError('Batch 01 duplicate product_id or slug')

    PRODUCTS.mkdir(parents=True, exist_ok=True)
    # Batch 01 owns only these deterministic product IDs. It never deletes other v3 cards.
    for card in products:
        _save(PRODUCTS / f"{card['product_id']}.json", card)

    index_items = []
    for path in sorted(PRODUCTS.glob('prd_*.json')):
        card = _load(path, None)
        if not isinstance(card, dict):
            continue
        c = card.get('content') or {}
        index_items.append({
            'product_id': card.get('product_id'),
            'slug': card.get('slug'),
            'title': c.get('title', ''),
            'brand': c.get('brand', ''),
            'category': c.get('category', ''),
            'enabled': bool(card.get('enabled')),
            'sku_count': len((card.get('sku_media') or {}).get('skus') or []),
        })
    index_items.sort(key=lambda x: (x.get('title') or '').lower())
    _save(INDEX, {'schema_version': '3.0', 'items': index_items})

    existing_map = _load(COMMERCE_MAP, {'schema_version': '1.0', 'products': []})
    other = [x for x in existing_map.get('products', []) if isinstance(x, dict) and x.get('product_id') not in set(ids)]
    _save(COMMERCE_MAP, {'schema_version': '1.0', 'products': other + mappings})

    _save(MANIFEST, {
        'schema_version': '1.0',
        'batch': 'VALAGRO-01',
        'status': 'GENERATED_AWAITING_MANUAL_VERIFY',
        'count': len(reports),
        'products': reports,
        'protected': ['commerce values', 'prices', 'stock', 'availability', 'publication', 'orders', 'physical media', 'legacy masters'],
    })

    print('PCV3 BATCH 01 GENERATED')
    print(f'Cards: {len(products)}/{len(TARGETS)}')
    for row in reports:
        print(f"PASS GENERATE | {row['name']} | {row['existing_product_key']} | SKU={row['sku_count']} | MEDIA={len(row['media_paths'])}")
    print('Manifest status: GENERATED_AWAITING_MANUAL_VERIFY')
    print('No commerce write API was called by this tool.')


if __name__ == '__main__':
    main()
