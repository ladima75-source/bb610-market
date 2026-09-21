from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data' / 'catalog.master.json'

class CatalogError(ValueError): pass

def load_catalog(): return json.loads(CATALOG.read_text(encoding='utf-8'))
def _commerce_map():
    from .services.product_commerce import commerce_map
    return commerce_map()

def resolve_order_items(lines):
    """Resolve checkout lines from Product Master V5 + live sku_commerce.

    The requested SKU is preserved in the order snapshot for backward
    compatibility. Product identity and package metadata come from the V5
    canonical SKU. Price/availability/enabled come from the operational
    sku_commerce row overlaid by product_master_v5.resolve_order_sku().
    """
    from .services.product_master_v5 import resolve_order_sku

    category_labels = {
        'nutrition': 'Живлення',
        'biostimulation': 'Біостимуляція',
        'containers': 'Горщики',
        'protection': 'Захист рослин',
        'other': 'Інше',
    }
    result = []
    for line in lines:
        requested_sku = str(line['sku']).strip()
        qty = int(line['quantity'])
        if qty < 1:
            raise CatalogError(f'Invalid quantity for SKU: {requested_sku}')

        row = resolve_order_sku(requested_sku)
        if not row:
            raise CatalogError(f'Unknown SKU: {requested_sku}')
        if not bool(row.get('identity_enabled')):
            raise CatalogError(f'SKU identity is disabled: {requested_sku}')
        if not bool(row.get('public_enabled')) or row.get('status') != 'active':
            raise CatalogError(f'Product is not public: {requested_sku}')
        if not bool(row.get('enabled')):
            raise CatalogError(f'SKU is not active: {requested_sku}')

        sale = row.get('sale_price')
        base = row.get('price')
        effective = sale if sale is not None else base
        if effective is None:
            raise CatalogError(f'Price is not configured: {requested_sku}')

        availability = row.get('availability')
        if availability in (None, 'unknown', 'out_of_stock', 'request_price', 'legacy_disabled'):
            raise CatalogError(f'SKU is unavailable: {requested_sku}')

        price = float(effective)
        product_id = row['product_id']
        category_id = row.get('category_id') or 'other'
        variant = row.get('package_label') or requested_sku
        snapshot = {
            'requested_sku': requested_sku,
            'canonical_sku': row['canonical_sku_id'],
            'commerce_source': row.get('commerce_source'),
            'sku': {
                'id': requested_sku,
                'canonical_sku_id': row['canonical_sku_id'],
                'product_id': product_id,
                'manufacturer_sku': row.get('manufacturer_sku'),
                'variant': variant,
                'package_value': row.get('package_value'),
                'package_unit': row.get('package_unit'),
                'package_group': row.get('package_group'),
                'attributes': row.get('attributes') or {},
                'price': price,
                'base_price': base,
                'sale_price': sale,
                'availability': availability,
                'stock_qty': row.get('stock_qty'),
                'commercial_status': 'active',
                'offer_status': 'active',
            },
            'product': {
                'id': product_id,
                'slug': row.get('slug'),
                'name': row.get('name'),
                'brand': row.get('brand'),
                'manufacturer': row.get('manufacturer'),
                'category_id': category_id,
            },
        }
        result.append({
            'sku': requested_sku,
            'product_id': product_id,
            'name': row.get('name') or requested_sku,
            'brand': row.get('brand'),
            'category': category_labels.get(category_id, category_id),
            'variant': variant,
            'unit_price': price,
            'quantity': qty,
            'line_total': round(price * qty, 2),
            'currency': 'UAH',
            'snapshot': snapshot,
        })
    return result

