from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data' / 'product_cards_v3'
PRODUCTS = BASE / 'products'
COMMERCE_MAP = BASE / 'commerce_map.json'


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _norm_label(value: Any) -> str:
    s = str(value or '').strip().lower().replace('ё', 'е')
    s = re.sub(r'\s+', ' ', s)
    return s


def _split_values(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = [str(x).strip() for x in value]
    else:
        raw = re.split(r'[;\n|]+', str(value or ''))
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        item = item.strip(' ,')
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _characteristics(content: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in content.get('characteristics') or []:
        if not isinstance(row, dict):
            continue
        label = _norm_label(row.get('label'))
        value = str(row.get('value') or '').strip()
        if label and value:
            out[label] = value
    return out


def _first(chars: dict[str, str], *labels: str) -> str:
    for label in labels:
        value = chars.get(_norm_label(label), '').strip()
        if value:
            return value
    return ''


def _mapping_by_product() -> dict[str, dict]:
    obj = _load(COMMERCE_MAP, {'products': []})
    rows = obj.get('products') if isinstance(obj, dict) else []
    return {
        str(row.get('product_id') or ''): row
        for row in (rows or [])
        if isinstance(row, dict) and row.get('product_id')
    }


def catalog_overlays() -> list[dict]:
    """Return content-only overlays used by the storefront catalog facets.

    Packaging and availability intentionally stay out of this layer: they belong
    to SKU/commerce. V3 characteristics are the single source for curated
    cultures, purposes, application methods, NPK and active ingredient.
    """
    mappings = _mapping_by_product()
    out: list[dict] = []
    if not PRODUCTS.exists():
        return out

    for path in sorted(PRODUCTS.glob('prd_*.json')):
        card = _load(path, None)
        if not isinstance(card, dict) or not card.get('enabled', False):
            continue
        product_id = str(card.get('product_id') or '').strip()
        slug = str(card.get('slug') or '').strip()
        mapping = mappings.get(product_id) or {}
        target = str(mapping.get('existing_product_key') or slug).strip()
        if not target:
            continue

        content = card.get('content') if isinstance(card.get('content'), dict) else {}
        chars = _characteristics(content)
        cultures = _split_values(_first(chars, 'Культури', 'Культуры', 'Культура'))
        purposes = _split_values(_first(chars, 'Призначення', 'Назначение'))
        methods = _split_values(_first(chars, 'Спосіб застосування', 'Способ применения', 'Метод внесення'))
        npk = _first(chars, 'NPK', 'Формула NPK')
        active = _first(chars, 'Діюча речовина', 'Действующее вещество', 'Активна речовина')

        patch: dict[str, Any] = {'id': target, 'v3_facets': True}
        brand = str(content.get('brand') or '').strip()
        application = str(content.get('application') or '').strip()
        if brand:
            patch['brand'] = brand
        if cultures:
            patch['cultures'] = cultures
        if purposes:
            patch['purposes'] = purposes
        if npk:
            patch['npk'] = npk
        if active:
            # Keep both spellings: catalog data is snake_case, the current
            # storefront facet reads camelCase.
            patch['active_ingredient'] = active
            patch['activeIngredient'] = active
        if methods or application:
            method_text = '; '.join(methods)
            combined = '\n'.join(x for x in (method_text, application) if x)
            patch['application'] = combined
            patch['manufacturerUse'] = combined
            patch['manufacturer_use'] = combined
        out.append(patch)
    return out
