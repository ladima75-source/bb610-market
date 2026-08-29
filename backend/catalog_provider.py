from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data' / 'catalog.master.json'

class CatalogError(ValueError): pass

def load_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))

def resolve_order_items(lines):
    data = load_catalog()
    skus = {x['id']: x for x in data.get('skus', [])}
    products = {x['id']: x for x in data.get('products', [])}
    categories = {x['id']: x for x in data.get('categories', [])}
    result=[]
    for line in lines:
        sku_id=line['sku']; qty=int(line['quantity'])
        sku=skus.get(sku_id)
        if not sku: raise CatalogError(f'Unknown SKU: {sku_id}')
        if sku.get('commercial_status')!='active' or sku.get('offer_status')!='active':
            raise CatalogError(f'SKU is not active: {sku_id}')
        if sku.get('price') is None: raise CatalogError(f'Price is not configured: {sku_id}')
        if sku.get('availability') in (None,'unknown','out_of_stock'):
            raise CatalogError(f'SKU is unavailable: {sku_id}')
        if sku.get('currency')!='UAH': raise CatalogError(f'Unsupported currency: {sku_id}')
        p=products.get(sku['product_id']) or {}
        cat=categories.get(p.get('category_id')) or {}
        price=float(sku['price'])
        result.append({
            'sku':sku_id,'product_id':sku['product_id'],'name':p.get('name') or sku_id,
            'brand':p.get('brand'),'category':cat.get('name') or p.get('category_id'),
            'variant':sku.get('variant'),'unit_price':price,'quantity':qty,
            'line_total':round(price*qty,2),'currency':'UAH','snapshot':{'sku':sku,'product':{
                'id':p.get('id'),'name':p.get('name'),'brand':p.get('brand'),'category_id':p.get('category_id')
            }}
        })
    return result
