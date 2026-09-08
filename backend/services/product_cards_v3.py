from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from .catalog_cms import admin_detail as legacy_catalog_detail

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data' / 'product_cards_v3'
PRODUCTS = BASE / 'products'
INDEX = BASE / 'index.json'
COMMERCE_MAP = BASE / 'commerce_map.json'
MIGRATION_MANIFEST = BASE / 'migration_manifest.json'

PRODUCTS.mkdir(parents=True, exist_ok=True)

FORBIDDEN_KEYS = {
    'how', 'how_works', 'specs', 'applications', 'variants', 'sku_photo',
    'price', 'sale_price', 'stock', 'stock_qty', 'availability', 'published',
    'publication', 'offer_status', 'commercial_status'
}

PRODUCT_ID_RE = re.compile(r'^prd_[a-z0-9][a-z0-9_-]{2,80}$')
SKU_ID_RE = re.compile(r'^sku_[a-z0-9][a-z0-9_-]{2,100}$')
SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{1,160}$')


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


def _product_path(product_id: str) -> Path:
    return PRODUCTS / f'{product_id}.json'


def _walk_forbidden(value: Any, prefix: str = '') -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = f'{prefix}.{key}' if prefix else key
            if key in FORBIDDEN_KEYS:
                found.append(here)
            found.extend(_walk_forbidden(child, here))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(_walk_forbidden(child, f'{prefix}[{i}]'))
    return found


def _require_str(obj: dict, key: str, *, nonempty: bool = False) -> str:
    value = obj.get(key)
    if not isinstance(value, str):
        raise ValueError(f'{key} must be a string')
    value = value.strip()
    if nonempty and not value:
        raise ValueError(f'{key} is required')
    return value


def _validate_pair_list(items: Any, *, field: str, first: str, second: str) -> None:
    if not isinstance(items, list):
        raise ValueError(f'{field} must be an array')
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f'{field}[{i}] must be an object')
        if set(item) != {first, second}:
            raise ValueError(f'{field}[{i}] must contain only {first} and {second}')
        if not isinstance(item.get(first), str) or not isinstance(item.get(second), str):
            raise ValueError(f'{field}[{i}] values must be strings')


def validate(card: dict) -> dict:
    if not isinstance(card, dict):
        raise ValueError('Card must be an object')
    forbidden = _walk_forbidden(card)
    if forbidden:
        raise ValueError('Legacy/commerce fields are forbidden in v3: ' + ', '.join(forbidden[:20]))

    allowed_top = {'schema_version', 'product_id', 'slug', 'enabled', 'content', 'sku_media'}
    extra_top = set(card) - allowed_top
    if extra_top:
        raise ValueError('Unknown top-level fields: ' + ', '.join(sorted(extra_top)))

    if card.get('schema_version') != '3.0':
        raise ValueError('schema_version must be 3.0')

    product_id = _require_str(card, 'product_id', nonempty=True)
    if not PRODUCT_ID_RE.fullmatch(product_id):
        raise ValueError('Invalid product_id')

    slug = _require_str(card, 'slug', nonempty=True).lower()
    if not SLUG_RE.fullmatch(slug):
        raise ValueError('Invalid slug')

    if not isinstance(card.get('enabled'), bool):
        raise ValueError('enabled must be boolean')

    content = card.get('content')
    if not isinstance(content, dict):
        raise ValueError('content must be an object')
    allowed_content = {
        'title', 'brand', 'category', 'short_description', 'description',
        'benefits', 'how_it_works', 'application', 'composition',
        'characteristics', 'seo'
    }
    extra = set(content) - allowed_content
    if extra:
        raise ValueError('Unknown content fields: ' + ', '.join(sorted(extra)))
    missing = allowed_content - set(content)
    if missing:
        raise ValueError('Missing content fields: ' + ', '.join(sorted(missing)))
    _require_str(content, 'title', nonempty=True)
    for key in ('brand', 'category', 'short_description', 'description', 'how_it_works', 'application', 'composition'):
        _require_str(content, key)
    _validate_pair_list(content.get('benefits'), field='content.benefits', first='title', second='text')
    _validate_pair_list(content.get('characteristics'), field='content.characteristics', first='label', second='value')

    seo = content.get('seo')
    if not isinstance(seo, dict):
        raise ValueError('content.seo must be an object')
    if set(seo) != {'title', 'description'}:
        raise ValueError('content.seo must contain only title and description')
    _require_str(seo, 'title')
    _require_str(seo, 'description')

    sm = card.get('sku_media')
    if not isinstance(sm, dict) or set(sm) != {'skus', 'media'}:
        raise ValueError('sku_media must contain only skus and media')
    skus = sm.get('skus')
    media = sm.get('media')
    if not isinstance(skus, list) or not skus:
        raise ValueError('At least one SKU is required')
    if not isinstance(media, list):
        raise ValueError('sku_media.media must be an array')

    media_ids: set[str] = set()
    for item in media:
        if not isinstance(item, dict):
            raise ValueError('Media item must be an object')
        allowed = {'media_id', 'path', 'alt', 'kind', 'sort_order'}
        if set(item) != allowed:
            raise ValueError('Media item must contain only media_id, path, alt, kind and sort_order')
        mid = _require_str(item, 'media_id', nonempty=True)
        if mid in media_ids:
            raise ValueError(f'Duplicate media_id: {mid}')
        media_ids.add(mid)
        _require_str(item, 'path', nonempty=True)
        _require_str(item, 'alt')
        _require_str(item, 'kind')
        if not isinstance(item.get('sort_order'), int):
            raise ValueError('media.sort_order must be integer')

    sku_ids: set[str] = set()
    for item in skus:
        if not isinstance(item, dict):
            raise ValueError('SKU item must be an object')
        allowed = {'sku_id', 'sku_code', 'label', 'package', 'primary_media_id', 'gallery_media_ids', 'sort_order', 'enabled'}
        if set(item) != allowed:
            raise ValueError('SKU item has missing or unknown fields')
        sid = _require_str(item, 'sku_id', nonempty=True)
        if not SKU_ID_RE.fullmatch(sid):
            raise ValueError(f'Invalid sku_id: {sid}')
        if sid in sku_ids:
            raise ValueError(f'Duplicate sku_id: {sid}')
        sku_ids.add(sid)
        for key in ('sku_code', 'label', 'package'):
            _require_str(item, key)
        primary = item.get('primary_media_id')
        if primary is not None and (not isinstance(primary, str) or primary not in media_ids):
            raise ValueError(f'Unknown primary_media_id for {sid}')
        gallery = item.get('gallery_media_ids')
        if not isinstance(gallery, list):
            raise ValueError(f'Invalid gallery_media_ids for {sid}')
        if len(gallery) != len(set(gallery)):
            raise ValueError(f'Duplicate gallery_media_ids for {sid}')
        if any(not isinstance(x, str) or x not in media_ids for x in gallery):
            raise ValueError(f'Invalid gallery_media_ids for {sid}')
        if not isinstance(item.get('sort_order'), int):
            raise ValueError('sku.sort_order must be integer')
        if not isinstance(item.get('enabled'), bool):
            raise ValueError('sku.enabled must be boolean')

    return card


def empty_card(title: str = 'Новий товар', slug: Optional[str] = None) -> dict:
    token = uuid.uuid4().hex[:12]
    product_id = f'prd_{token}'
    clean_slug = (slug or f'product-{token}').strip().lower()
    sku_id = f'sku_{token}'
    return {
        'schema_version': '3.0',
        'product_id': product_id,
        'slug': clean_slug,
        'enabled': True,
        'content': {
            'title': title.strip() or 'Новий товар',
            'brand': '',
            'category': '',
            'short_description': '',
            'description': '',
            'benefits': [],
            'how_it_works': '',
            'application': '',
            'composition': '',
            'characteristics': [],
            'seo': {'title': '', 'description': ''}
        },
        'sku_media': {
            'skus': [{
                'sku_id': sku_id,
                'sku_code': '',
                'label': 'Фасування',
                'package': '',
                'primary_media_id': None,
                'gallery_media_ids': [],
                'sort_order': 0,
                'enabled': True
            }],
            'media': []
        }
    }


def get(product_id: str) -> Optional[dict]:
    path = _product_path(product_id)
    if not path.exists():
        return None
    obj = _load(path, None)
    return obj if isinstance(obj, dict) else None


def list_cards() -> list[dict]:
    out = []
    for path in sorted(PRODUCTS.glob('prd_*.json')):
        card = _load(path, None)
        if not isinstance(card, dict):
            continue
        content = card.get('content') or {}
        out.append({
            'product_id': card.get('product_id'),
            'slug': card.get('slug'),
            'title': content.get('title', ''),
            'brand': content.get('brand', ''),
            'category': content.get('category', ''),
            'enabled': bool(card.get('enabled', False)),
            'sku_count': len((card.get('sku_media') or {}).get('skus') or [])
        })
    out.sort(key=lambda x: (x.get('title') or '').lower())
    return out


def _assert_unique(card: dict, *, exclude_product_id: Optional[str] = None) -> None:
    for row in list_cards():
        if exclude_product_id and row.get('product_id') == exclude_product_id:
            continue
        if row.get('product_id') == card['product_id']:
            raise ValueError('product_id already exists')
        if row.get('slug') == card['slug']:
            raise ValueError('slug already exists')


def _rebuild_index() -> None:
    _save(INDEX, {'schema_version': '3.0', 'items': list_cards()})


def create(card: Optional[dict] = None) -> dict:
    obj = deepcopy(card) if isinstance(card, dict) else empty_card()
    validate(obj)
    _assert_unique(obj)
    _save(_product_path(obj['product_id']), obj)
    _rebuild_index()
    return deepcopy(obj)


def put(product_id: str, card: dict) -> dict:
    current = get(product_id)
    if not current:
        raise KeyError('Product card v3 not found')
    obj = deepcopy(card)
    if obj.get('product_id') != product_id:
        raise ValueError('product_id is immutable')
    validate(obj)
    _assert_unique(obj, exclude_product_id=product_id)
    _save(_product_path(product_id), obj)
    _rebuild_index()
    return deepcopy(obj)


def commerce_map() -> dict:
    obj = _load(COMMERCE_MAP, {'schema_version': '1.0', 'products': []})
    return obj if isinstance(obj, dict) else {'schema_version': '1.0', 'products': []}


def commerce_view(product_id: str) -> dict:
    mapping = next((x for x in commerce_map().get('products', []) if x.get('product_id') == product_id), None)
    if not mapping:
        return {'product_id': product_id, 'mapped': False, 'mapping': None, 'commerce': None}
    legacy_key = str(mapping.get('existing_product_key') or '').strip()
    detail = legacy_catalog_detail(legacy_key) if legacy_key else None
    return {'product_id': product_id, 'mapped': bool(detail), 'mapping': mapping, 'commerce': detail}
