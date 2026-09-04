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


# === BB610 STAGE20A3 FIX2 CATALOG SKU COMMERCE AUTOCREATE ===
_bb610_seed_from_catalog_base = seed_from_catalog
_bb610_update_product_base = update_product

def _bb610_catalog_products():
    import json as _json
    from pathlib import Path as _Path
    root=_Path(__file__).resolve().parents[2]
    path=root/"data"/"catalog.master.json"
    raw=_json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw,list):
        return raw
    if isinstance(raw,dict):
        for k in ("products","items","catalog"):
            if isinstance(raw.get(k),list):
                return raw[k]
    return []

def _bb610_catalog_sku_map():
    result={}
    for product in _bb610_catalog_products():
        if not isinstance(product,dict):
            continue
        pid=str(product.get("id") or product.get("slug") or "").strip()
        skus=[]
        for k in ("default_sku_id","sku"):
            v=product.get(k)
            if isinstance(v,str) and v.strip():
                skus.append(v.strip())
        for k in ("launch_sku_ids","sku_ids"):
            arr=product.get(k)
            if isinstance(arr,list):
                skus.extend(str(x).strip() for x in arr if str(x).strip())
        arr=product.get("skus")
        if isinstance(arr,list):
            for item in arr:
                if isinstance(item,dict):
                    v=item.get("sku") or item.get("id")
                    if v:
                        skus.append(str(v).strip())
                elif isinstance(item,str) and item.strip():
                    skus.append(item.strip())
        for sku in skus:
            if sku:
                result.setdefault(sku, pid or sku)
    return result

def _bb610_insert_missing_commerce_row(sku):
    import datetime as _dt
    sku=str(sku or "").strip()
    if not sku:
        return False
    sku_map=_bb610_catalog_sku_map()
    if sku not in sku_map:
        return False
    with connect() as con:
        if con.execute("SELECT 1 FROM sku_commerce WHERE sku=?",(sku,)).fetchone():
            return False
        cols=con.execute("PRAGMA table_info(sku_commerce)").fetchall()
        if not cols:
            raise RuntimeError("sku_commerce table not found")
        info={row[1]:row for row in cols}
        candidates={
            "sku":sku,
            "product_id":sku_map.get(sku) or sku,
            "price":None,
            "sale_price":None,
            "availability":"unknown",
            "stock_qty":None,
            "enabled":0,
            "updated_at":_dt.datetime.now(_dt.timezone.utc).isoformat(),
        }
        fields=[c for c in info if c in candidates]
        missing_required=[]
        for col,row in info.items():
            cid,name,ctype,notnull,dflt,pk=row
            if pk:
                continue
            if notnull and dflt is None and col not in fields:
                missing_required.append(col)
        if missing_required:
            raise RuntimeError("unsupported required sku_commerce columns: "+", ".join(missing_required))
        vals=[candidates[c] for c in fields]
        sql=("INSERT OR IGNORE INTO sku_commerce ("+", ".join(fields)+") VALUES ("+", ".join("?" for _ in fields)+")")
        con.execute(sql, vals)
        con.commit()
        return bool(con.execute("SELECT 1 FROM sku_commerce WHERE sku=?",(sku,)).fetchone())

def _bb610_sync_catalog_skus_to_commerce():
    sku_map=_bb610_catalog_sku_map()
    created=[]
    for sku in sku_map:
        if _bb610_insert_missing_commerce_row(sku):
            created.append(sku)
    return {"seen":len(sku_map),"created":len(created),"created_skus":created}

def seed_from_catalog():
    _bb610_seed_from_catalog_base()
    return _bb610_sync_catalog_skus_to_commerce()

def update_product(sku:str, *, price=None, sale_price=None, sale_price_set=False,
                   availability=None, stock_qty=None, stock_qty_set=False,
                   enabled=None):
    _bb610_insert_missing_commerce_row(sku)
    return _bb610_update_product_base(
        sku,
        price=price,
        sale_price=sale_price,
        sale_price_set=sale_price_set,
        availability=availability,
        stock_qty=stock_qty,
        stock_qty_set=stock_qty_set,
        enabled=enabled,
    )

