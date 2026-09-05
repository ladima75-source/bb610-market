#!/usr/bin/env python3
from pathlib import Path
import csv, json, re, sys
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/bb610-market").resolve()

MASTER_CANDIDATES = [
    ROOT/"data/product_cards.master.json",
    ROOT/"data/product-cards.master.json",
]
CATALOG_CANDIDATES = [
    ROOT/"data/catalog.master.json",
    ROOT/"data/catalog.json",
    ROOT/"data/catalog.runtime.json",
]

IMAGE_EXTS={".jpg",".jpeg",".png",".webp",".avif",".gif",".svg"}

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_master():
    for p in MASTER_CANDIDATES:
        if p.exists():
            return p, load_json(p)
    raise SystemExit("ERROR: product card master not found")

def collection(obj):
    if isinstance(obj,list):
        return [x for x in obj if isinstance(x,dict)]
    if isinstance(obj,dict):
        for k in ("products","cards","items"):
            v=obj.get(k)
            if isinstance(v,list):
                return [x for x in v if isinstance(x,dict)]
            if isinstance(v,dict):
                return [x for x in v.values() if isinstance(x,dict)]
        return [x for x in obj.values() if isinstance(x,dict)]
    return []

def source_row(card):
    m=card.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None:
                    return int(m.get(k))
            except Exception:
                pass
    return None

def norm(s):
    s=str(s or "").lower().replace("ё","е")
    s=re.sub(r"[^a-z0-9а-яіїєґ]+","-",s,flags=re.I)
    return re.sub(r"-+","-",s).strip("-")

def tokens(s):
    bad={"bb610","vlg","sku","product","img","image","photo","real","assets","media","jpg","jpeg","png","webp","avif"}
    return {x for x in norm(s).split("-") if len(x)>=3 and x not in bad}

def variants(card):
    for k in ("variants","skus","offers"):
        v=card.get(k)
        if isinstance(v,list):
            return [x for x in v if isinstance(x,dict)]
        if isinstance(v,dict):
            return [x for x in v.values() if isinstance(x,dict)]
    return []

def sku_of(v):
    for k in ("sku","id","variant_id"):
        x=v.get(k)
        if isinstance(x,str) and x.strip():
            return x.strip()
    return ""

def product_id(card):
    for k in ("id","product_id","slug"):
        x=card.get(k)
        if isinstance(x,str) and x.strip():
            return x.strip()
    m=card.get("import_meta")
    if isinstance(m,dict):
        for k in ("product_id","source_product_id","slug"):
            x=m.get(k)
            if isinstance(x,str) and x.strip():
                return x.strip()
    return ""

def image_from_obj(obj):
    keys=("image","image_url","primary_image","main_image","photo","photo_url","thumbnail")
    for k in keys:
        v=obj.get(k) if isinstance(obj,dict) else None
        if isinstance(v,str) and v.strip():
            return v.strip()
    imgs=obj.get("images") if isinstance(obj,dict) else None
    if isinstance(imgs,list):
        for x in imgs:
            if isinstance(x,str) and x.strip():
                return x.strip()
            if isinstance(x,dict):
                for k in ("url","src","path","image"):
                    v=x.get(k)
                    if isinstance(v,str) and v.strip():
                        return v.strip()
    return ""

def source_bucket(st):
    s=(st or "").lower()
    if "conflict" in s: return "SOURCE_CONFLICT"
    if "unverified" in s or "legacy" in s: return "NEED_LABEL"
    if "technical_match" in s: return "TECH_MATCH"
    if "supplier" in s or "market" in s: return "SUPPLIER_SOURCE"
    if "registration" in s: return "REGISTRATION_MARKET"
    return "OFFICIAL_MANUFACTURER"

def content_status(card):
    req=("name","subtitle","lead","full_description","why","application","specs","sources")
    missing=[k for k in req if card.get(k) in (None,"",[],{})]
    sb=source_bucket((card.get("sources") or {}).get("source_type","") if isinstance(card.get("sources"),dict) else "")
    if missing: return "CONTENT_GAPS",missing,sb
    if sb=="SOURCE_CONFLICT": return "SOURCE_CONFLICT",[],sb
    if sb=="NEED_LABEL": return "NEED_LABEL",[],sb
    return "CONTENT_READY",[],sb

def commerce_map():
    try:
        sys.path.insert(0,str(ROOT))
        from backend.services.product_commerce import commerce_map
        x=commerce_map()
        return x if isinstance(x,dict) else {}
    except Exception as e:
        print("WARN: commerce_map unavailable:",repr(e))
        return {}

def effective_price(c):
    if not isinstance(c,dict): return None
    for k in ("effective_price","sale_price","price"):
        v=c.get(k)
        if isinstance(v,(int,float)) and v>0:
            return v
    return None

def relpath(p):
    try:
        return p.relative_to(ROOT).as_posix()
    except Exception:
        return str(p)

def scan_images():
    roots=[
        ROOT/"assets/img/real",
        ROOT/"assets/img/imported",
        ROOT/"assets/media",
        ROOT/"assets/img",
        ROOT/"media",
    ]
    seen=set()
    files=[]
    for base in roots:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS:
                continue
            rp=relpath(p)
            if rp in seen:
                continue
            seen.add(rp)
            files.append({
                "path":rp,
                "name":p.name,
                "stem":norm(p.stem),
                "tokens":tokens(p.stem+" "+rp),
            })
    return files

def load_catalog():
    for p in CATALOG_CANDIDATES:
        if p.exists():
            try:
                return p, load_json(p)
            except Exception:
                pass
    return None,None

def catalog_rows(obj):
    if obj is None: return []
    if isinstance(obj,list): return [x for x in obj if isinstance(x,dict)]
    if isinstance(obj,dict):
        for k in ("products","items","catalog"):
            v=obj.get(k)
            if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
            if isinstance(v,dict): return [x for x in v.values() if isinstance(x,dict)]
        return [x for x in obj.values() if isinstance(x,dict)]
    return []

def build_catalog_image_indexes(obj):
    sku_img={}
    pid_img={}
    for p in catalog_rows(obj):
        pimg=image_from_obj(p)
        pid=str(p.get("id") or p.get("product_id") or p.get("slug") or "").strip()
        if pid and pimg: pid_img[pid]=pimg
        vv=[]
        for k in ("variants","skus","offers"):
            v=p.get(k)
            if isinstance(v,list): vv=[x for x in v if isinstance(x,dict)]; break
            if isinstance(v,dict): vv=[x for x in v.values() if isinstance(x,dict)]; break
        for v in vv:
            sku=sku_of(v)
            img=image_from_obj(v) or pimg
            if sku and img: sku_img[sku]=img
    return sku_img,pid_img

def score_candidate(card, sku, img):
    score=0
    reasons=[]
    p=img["path"].lower()
    stem=img["stem"]
    sku_n=norm(sku)
    pid=norm(product_id(card))
    name_n=norm(card.get("name",""))
    if sku_n and sku_n in norm(p):
        score+=100; reasons.append("sku")
    if pid and pid in norm(p):
        score+=80; reasons.append("product_id")
    if name_n and name_n in norm(p):
        score+=70; reasons.append("name")
    ct=tokens(card.get("name","")+" "+product_id(card)+" "+sku)
    common=ct & img["tokens"]
    if common:
        score += min(30, 8*len(common))
        reasons.append("tokens:"+",".join(sorted(common)))
    return score,reasons

master_path,obj=load_master()
cards=[x for x in collection(obj) if source_row(x) is not None]
cards.sort(key=lambda x:source_row(x))
cm=commerce_map()
images=scan_images()
catalog_path,catalog_obj=load_catalog()
catalog_sku_img,catalog_pid_img=build_catalog_image_indexes(catalog_obj)

rows=[]
card_rows=[]
corrected_counts=defaultdict(int)

for card in cards:
    sr=source_row(card)
    cstatus,missing,sbucket=content_status(card)
    corrected_counts[cstatus]+=1
    corrected_counts[sbucket]+=1
    pid=product_id(card)
    card_embedded=image_from_obj(card)
    vv=variants(card)
    per_card_candidates=set()
    for v in vv:
        sku=sku_of(v)
        vimg=image_from_obj(v)
        existing = vimg or catalog_sku_img.get(sku) or card_embedded or (catalog_pid_img.get(pid) if pid else "")
        status=""
        candidate=""
        confidence=""
        reason=""
        if existing:
            status="EXISTING_IMAGE_REFERENCE"
            candidate=existing
            confidence="EXACT_REFERENCE"
            reason="variant/catalog/card reference"
        else:
            scored=[]
            for img in images:
                sc,rs=score_candidate(card,sku,img)
                if sc>0:
                    scored.append((sc,img["path"],";".join(rs)))
            scored.sort(reverse=True)
            if scored:
                top=scored[0]
                ties=[x for x in scored if x[0]==top[0]]
                candidate=top[1]
                reason=top[2]
                if len(ties)>1:
                    status="AMBIGUOUS_MEDIA_MATCH"
                    confidence="AMBIGUOUS"
                elif top[0]>=100:
                    status="MEDIA_MATCH"
                    confidence="HIGH"
                elif top[0]>=70:
                    status="MEDIA_MATCH"
                    confidence="MEDIUM"
                else:
                    status="MEDIA_CANDIDATE"
                    confidence="LOW"
                per_card_candidates.add(candidate)
            else:
                status="NO_MEDIA_MATCH"
                confidence="NONE"
        cc=cm.get(sku,{}) if sku else {}
        rows.append({
            "source_row":sr,
            "card_name":card.get("name",""),
            "product_id":pid,
            "sku":sku,
            "variant":v.get("variant") or v.get("name") or v.get("label") or "",
            "media_status":status,
            "media_candidate":candidate,
            "media_confidence":confidence,
            "media_reason":reason,
            "price":effective_price(cc),
            "availability":cc.get("availability","") if isinstance(cc,dict) else "",
            "stock_qty":cc.get("stock_qty","") if isinstance(cc,dict) else "",
            "commerce_enabled":bool(cc.get("enabled")) if isinstance(cc,dict) else False,
            "content_status":cstatus,
            "source_status":sbucket,
        })
    media_stats=[r["media_status"] for r in rows if r["source_row"]==sr]
    if any(x=="EXISTING_IMAGE_REFERENCE" for x in media_stats):
        cms="HAS_EXISTING_REFERENCE"
    elif any(x=="MEDIA_MATCH" for x in media_stats):
        cms="HAS_MEDIA_MATCH"
    elif any(x=="AMBIGUOUS_MEDIA_MATCH" for x in media_stats):
        cms="AMBIGUOUS"
    elif any(x=="MEDIA_CANDIDATE" for x in media_stats):
        cms="LOW_CONFIDENCE_CANDIDATE"
    else:
        cms="NO_MEDIA_MATCH"
    card_rows.append({
        "source_row":sr,
        "card_name":card.get("name",""),
        "product_id":pid,
        "variants":len(vv),
        "content_status":cstatus,
        "source_status":sbucket,
        "card_media_status":cms,
        "candidate_count":len(per_card_candidates),
        "commerce_price_variants":sum(1 for r in rows if r["source_row"]==sr and r["price"] is not None),
        "commerce_enabled_variants":sum(1 for r in rows if r["source_row"]==sr and r["commerce_enabled"]),
        "publication_hint":card.get("published",card.get("active",card.get("status",""))),
    })

out=ROOT/"var/import-reports"
out.mkdir(parents=True,exist_ok=True)
csv_sku=out/"stage22e_media_commerce_sku_mapping_latest.csv"
csv_cards=out/"stage22e_media_commerce_card_summary_latest.csv"
js=out/"stage22e_media_commerce_mapping_latest.json"

with csv_sku.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys()) if rows else [])
    w.writeheader(); w.writerows(rows)
with csv_cards.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(card_rows[0].keys()) if card_rows else [])
    w.writeheader(); w.writerows(card_rows)

media_counts=defaultdict(int)
for r in rows: media_counts[r["media_status"]]+=1
card_media_counts=defaultdict(int)
for r in card_rows: card_media_counts[r["card_media_status"]]+=1

payload={
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "master":str(master_path),
    "catalog":str(catalog_path) if catalog_path else None,
    "cards":len(card_rows),
    "variants":len(rows),
    "scanned_media_files":len(images),
    "corrected_content_source_counts":dict(corrected_counts),
    "media_variant_counts":dict(media_counts),
    "media_card_counts":dict(card_media_counts),
    "card_summary":card_rows,
    "sku_mapping":rows,
}
js.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

print("MASTER:",master_path)
print("CATALOG:",catalog_path if catalog_path else "not found")
print("CARDS:",len(card_rows))
print("VARIANTS:",len(rows))
print("SCANNED_MEDIA_FILES:",len(images))
print("")
print("CORRECTED STAGE 22D COUNTS:")
for k in ("CONTENT_READY","NEED_LABEL","SOURCE_CONFLICT","CONTENT_GAPS"):
    print(f"  {k}: {corrected_counts.get(k,0)}")
print("")
print("UNIQUE SOURCE STATUS:")
for k in ("OFFICIAL_MANUFACTURER","TECH_MATCH","SUPPLIER_SOURCE","REGISTRATION_MARKET","NEED_LABEL","SOURCE_CONFLICT"):
    print(f"  {k}: {corrected_counts.get(k,0)}")
print("")
print("MEDIA / VARIANTS:")
for k in ("EXISTING_IMAGE_REFERENCE","MEDIA_MATCH","AMBIGUOUS_MEDIA_MATCH","MEDIA_CANDIDATE","NO_MEDIA_MATCH"):
    print(f"  {k}: {media_counts.get(k,0)}")
print("")
print("MEDIA / CARDS:")
for k in ("HAS_EXISTING_REFERENCE","HAS_MEDIA_MATCH","AMBIGUOUS","LOW_CONFIDENCE_CANDIDATE","NO_MEDIA_MATCH"):
    print(f"  {k}: {card_media_counts.get(k,0)}")
print("")
print("COMMERCE:")
print("  PRICE_CONFIGURED:",sum(1 for r in rows if r["price"] is not None))
print("  AVAILABILITY_CONFIGURED:",sum(1 for r in rows if r["availability"] not in (None,"","unknown")))
print("  COMMERCE_ENABLED:",sum(1 for r in rows if r["commerce_enabled"]))
print("")
print("READ-ONLY: no image assignment, no publication, no commerce changes.")
print("REPORTS:")
print(" ",csv_cards)
print(" ",csv_sku)
print(" ",js)
