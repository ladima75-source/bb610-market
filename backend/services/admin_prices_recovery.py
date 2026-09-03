
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def _load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _catalog_products():
    raw=_load_json(ROOT/"data"/"catalog.master.json",{})
    if isinstance(raw,list): return raw
    if isinstance(raw,dict):
        for key in ("products","items","catalog"):
            if isinstance(raw.get(key),list): return raw[key]
    return []

def _commerce_map():
    try:
        from .product_commerce import commerce_map
        m=commerce_map()
        if isinstance(m,dict): return m
    except Exception:
        pass
    return {}

def _sku_ids(product):
    ids=[]
    for key in ("default_sku_id","sku"):
        v=product.get(key)
        if isinstance(v,str) and v.strip():
            ids.append(v.strip())
    for key in ("launch_sku_ids","sku_ids"):
        arr=product.get(key)
        if isinstance(arr,list):
            for v in arr:
                if isinstance(v,str) and v.strip():
                    ids.append(v.strip())
    # stable dedupe
    seen=set()
    return [x for x in ids if not (x in seen or seen.add(x))]

def _value(c,*keys,default=None):
    for k in keys:
        if isinstance(c,dict) and c.get(k) is not None:
            return c.get(k)
    return default

def rows():
    products=_catalog_products()
    commerce=_commerce_map()
    out=[]
    matched=set()

    for p in products:
        if not isinstance(p,dict): continue
        title=str(p.get("name") or p.get("official_name") or p.get("title") or "").strip()
        brand=str(p.get("brand") or "").strip()
        ppack=p.get("pack") or p.get("size") or ""
        ids=_sku_ids(p)

        for sku in ids:
            c=commerce.get(sku,{}) if isinstance(commerce,dict) else {}
            if not isinstance(c,dict): c={}
            matched.add(sku)

            price=_value(c,"price","base_price","regular_price")
            sale_price=_value(c,"sale_price","promo_price","special_price")
            availability=_value(c,"availability","stock_status","status",default="")
            qty=_value(c,"qty","quantity","stock","stock_qty")
            sale_enabled=bool(_value(c,"sale_enabled","enabled","active",default=False))
            pack=_value(c,"pack","packing","size","variant","label",default=ppack or "")
            gtin=_value(c,"gtin","ean","barcode",default="")
            mpn=_value(c,"mpn","manufacturer_part_number",default="")

            out.append({
                "product":title,
                "brand":brand,
                "sku":sku,
                "pack":pack,
                "price":price,
                "sale_price":sale_price,
                "availability":availability,
                "qty":qty,
                "sale_enabled":sale_enabled,
                "gtin":gtin,
                "mpn":mpn,
                "commerce_found": sku in commerce,
            })

    # If commerce contains SKU not referenced by product, keep them visible for diagnosis.
    for sku,c in commerce.items():
        if sku in matched or not isinstance(c,dict): continue
        out.append({
            "product":str(c.get("product_name") or c.get("title") or "SKU без прив'язаної картки"),
            "brand":str(c.get("brand") or ""),
            "sku":str(sku),
            "pack":_value(c,"pack","packing","size","variant","label",default=""),
            "price":_value(c,"price","base_price","regular_price"),
            "sale_price":_value(c,"sale_price","promo_price","special_price"),
            "availability":_value(c,"availability","stock_status","status",default=""),
            "qty":_value(c,"qty","quantity","stock","stock_qty"),
            "sale_enabled":bool(_value(c,"sale_enabled","enabled","active",default=False)),
            "gtin":_value(c,"gtin","ean","barcode",default=""),
            "mpn":_value(c,"mpn","manufacturer_part_number",default=""),
            "commerce_found":True,
        })

    out.sort(key=lambda x:(str(x["product"]).lower(),str(x["pack"]).lower(),str(x["sku"]).lower()))
    return out

def diagnostics():
    products=_catalog_products()
    commerce=_commerce_map()
    referenced=[]
    for p in products:
        if isinstance(p,dict): referenced.extend(_sku_ids(p))
    r=rows()
    return {
        "catalog_products":len(products),
        "commerce_records":len(commerce),
        "referenced_sku_ids":len(set(referenced)),
        "rows":len(r),
        "rows_with_commerce":sum(1 for x in r if x["commerce_found"]),
    }
