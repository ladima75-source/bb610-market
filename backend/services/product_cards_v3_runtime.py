from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from . import product_cards_v3 as v3
from .catalog_cms import admin_detail as catalog_detail
from .product_commerce import commerce_map as live_commerce_map


def _find_card_by_slug(slug: str) -> Optional[dict]:
    wanted = str(slug or '').strip().lower()
    if not wanted:
        return None
    row = next((x for x in v3.list_cards() if str(x.get('slug') or '').lower() == wanted), None)
    if not row:
        return None
    card = v3.get(str(row.get('product_id') or ''))
    if not isinstance(card, dict) or not card.get('enabled', False):
        return None
    return card


def _mapping(product_id: str) -> Optional[dict]:
    return next(
        (x for x in v3.commerce_map().get('products', [])
         if isinstance(x, dict) and x.get('product_id') == product_id),
        None,
    )


def _detail_skus(detail: Optional[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in (detail or {}).get('skus') or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get('id') or row.get('sku') or '').strip()
        if key:
            out[key] = row
    return out


def _media_map(card: dict) -> dict[str, dict]:
    return {
        str(x.get('media_id')): x
        for x in ((card.get('sku_media') or {}).get('media') or [])
        if isinstance(x, dict) and x.get('media_id')
    }


def _stock_label(availability: str) -> str:
    return {
        'in_stock': 'В наявності',
        'out_of_stock': 'Немає в наявності',
        'preorder': 'Передзамовлення',
        'backorder': 'Під замовлення',
    }.get(availability, 'Наявність уточнюється')


def _project_commerce(row: Optional[dict], *, sku_key: str = '', meta: Optional[dict] = None) -> Optional[dict]:
    if not isinstance(row, dict):
        return None
    meta = meta if isinstance(meta, dict) else {}
    availability = str(row.get('availability') or 'unknown')
    enabled = bool(row.get('enabled'))
    effective_price = row.get('effective_price')
    if effective_price is None:
        effective_price = row.get('sale_price') if row.get('sale_price') is not None else row.get('price')

    # Commercial values come only from sku_commerce/product_commerce. Catalog
    # detail is optional presentation metadata and must never become a fallback
    # source for price, stock, availability or enabled state.
    return {
        'sku': str(row.get('sku') or row.get('id') or sku_key),
        'price': effective_price,
        'base_price': row.get('price'),
        'sale_price': row.get('sale_price'),
        'currency': meta.get('currency') or row.get('currency') or 'UAH',
        'availability': availability,
        'stock_qty': row.get('stock_qty'),
        'stock_label': meta.get('stock_label') or _stock_label(availability),
        'offer_status': meta.get('offer_status') or ('active' if enabled else 'draft'),
        'commercial_status': meta.get('commercial_status') or ('active' if enabled else 'paused'),
        'url': meta.get('url') or '',
    }


def storefront_runtime(slug: str) -> Optional[dict]:
    card = _find_card_by_slug(slug)
    if not card:
        return None

    product_id = str(card.get('product_id') or '')
    mapping = _mapping(product_id) or {}
    existing_product_key = str(mapping.get('existing_product_key') or '').strip()
    detail = catalog_detail(existing_product_key) if existing_product_key else None

    # Publication remains owned by the existing catalog layer when that layer
    # has an explicit record. Runtime-fallback products may legitimately have no
    # catalog_cms detail, so absence alone must not hide an enabled V3 card.
    if isinstance(detail, dict) and detail.get('published') is False:
        return None

    bound_by_v3_sku = {
        str(x.get('sku_id')): str(x.get('existing_commerce_sku_key') or '').strip()
        for x in (mapping.get('skus') or [])
        if isinstance(x, dict) and x.get('sku_id')
    }

    # sku_commerce is the authoritative live source for price/availability/stock.
    # Do not require catalog_cms.admin_detail() to exist just to resolve commerce:
    # migrated legacy products can be present in runtime catalog identity while
    # being absent from the CMS/static catalog resolver.
    live_by_key = live_commerce_map()
    detail_by_key = _detail_skus(detail)
    media_by_id = _media_map(card)
    content = deepcopy(card.get('content') or {})
    market_test = str(content.get('brand') or '').strip().lower() == 'plantlogic'

    runtime_skus: list[dict[str, Any]] = []
    for sku in sorted(
        [x for x in ((card.get('sku_media') or {}).get('skus') or []) if isinstance(x, dict)],
        key=lambda x: int(x.get('sort_order') or 0),
    ):
        if not sku.get('enabled', True):
            continue
        primary = media_by_id.get(str(sku.get('primary_media_id') or ''))
        gallery = [
            media_by_id[mid]
            for mid in sku.get('gallery_media_ids') or []
            if mid in media_by_id
        ]
        commerce_key = bound_by_v3_sku.get(str(sku.get('sku_id') or ''), '')
        live = live_by_key.get(commerce_key) if commerce_key else None
        runtime_skus.append({
            'sku_id': sku.get('sku_id'),
            'sku_code': sku.get('sku_code') or '',
            'label': sku.get('label') or '',
            'package': sku.get('package') or '',
            'primary_media': deepcopy(primary) if primary else None,
            'gallery_media': deepcopy(gallery),
            'commerce_bound': bool(commerce_key and live),
            'commerce_key': commerce_key,
            'market_test': market_test,
            'price_request': market_test,
            'market_status': 'Під замовлення' if market_test else '',
            'price_label': 'Ціна за запитом' if market_test else '',
            'cta_label': 'Запросити ціну' if market_test else '',
            'commerce': _project_commerce(
                live,
                sku_key=commerce_key,
                meta=detail_by_key.get(commerce_key),
            ),
        })

    return {
        'runtime_version': '3.0',
        'source': 'product-card-v3',
        'product_id': product_id,
        'slug': card.get('slug'),
        'content': content,
        'market_test': {
            'enabled': market_test,
            'status_label': 'Під замовлення' if market_test else '',
            'price_label': 'Ціна за запитом' if market_test else '',
            'cta_label': 'Запросити ціну' if market_test else '',
            'cart_enabled': False if market_test else None,
        },
        'skus': runtime_skus,
        'commerce_product_key': existing_product_key,
        'commerce_product_published': detail.get('published') if isinstance(detail, dict) else None,
        'commerce_binding': {
            'total': len(runtime_skus),
            'bound': sum(1 for x in runtime_skus if x.get('commerce_bound')),
            'unbound': sum(1 for x in runtime_skus if not x.get('commerce_bound')),
        },
    }
