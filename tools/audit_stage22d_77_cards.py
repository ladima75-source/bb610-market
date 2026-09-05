#!/usr/bin/env python3
from pathlib import Path
import csv, json, sys, re
from datetime import datetime, timezone

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/bb610-market").resolve()

def load_master():
    for p in (ROOT/"data/product_cards.master.json", ROOT/"data/product-cards.master.json"):
        if p.exists():
            return p, json.loads(p.read_text(encoding="utf-8"))
    raise SystemExit("ERROR: product_cards master not found")

def collection(obj):
    if isinstance(obj,list): return obj
    if isinstance(obj,dict):
        for k in ("products","cards","items"):
            v=obj.get(k)
            if isinstance(v,list): return v
            if isinstance(v,dict): return [x for x in v.values() if isinstance(x,dict)]
        return [x for x in obj.values() if isinstance(x,dict)]
    return []

def source_row(card):
    m=card.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None: return int(m.get(k))
            except Exception: pass
    return None

def source_bucket(st):
    s=(st or "").lower()
    if "conflict" in s: return "SOURCE_CONFLICT"
    if "unverified" in s or "legacy" in s: return "NEED_LABEL"
    if "technical_match" in s: return "TECH_MATCH"
    if "supplier" in s or "market" in s: return "SUPPLIER_SOURCE"
    if "registration" in s: return "REGISTRATION_MARKET"
    return "OFFICIAL_MANUFACTURER"

def nonempty(v):
    return v not in (None,"",[],{})

def nested_image(card):
    # conservative: only image-like keys / values; do not interpret arbitrary URLs as product photos
    keys=("image","image_url","primary_image","main_image","photo","photo_url","thumbnail")
    for k in keys:
        v=card.get(k)
        if isinstance(v,str) and v.strip(): return v.strip()
    imgs=card.get("images")
    if isinstance(imgs,list):
        for x in imgs:
            if isinstance(x,str) and x.strip(): return x.strip()
            if isinstance(x,dict):
                for k in ("url","src","path","image"):
                    v=x.get(k)
                    if isinstance(v,str) and v.strip(): return v.strip()
    media=card.get("media")
    if isinstance(media,dict):
        for k in ("main","primary","image","url"):
            v=media.get(k)
            if isinstance(v,str) and v.strip(): return v.strip()
    return ""

def variants(card):
    for k in ("variants","skus","offers"):
        v=card.get(k)
        if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
        if isinstance(v,dict): return [x for x in v.values() if isinstance(x,dict)]
    return []

def commerce():
    try:
        sys.path.insert(0,str(ROOT))
        from backend.services.product_commerce import commerce_map
        cm=commerce_map()
        return cm if isinstance(cm,dict) else {}
    except Exception as e:
        print("WARN: commerce_map unavailable:",repr(e))
        return {}

def sku_of(v):
    for k in ("sku","id","variant_id"):
        x=v.get(k)
        if isinstance(x,str) and x.strip(): return x.strip()
    return ""

def effective_price(c):
    if not isinstance(c,dict): return None
    for k in ("effective_price","sale_price","price"):
        v=c.get(k)
        if isinstance(v,(int,float)) and v>0: return v
    return None

master_path,obj=load_master()
cards=[c for c in collection(obj) if source_row(c) is not None]
cards.sort(key=lambda x:source_row(x))
cm=commerce()

outdir=ROOT/"var/import-reports"
outdir.mkdir(parents=True,exist_ok=True)
stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
csv_path=outdir/"stage22d_77_cards_audit_latest.csv"
json_path=outdir/"stage22d_77_cards_audit_latest.json"

rows=[]
counts={}
for card in cards:
    sr=source_row(card)
    req=("name","subtitle","lead","full_description","why","application","specs","sources")
    missing=[k for k in req if not nonempty(card.get(k))]
    st=(card.get("sources") or {}).get("source_type","") if isinstance(card.get("sources"),dict) else ""
    sb=source_bucket(st)
    vs=variants(card)
    skus=[sku_of(v) for v in vs if sku_of(v)]
    crows=[cm.get(s,{}) for s in skus]
    price_count=sum(1 for x in crows if effective_price(x) is not None)
    enabled_count=sum(1 for x in crows if bool(x.get("enabled")) is True)
    availability_count=sum(1 for x in crows if x.get("availability") not in (None,"","unknown"))
    image=nested_image(card)
    if missing:
        content_status="CONTENT_GAPS"
    elif sb=="SOURCE_CONFLICT":
        content_status="SOURCE_CONFLICT"
    elif sb=="NEED_LABEL":
        content_status="NEED_LABEL"
    else:
        content_status="CONTENT_READY"
    counts[content_status]=counts.get(content_status,0)+1
    counts[sb]=counts.get(sb,0)+1
    rows.append({
        "source_row":sr,
        "name":card.get("name",""),
        "brand":card.get("brand",""),
        "category":card.get("category",""),
        "content_status":content_status,
        "source_status":sb,
        "source_type":st,
        "missing_content_fields":"; ".join(missing),
        "variants":len(vs),
        "skus_found":len(skus),
        "prices_configured":price_count,
        "availability_configured":availability_count,
        "commerce_enabled":enabled_count,
        "photo_status":"PHOTO_PRESENT" if image else "MISSING_PHOTO",
        "image":image,
        "published_hint":card.get("published",card.get("active",card.get("status",""))),
        "source_url":(card.get("sources") or {}).get("source_url","") if isinstance(card.get("sources"),dict) else "",
    })

fields=list(rows[0].keys()) if rows else []
with csv_path.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields)
    w.writeheader(); w.writerows(rows)
payload={
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "master":str(master_path),
    "cards":len(rows),
    "counts":counts,
    "rows":rows,
}
json_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

print("MASTER:",master_path)
print("CARDS:",len(rows))
for k in ("CONTENT_READY","NEED_LABEL","SOURCE_CONFLICT","CONTENT_GAPS"):
    print(f"{k}:",counts.get(k,0))
print("SOURCE:")
for k in ("OFFICIAL_MANUFACTURER","TECH_MATCH","SUPPLIER_SOURCE","REGISTRATION_MARKET","NEED_LABEL","SOURCE_CONFLICT"):
    print(f"  {k}: {counts.get(k,0)}")
print("PHOTO_PRESENT:",sum(1 for r in rows if r["photo_status"]=="PHOTO_PRESENT"))
print("MISSING_PHOTO:",sum(1 for r in rows if r["photo_status"]=="MISSING_PHOTO"))
print("VARIANTS:",sum(r["variants"] for r in rows))
print("PRICES_CONFIGURED:",sum(r["prices_configured"] for r in rows))
print("AVAILABILITY_CONFIGURED:",sum(r["availability_configured"] for r in rows))
print("COMMERCE_ENABLED:",sum(r["commerce_enabled"] for r in rows))
print("CSV:",csv_path)
print("JSON:",json_path)
