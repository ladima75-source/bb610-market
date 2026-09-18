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


MARKET_TEST_BRANDS = {'plantlogic'}


def _public_media_path(path: Any) -> str:
    raw = str(path or '').strip()
    if not raw:
        return ''
    if raw.startswith('/media/'):
        return raw
    if raw.startswith('media/'):
        return '/' + raw
    return raw


def _media_index(card: dict) -> dict[str, dict]:
    return {
        str(row.get('media_id') or ''): row
        for row in ((card.get('sku_media') or {}).get('media') or [])
        if isinstance(row, dict) and row.get('media_id')
    }


def _market_test(card: dict) -> bool:
    content = card.get('content') if isinstance(card.get('content'), dict) else {}
    return (
        bool(card.get('enabled'))
        and str(content.get('brand') or '').strip().lower() in MARKET_TEST_BRANDS
    )


def _volume_weight(package: Any) -> dict:
    raw = str(package or '').strip().lower().replace(',', '.')
    m = re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*(л|l|шт|pcs?)\b', raw)
    if not m:
        return {'value': 1, 'unit': 'pcs'}
    value = float(m.group(1))
    unit = m.group(2)
    if unit in {'л', 'l'}:
        unit = 'l'
    else:
        unit = 'pcs'
    if value.is_integer():
        value = int(value)
    return {'value': value, 'unit': unit}


def market_test_projection() -> dict[str, list[dict]]:
    """Project enabled Plantlogic V3 drafts into the current catalog UI.

    This is intentionally a non-commerce projection: no price or stock is
    invented. Every projected SKU is marked as request-price/backorder and is
    not eligible for the cart. The browser renders a dedicated price-request
    CTA instead.
    """
    mappings = _mapping_by_product()
    products: list[dict] = []
    skus: list[dict] = []

    if not PRODUCTS.exists():
        return {'products': products, 'skus': skus}

    for path in sorted(PRODUCTS.glob('prd_*.json')):
        card = _load(path, None)
        if not isinstance(card, dict) or not _market_test(card):
            continue

        product_id = str(card.get('product_id') or '').strip()
        slug = str(card.get('slug') or '').strip()
        if not product_id or not slug:
            continue

        content = card.get('content') if isinstance(card.get('content'), dict) else {}
        mapping = mappings.get(product_id) or {}
        target = str(mapping.get('existing_product_key') or slug).strip() or slug
        chars = _characteristics(content)
        media = _media_index(card)

        enabled_skus = [
            row for row in ((card.get('sku_media') or {}).get('skus') or [])
            if isinstance(row, dict) and row.get('enabled') is not False
        ]
        enabled_skus.sort(key=lambda row: int(row.get('sort_order') or 0))

        projected_skus: list[dict] = []
        gallery: list[str] = []
        for sku in enabled_skus:
            public_sku = str(sku.get('sku_code') or sku.get('sku_id') or '').strip()
            if not public_sku:
                continue
            primary = media.get(str(sku.get('primary_media_id') or '')) or {}
            image = _public_media_path(primary.get('path'))
            for mid in sku.get('gallery_media_ids') or []:
                grow = media.get(str(mid)) or {}
                gpath = _public_media_path(grow.get('path'))
                if gpath and gpath not in gallery:
                    gallery.append(gpath)
            if image and image not in gallery:
                gallery.append(image)

            projected = {
                'id': public_sku,
                'sku': public_sku,
                'product_id': target,
                'variant_id': f"{target}--{public_sku.lower()}",
                'slug': slug,
                'variant': str(sku.get('label') or sku.get('package') or public_sku),
                'volume_weight': _volume_weight(sku.get('package')),
                'price': None,
                'sale_price': None,
                'currency': 'UAH',
                'availability': 'backorder',
                'stock_qty': None,
                'stock_label': 'Під замовлення',
                'offer_status': 'request-price',
                'commercial_status': 'request-price',
                'price_request': True,
                'market_test': True,
                'feed_eligible': False,
                'url': f"product.html?id={target}&sku={public_sku}",
                'shipping': ['Умови та термін поставки уточнюємо у відповіді на запит'],
                'image': image,
                'image_alt': str(content.get('title') or ''),
                'enabled': True,
            }
            projected_skus.append(projected)
            skus.append(projected)

        first_image = next((str(x.get('image') or '') for x in projected_skus if x.get('image')), '')
        source_url = _first(chars, 'Офіційне джерело')
        product_type = _first(chars, 'Тип')
        purposes = _split_values(_first(chars, 'Призначення'))
        cultures = _split_values(_first(chars, 'Культури', 'Культура'))
        methods = _split_values(_first(chars, 'Спосіб застосування', 'Метод внесення'))

        patch: dict[str, Any] = {
            'id': target,
            'slug': slug,
            'name': str(content.get('title') or slug),
            'brand': str(content.get('brand') or ''),
            'manufacturer': str(content.get('brand') or ''),
            'category_id': 'containers',
            'product_type': product_type or 'Професійний горщик',
            'short_description': str(content.get('short_description') or ''),
            'manufacturer_use': str(content.get('description') or ''),
            'application': str(content.get('application') or ''),
            'composition': str(content.get('composition') or ''),
            'cultures': cultures,
            'purposes': purposes,
            'applicationMethods': methods,
            'application_methods': methods,
            'image': {'local': first_image} if first_image else {'local': ''},
            'gallery': gallery,
            'source': {
                'title': 'Офіційні матеріали Plantlogic',
                'url': source_url,
            },
            'verification': {
                'verified': True,
                'verifiedAt': '2026-09-18',
            },
            'verified': True,
            'runtime_dynamic': True,
            'runtime_hidden': False,
            'selected_by_bb610': True,
            'legacy_url': f"product.html?id={target}",
            'canonical_product_url': f"product.html?id={target}",
            'default_sku_id': projected_skus[0]['id'] if projected_skus else None,
            'market_test': True,
            'price_request': True,
            'market_test_status': 'Під замовлення',
            'market_test_price_label': 'Ціна за запитом',
            'market_test_cta': 'Запросити ціну',
            'v3_product_id': product_id,
            'v3_facets': True,
        }
        products.append(patch)

    return {'products': products, 'skus': skus}



def _content_media(card: dict) -> tuple[str, list[str]]:
    media = _media_index(card)
    primary = ''
    gallery: list[str] = []
    enabled = [
        row for row in ((card.get('sku_media') or {}).get('skus') or [])
        if isinstance(row, dict) and row.get('enabled') is not False
    ]
    enabled.sort(key=lambda row: int(row.get('sort_order') or 0))
    for sku in enabled:
        row = media.get(str(sku.get('primary_media_id') or '')) or {}
        path = _public_media_path(row.get('path'))
        if path and not primary:
            primary = path
        if path and path not in gallery:
            gallery.append(path)
        for mid in sku.get('gallery_media_ids') or []:
            grow = media.get(str(mid)) or {}
            gpath = _public_media_path(grow.get('path'))
            if gpath and gpath not in gallery:
                gallery.append(gpath)
    return primary, gallery

def catalog_overlays() -> list[dict]:
    """Return content-only overlays used by storefront catalog facets.

    Packaging and availability intentionally stay out of this layer: they belong
    to SKU/commerce. V3 characteristics are the single source for curated
    cultures, purposes, application methods, NPK and active ingredient.

    The long Product Card v3 recipe is never copied into legacy presentation
    fields. ``application`` receives only the short method taxonomy so the
    current catalog filter can keep using its existing method detector without
    polluting the hero/manufacturer recommendation copy.
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
        title = str(content.get('title') or '').strip()
        short = str(content.get('short_description') or '').strip()
        description = str(content.get('description') or '').strip()
        product_type = _first(chars, 'Тип продукту', 'Тип продукта', 'Тип')
        primary_image, gallery = _content_media(card)

        # Product Card v3 is the descriptive storefront source of truth.
        # Legacy catalog identity and SKU/commerce bindings remain untouched.
        if title:
            patch['name'] = title
            patch['official_name'] = title
        if brand:
            patch['brand'] = brand
        if short:
            patch['short_description'] = short
        if description:
            patch['manufacturer_use'] = description
        if product_type:
            patch['product_type'] = product_type
            patch['form'] = product_type
        if primary_image:
            patch['image'] = {'local': primary_image, 'status': 'product-card-v3'}
        if gallery:
            patch['gallery'] = gallery
        if cultures:
            patch['cultures'] = cultures
        if purposes:
            patch['purposes'] = purposes
        if npk and npk != '—':
            patch['npk'] = npk
        if active:
            patch['active_ingredient'] = active
            patch['activeIngredient'] = active
        if methods:
            patch['applicationMethods'] = methods
            patch['application_methods'] = methods
            patch['application'] = '; '.join(methods)
        out.append(patch)
    return out
