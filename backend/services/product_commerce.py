from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from ..db import connect
from ..catalog_provider import load_catalog

VALID_AVAILABILITY={'unknown','in_stock','out_of_stock','preorder','backorder'}

def _now(): return datetime.now(timezone.utc).isoformat()

def seed_from_catalog() -> None:
    data=load_catalog()
    with connect() as con:
        for s in data.get('skus',[]):
            enabled=1 if s.get('commercial_status')=='active' and s.get('offer_status')=='active' else 0
            con.execute('INSERT OR IGNORE INTO sku_commerce(sku,price,sale_price,availability,stock_qty,enabled,updated_at) VALUES(?,?,?,?,?,?,?)',
                        (s['id'],s.get('price'),None,s.get('availability') or 'unknown',None,enabled,_now()))
        con.commit()

def commerce_map() -> dict[str,dict]:
    seed_from_catalog()
    with connect() as con:
        rows=con.execute('SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce').fetchall()
    out={}
    for r in rows:
        x=dict(r); x['enabled']=bool(x['enabled'])
        x['effective_price']=x['sale_price'] if x['sale_price'] is not None else x['price']
        out[x['sku']]=x
    return out

def public_catalog() -> list[dict]:
    return list(commerce_map().values())

def admin_products() -> list[dict]:
    data=load_catalog(); products={p['id']:p for p in data.get('products',[])}; cm=commerce_map(); result=[]
    skus=list(data.get('skus',[]))
    try:
        from .catalog_cms import _dynamic_skus, _overrides
        ov=_overrides()
        for pid,c in ov.items():
            if pid in products: products[pid]={**products[pid],**{k:v for k,v in c.items() if not k.startswith('cms_')}}
            else: products[pid]=c
        skus += _dynamic_skus()
    except Exception:
        pass
    seen=set()
    for s in skus:
        sid=s.get('id') or s.get('sku')
        if not sid or sid in seen: continue
        seen.add(sid); p=products.get(s.get('product_id'),{}); c=cm.get(sid,{})
        result.append({'sku':sid,'product_id':s.get('product_id'),'name':p.get('name') or sid,'brand':p.get('brand'),
                       'variant':s.get('variant'),'currency':s.get('currency','UAH'),'image':s.get('image') or (p.get('image',{}).get('local') if isinstance(p.get('image'),dict) else p.get('image')),
                       'price':c.get('price'),'sale_price':c.get('sale_price'),'effective_price':c.get('effective_price'),
                       'availability':c.get('availability','unknown'),'stock_qty':c.get('stock_qty'),'enabled':bool(c.get('enabled')),
                       'updated_at':c.get('updated_at')})
    return result

def update_product(sku:str, *, price:Optional[float]=None, sale_price:Optional[float]=None, sale_price_set:bool=False,
                   availability:Optional[str]=None, stock_qty:Optional[int]=None, stock_qty_set:bool=False,
                   enabled:Optional[bool]=None) -> dict|None:
    seed_from_catalog(); cm=commerce_map()
    if sku not in cm: return None
    if availability is not None and availability not in VALID_AVAILABILITY: raise ValueError('Invalid availability')
    if price is not None and price < 0: raise ValueError('Price must be >= 0')
    if sale_price is not None and sale_price < 0: raise ValueError('Sale price must be >= 0')
    if stock_qty is not None and stock_qty < 0: raise ValueError('Stock quantity must be >= 0')
    fields=[]; values=[]
    if price is not None: fields.append('price=?'); values.append(price)
    if sale_price_set: fields.append('sale_price=?'); values.append(sale_price)
    if availability is not None: fields.append('availability=?'); values.append(availability)
    if stock_qty_set: fields.append('stock_qty=?'); values.append(stock_qty)
    if enabled is not None: fields.append('enabled=?'); values.append(1 if enabled else 0)
    fields.append('updated_at=?'); values.append(_now()); values.append(sku)
    with connect() as con:
        con.execute('UPDATE sku_commerce SET '+','.join(fields)+' WHERE sku=?',values); con.commit()
    return next((x for x in admin_products() if x['sku']==sku),None)
