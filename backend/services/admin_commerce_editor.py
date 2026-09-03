
from __future__ import annotations
from copy import deepcopy

def _svc():
    from . import product_commerce as pc
    return pc

def read_map():
    pc=_svc()
    m=pc.commerce_map()
    return deepcopy(m) if isinstance(m,dict) else {}

def _call_write(pc,sku,patch):
    # Support common service APIs without inventing a new storage format.
    candidates=[
        ("update_commerce",(sku,patch)),
        ("save_commerce",(sku,patch)),
        ("set_commerce",(sku,patch)),
        ("update_sku",(sku,patch)),
        ("save_sku",(sku,patch)),
    ]
    for name,args in candidates:
        fn=getattr(pc,name,None)
        if callable(fn):
            return fn(*args)
    raise RuntimeError("У поточному product_commerce service не знайдено безпечного write-методу")

def update_rows(changes):
    pc=_svc()
    current=pc.commerce_map()
    results=[]
    for ch in changes:
        sku=str(ch.get("sku") or "").strip()
        if not sku: continue
        old=deepcopy(current.get(sku,{})) if isinstance(current,dict) else {}
        patch={}
        for key in ("price","sale_price","qty","quantity","availability","sale_enabled"):
            if key in ch: patch[key]=ch[key]
        _call_write(pc,sku,patch)
        results.append({"sku":sku,"updated":patch,"before":old})
    return results
