
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
    p = ROOT/"data"/"catalog.master.json"
    raw = _load_json(p, {})
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("products","items","catalog"):
            if isinstance(raw.get(key), list):
                return raw[key]
    return []

def _commerce_map():
    # First use the project's own commerce service.
    try:
        from .product_commerce import commerce_map
        m = commerce_map()
        if isinstance(m, dict):
            return m
    except Exception:
        pass

    # Conservative fallback: read common local commerce master files without writing anything.
    for name in ("product_commerce.json","commerce.master.json","commerce.json","sku.commerce.json"):
        p = ROOT/"data"/name
        raw = _load_json(p, {})
        if isinstance(raw, dict):
            if isinstance(raw.get("items"), list):
                out={}
                for x in raw["items"]:
                    if isinstance(x,dict):
                        sku=str(x.get("sku") or x.get("id") or "").strip()
                        if sku: out[sku]=x
                if out:return out
            return raw
    return {}

def _variants(product):
    for key in ("skus","variants","offers"):
        arr=product.get(key)
        if isinstance(arr,list) and arr:
            return arr
    sku=product.get("sku")
    if sku:
        return [{"sku":sku,"pack":product.get("pack") or product.get("size") or product.get("packing")}]
    return []

def rows():
    products=_catalog_products()
    commerce=_commerce_map()
    out=[]
    for p in products:
        if not isinstance(p,dict): continue
        title=str(p.get("title") or p.get("name") or "").strip()
        brand=str(p.get("brand") or "").strip()
        for v in _variants(p):
            if not isinstance(v,dict): continue
            sku=str(v.get("sku") or v.get("id") or "").strip()
            if not sku: continue
            c=commerce.get(sku,{}) if isinstance(commerce,dict) else {}
            if not isinstance(c,dict): c={}
            price=c.get("price", v.get("price"))
            sale_price=c.get("sale_price", c.get("promo_price", v.get("sale_price")))
            availability=c.get("availability", v.get("availability", ""))
            qty=c.get("qty", c.get("quantity", c.get("stock", v.get("qty", v.get("stock")))))
            sale_enabled=c.get("sale_enabled", c.get("enabled", v.get("sale_enabled", False)))
            out.append({
                "product":title,
                "brand":brand,
                "sku":sku,
                "pack":v.get("pack") or v.get("size") or v.get("packing") or "",
                "price":price,
                "sale_price":sale_price,
                "availability":availability,
                "qty":qty,
                "sale_enabled":bool(sale_enabled),
            })
    return out

def diagnostics():
    return {
        "catalog_products": len(_catalog_products()),
        "commerce_records": len(_commerce_map()),
        "rows": len(rows()),
    }
