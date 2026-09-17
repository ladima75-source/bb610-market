from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import update_valagro_batch_v2_migrate as base

RUNTIME_CATALOG = ROOT / 'data' / 'catalog.runtime.js'
PREFIX = 'window.BB610_CATALOG = '


def _load_runtime_catalog() -> dict:
    raw = RUNTIME_CATALOG.read_text(encoding='utf-8').strip()
    if not raw.startswith(PREFIX):
        raise ValueError('catalog.runtime.js has unexpected format')
    payload = raw[len(PREFIX):].strip()
    if payload.endswith(';'):
        payload = payload[:-1].rstrip()
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError('catalog.runtime.js root is not an object')
    return data


def runtime_detail(slug: str) -> dict:
    slug = str(slug or '').strip().lower()
    data = _load_runtime_catalog()
    matches = [
        p for p in (data.get('products') or [])
        if isinstance(p, dict) and (
            str(p.get('id') or '').strip().lower() == slug
            or str(p.get('slug') or '').strip().lower() == slug
        )
    ]
    if len(matches) != 1:
        raise ValueError(f'{slug}: exact runtime product not found or ambiguous')

    product = deepcopy(matches[0])
    product_id = str(product.get('id') or '').strip()
    skus = [
        deepcopy(s) for s in (data.get('skus') or [])
        if isinstance(s, dict) and str(s.get('product_id') or '').strip() == product_id
    ]
    if not skus:
        raise ValueError(f'{slug}: runtime product has no SKUs')

    product['skus'] = skus
    product.setdefault('slug', slug)
    product.setdefault('category_id', product.get('category') or 'nutrition')
    return product


_original_resolve = base._resolve_legacy


def resolve_with_runtime_fallback(catalog_cms, slug: str) -> dict:
    try:
        return _original_resolve(catalog_cms, slug)
    except ValueError:
        return runtime_detail(slug)


base._resolve_legacy = resolve_with_runtime_fallback


if __name__ == '__main__':
    raise SystemExit(base.main())
