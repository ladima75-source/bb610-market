from __future__ import annotations
from copy import deepcopy

def _svc():
    from . import product_commerce as pc
    return pc

def read_map():
    pc=_svc()
    m=pc.commerce_map()
    return deepcopy(m) if isinstance(m,dict) else {}

def update_rows(changes):
    pc=_svc()
    fn=getattr(pc,"update_product",None)
    if not callable(fn):
        raise RuntimeError("product_commerce.update_product() не знайдено")

    results=[]
    for ch in changes:
        sku=str(ch.get("sku") or "").strip()
        if not sku:
            continue

        kwargs={}
        if "price" in ch:
            v=ch.get("price")
            kwargs["price"]=None if v in ("",None) else float(v)

        if "sale_price" in ch:
            v=ch.get("sale_price")
            kwargs["sale_price"]=None if v in ("",None) else float(v)
            kwargs["sale_price_set"]=True

        if "availability" in ch:
            v=str(ch.get("availability") or "").strip()
            if v:
                kwargs["availability"]=v

        if "qty" in ch or "quantity" in ch:
            v=ch.get("qty",ch.get("quantity"))
            kwargs["stock_qty"]=None if v in ("",None) else int(float(v))
            kwargs["stock_qty_set"]=True

        if "sale_enabled" in ch:
            kwargs["enabled"]=bool(ch.get("sale_enabled"))
        elif "enabled" in ch:
            kwargs["enabled"]=bool(ch.get("enabled"))

        before=deepcopy(pc.commerce_map().get(sku))
        returned=fn(sku,**kwargs)

        # Important:
        # legacy update_product() may return None even after a successful SQL UPDATE,
        # because its return value is based on legacy admin_products().
        # Verify success from the authoritative commerce_map instead.
        after=deepcopy(pc.commerce_map().get(sku))
        if after is None:
            raise ValueError(f"SKU не знайдено у commerce після збереження: {sku}")

        results.append({
            "sku":sku,
            "before":before,
            "updated":kwargs,
            "result":after,
            "legacy_return_was_none": returned is None,
        })

    return results
