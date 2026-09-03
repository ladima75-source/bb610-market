from __future__ import annotations
import json
from pathlib import Path
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[2]
CATALOG=ROOT/"data"/"catalog.master.json"

def _load_catalog():
    raw=json.loads(CATALOG.read_text(encoding="utf-8"))
    if isinstance(raw,list): return raw
    if isinstance(raw,dict):
        for k in ("products","items","catalog"):
            if isinstance(raw.get(k),list): return raw[k]
    return []

def _find_product(slug):
    for p in _load_catalog():
        if not isinstance(p,dict): continue
        if str(p.get("slug"))==slug or str(p.get("id"))==slug:
            return p
    return None

def _sku_ids(p):
    out=[]
    for k in ("default_sku_id","sku"):
        v=p.get(k)
        if isinstance(v,str) and v.strip(): out.append(v.strip())
    for k in ("launch_sku_ids","sku_ids"):
        arr=p.get(k)
        if isinstance(arr,list):
            out.extend(str(x).strip() for x in arr if str(x).strip())
    seen=set()
    return [x for x in out if not (x in seen or seen.add(x))]

def _commerce():
    try:
        from .product_commerce import commerce_map
        m=commerce_map()
        return m if isinstance(m,dict) else {}
    except Exception:
        return {}

def _val(d,*keys,default=None):
    for k in keys:
        if isinstance(d,dict) and d.get(k) is not None:
            return d.get(k)
    return default

def _label_from_sku(sku):
    tail=sku.split("-")[-1].upper()
    repl={"ML":" мл","KG":" кг","G":" г","L":" л"}
    for suffix,label in repl.items():
        if tail.endswith(suffix):
            n=tail[:-len(suffix)]
            if n.replace(".","",1).isdigit():
                return n+label
    return tail

def public_product_state(slug):
    p=_find_product(slug)
    if not p: return None
    commerce=_commerce()
    pc=p.get("product_card_v1") if isinstance(p.get("product_card_v1"),dict) else {}
    overrides=pc.get("sku_overrides") if isinstance(pc.get("sku_overrides"),dict) else {}
    main_image=""
    if isinstance(p.get("image"),dict):
        main_image=p["image"].get("local") or ""
    elif isinstance(p.get("image"),str):
        main_image=p["image"]

    items=[]
    for sku in _sku_ids(p):
        c=commerce.get(sku,{}) if isinstance(commerce,dict) else {}
        if not isinstance(c,dict): c={}
        ov=overrides.get(sku,{}) if isinstance(overrides.get(sku),dict) else {}
        availability=str(_val(c,"availability","stock_status","status",default="unknown") or "unknown")
        price=_val(c,"price","base_price","regular_price")
        sale_price=_val(c,"sale_price","promo_price","special_price")
        label=ov.get("label") or _val(c,"pack","packing","size","variant","label") or _label_from_sku(sku)
        image=ov.get("image") or _val(c,"image","image_url","photo") or main_image
        lead_time=ov.get("lead_time") or _val(c,"lead_time","delivery_term",default="")
        sale_enabled=bool(_val(c,"sale_enabled","enabled","active",default=False))
        items.append({
            "sku":sku,
            "label":label,
            "price":price,
            "sale_price":sale_price,
            "availability":availability,
            "lead_time":lead_time,
            "sale_enabled":sale_enabled,
            "image":image,
        })
    return {
        "slug":slug,
        "default_sku":p.get("default_sku_id") or (items[0]["sku"] if items else ""),
        "variants":items
    }
