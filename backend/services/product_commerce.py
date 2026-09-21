from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..db import connect

VALID_AVAILABILITY = {
    'unknown',
    'in_stock',
    'out_of_stock',
    'preorder',
    'backorder',
    'request_price',
    'legacy_disabled',
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _v5_snapshot():
    from .product_master_v5 import snapshot
    return snapshot(public_only=False)


def _seed_rows_from_v5() -> list[dict]:
    """Return every V5 commerce identity with its current/fallback commerce state."""
    data = _v5_snapshot()
    rows = []
    canonical = {}

    for product in data.get('products') or []:
        for sku in product.get('skus') or []:
            sid = str(sku.get('sku_id') or '').strip()
            if not sid:
                continue
            row = {
                'sku': sid,
                'price': sku.get('price'),
                'sale_price': sku.get('sale_price'),
                'availability': sku.get('availability') or 'unknown',
                'stock_qty': sku.get('stock_qty'),
                'enabled': 1 if sku.get('commerce_enabled') else 0,
                'updated_at': sku.get('updated_at') or _now(),
            }
            rows.append(row)
            canonical[sid] = row

    for alias in data.get('sku_aliases') or []:
        sid = str(alias.get('alias_sku_id') or '').strip()
        if not sid:
            continue
        rows.append({
            'sku': sid,
            'price': alias.get('price'),
            'sale_price': alias.get('sale_price'),
            'availability': alias.get('availability') or 'unknown',
            'stock_qty': alias.get('stock_qty'),
            'enabled': 1 if alias.get('enabled') else 0,
            'updated_at': alias.get('updated_at') or _now(),
        })
    return rows


def seed_from_catalog() -> dict:
    """Backfill operational sku_commerce from Product Master V5.

    Existing production rows are never overwritten. This turns sku_commerce
    into the live commerce source for every canonical V5 SKU and compatibility
    alias while preserving all previously edited prices/stock.
    """
    rows = _seed_rows_from_v5()
    created = []
    with connect() as con:
        for row in rows:
            before = con.total_changes
            con.execute(
                '''
                INSERT OR IGNORE INTO sku_commerce(
                    sku,price,sale_price,availability,stock_qty,enabled,updated_at
                ) VALUES(?,?,?,?,?,?,?)
                ''',
                (
                    row['sku'],
                    row.get('price'),
                    row.get('sale_price'),
                    row.get('availability') or 'unknown',
                    row.get('stock_qty'),
                    row.get('enabled', 0),
                    row.get('updated_at') or _now(),
                ),
            )
            if con.total_changes > before:
                created.append(row['sku'])
        con.commit()
    return {'seen': len(rows), 'created': len(created), 'created_skus': created}


def commerce_map() -> dict[str, dict]:
    seed_from_catalog()
    with connect() as con:
        rows = con.execute(
            '''
            SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at
            FROM sku_commerce
            '''
        ).fetchall()
    out = {}
    for r in rows:
        x = dict(r)
        x['enabled'] = bool(x['enabled'])
        x['effective_price'] = x['sale_price'] if x['sale_price'] is not None else x['price']
        out[x['sku']] = x
    return out


def public_catalog() -> list[dict]:
    return list(commerce_map().values())


def _primary_media(product: dict, sku: dict) -> str:
    media = sku.get('media') or []
    primary = next((x for x in media if x.get('is_primary') and x.get('path')), None)
    if primary:
        return primary['path']
    first = next((x for x in media if x.get('path')), None)
    if first:
        return first['path']
    first_product = next((x for x in (product.get('media') or []) if x.get('path')), None)
    return first_product['path'] if first_product else ''


def admin_products() -> list[dict]:
    """Admin commerce projection from V5 identity + operational commerce only."""
    data = _v5_snapshot()
    cm = commerce_map()
    result = []
    canonical_meta = {}

    for product in data.get('products') or []:
        for sku in product.get('skus') or []:
            sid = str(sku.get('sku_id') or '').strip()
            if not sid:
                continue
            c = cm.get(sid, {})
            row = {
                'sku': sid,
                'canonical_sku_id': sid,
                'legacy_alias': False,
                'product_id': product.get('product_id'),
                'name': product.get('name') or sid,
                'brand': product.get('brand') or '',
                'variant': sku.get('package_label') or sid,
                'package_group': sku.get('package_group'),
                'currency': 'UAH',
                'image': _primary_media(product, sku),
                'price': c.get('price'),
                'sale_price': c.get('sale_price'),
                'effective_price': c.get('effective_price'),
                'availability': c.get('availability', 'unknown'),
                'stock_qty': c.get('stock_qty'),
                'enabled': bool(c.get('enabled')),
                'updated_at': c.get('updated_at'),
                'public_enabled': bool(product.get('public_enabled')),
                'product_status': product.get('status'),
                'source': 'product-master-v5',
            }
            result.append(row)
            canonical_meta[sid] = row

    for alias in data.get('sku_aliases') or []:
        sid = str(alias.get('alias_sku_id') or '').strip()
        canonical_id = str(alias.get('canonical_sku_id') or '').strip()
        meta = canonical_meta.get(canonical_id)
        if not sid or not meta:
            continue
        c = cm.get(sid, {})
        result.append({
            **meta,
            'sku': sid,
            'canonical_sku_id': canonical_id,
            'legacy_alias': True,
            'price': c.get('price'),
            'sale_price': c.get('sale_price'),
            'effective_price': c.get('effective_price'),
            'availability': c.get('availability', 'unknown'),
            'stock_qty': c.get('stock_qty'),
            'enabled': bool(c.get('enabled')),
            'updated_at': c.get('updated_at'),
            'source': 'product-master-v5-alias',
        })

    result.sort(key=lambda x: (
        str(x.get('name') or '').lower(),
        str(x.get('variant') or '').lower(),
        1 if x.get('legacy_alias') else 0,
        str(x.get('sku') or ''),
    ))
    return result


def update_product(
    sku: str,
    *,
    price: Optional[float] = None,
    sale_price: Optional[float] = None,
    sale_price_set: bool = False,
    availability: Optional[str] = None,
    stock_qty: Optional[int] = None,
    stock_qty_set: bool = False,
    enabled: Optional[bool] = None,
) -> dict | None:
    sku = str(sku or '').strip()
    seed_from_catalog()
    with connect() as con:
        exists = con.execute('SELECT 1 FROM sku_commerce WHERE sku=?', (sku,)).fetchone()
    if not exists:
        return None

    if availability is not None and availability not in VALID_AVAILABILITY:
        raise ValueError('Invalid availability')
    if price is not None and price < 0:
        raise ValueError('Price must be >= 0')
    if sale_price is not None and sale_price < 0:
        raise ValueError('Sale price must be >= 0')
    if stock_qty is not None and stock_qty < 0:
        raise ValueError('Stock quantity must be >= 0')

    fields = []
    values = []
    if price is not None:
        fields.append('price=?')
        values.append(price)
    if sale_price_set:
        fields.append('sale_price=?')
        values.append(sale_price)
    if availability is not None:
        fields.append('availability=?')
        values.append(availability)
    if stock_qty_set:
        fields.append('stock_qty=?')
        values.append(stock_qty)
    if enabled is not None:
        fields.append('enabled=?')
        values.append(1 if enabled else 0)

    if not fields:
        return next((x for x in admin_products() if x['sku'] == sku), None)

    fields.append('updated_at=?')
    values.append(_now())
    values.append(sku)
    with connect() as con:
        con.execute(
            'UPDATE sku_commerce SET ' + ','.join(fields) + ' WHERE sku=?',
            values,
        )
        con.commit()

    return next((x for x in admin_products() if x['sku'] == sku), None)
