from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from . import product_cards_v3 as v3
from .catalog_cms import admin_detail as catalog_detail


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


def _commerce_skus(detail: Optional[dict]) -> dict[str, dict]:
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


def _project_commerce(row: Optional[dict]) -> Optional[dict]:
    if not isinstance(row, dict):
        return None
    # Read-only projection. Keep the live commerce source authoritative and
    # expose only fields needed by the storefront. Nothing here is persisted.
    return {
        'sku': str(row.get('id') or row.get('sku') or ''),
        'price': row.get('price'),
        'base_price': row.get('base_price'),
        'sale_price': row.get('sale_price'),
        'currency': row.get('currency') or 'UAH',
        'availability': row.get('availability') or 'unknown',
        'stock_qty': row.get('stock_qty'),
        'stock_label': row.get('stock_label') or '',
        'offer_status': row.get('offer_status') or '',
        'commercial_status': row.get('commercial_status') or '',
        'url': row.get('url') or '',
    }


def storefront_runtime(slug: str) -> Optional[dict]:
    card = _find_card_by_slug(slug)
    if not card:
        return None

    product_id = str(card.get('product_id') or '')
    mapping = _mapping(product_id) or {}
    existing_product_key = str(mapping.get('existing_product_key') or '').strip()
    detail = catalog_detail(existing_product_key) if existing_product_key else None

    # Publication remains owned by the existing catalog/commerce layer.
    # If that layer explicitly marks the product unpublished, v3 must not
    # independently publish it through this endpoint.
    if isinstance(detail, dict) and detail.get('published') is False:
        return None

    bound_by_v3_sku = {
        str(x.get('sku_id')): str(x.get('existing_commerce_sku_key') or '').strip()
        for x in (mapping.get('skus') or [])
        if isinstance(x, dict) and x.get('sku_id')
    }
    live_by_key = _commerce_skus(detail)
    media_by_id = _media_map(card)

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
            'commerce': _project_commerce(live),
        })

    content = deepcopy(card.get('content') or {})
    return {
        'runtime_version': '3.0',
        'source': 'product-card-v3',
        'product_id': product_id,
        'slug': card.get('slug'),
        'content': content,
        'skus': runtime_skus,
        'commerce_product_key': existing_product_key,
        'commerce_product_published': detail.get('published') if isinstance(detail, dict) else None,
        'commerce_binding': {
            'total': len(runtime_skus),
            'bound': sum(1 for x in runtime_skus if x.get('commerce_bound')),
            'unbound': sum(1 for x in runtime_skus if not x.get('commerce_bound')),
        },
    }
