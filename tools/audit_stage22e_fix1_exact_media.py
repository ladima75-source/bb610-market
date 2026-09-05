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
    if not isinstance(obj,dict):
        return ""
    keys=("image","image_url","primary_image","main_image","photo","photo_url","thumbnail")
    for k in keys:
        v=obj.get(k)
        if isinstance(v,str) and v.strip():
            return v.strip()
    imgs=obj.get("images")
    if isinstance(imgs,list):
        for x in imgs:
            if isinstance(x,str) and x.strip():
                return x.strip()
            if isinstance(x,dict):
                for k in ("url","src","path","image"):
                    v=x.get(k)
                    if isinstance(v,str) and v.strip():
                        return v.strip()
    media=obj.get("media")
    if isinstance(media,dict):
        for k in ("main","primary","image","url"):
            v=media.get(k)
            if isinstance(v,str) and v.strip():
                return v.strip()
    return ""

def source_bucket(st):
    s=(st or "").lower()
    if "conflict" in s:
        return "SOURCE_CONFLICT"
    if "unverified" in s or "legacy" in s:
        return "NEED_LABEL"
    if "technical_match" in s:
        return "TECH_MATCH"
    if "supplier" in s or "market" in s:
        return "SUPPLIER_SOURCE"
    if "registration" in s:
        return "REGISTRATION_MARKET"
    return "OFFICIAL_MANUFACTURER"

def content_state(card):
    req=("name","subtitle","lead","full_description","why","application","specs","sources")
    missing=[k for k in req if card.get(k) in (None,"",[],{})]
    sb=source_bucket((card.get("sources") or {}).get("source_type","") if isinstance(card.get("sources"),dict) else "")
    if missing:
        return "CONTENT_GAPS",missing,sb
    if sb=="SOURCE_CONFLICT":
        return "SOURCE_CONFLICT",[],sb
    if sb=="NEED_LABEL":
        return "NEED_LABEL",[],sb
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
    if not isinstance(c,dict):
        return None
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
    if obj is None:
        return []
    return collection(obj)

def build_catalog_image_indexes(obj):
    sku_img={}
    pid_img={}
    for p in catalog_rows(obj):
        pimg=image_from_obj(p)
        pid=str(p.get("id") or p.get("product_id") or p.get("slug") or "").strip()
        if pid and pimg:
            pid_img[pid]=pimg
        for v in variants(p):
            sku=sku_of(v)
            img=image_from_obj(v) or pimg
            if sku and img:
                sku_img[sku]=img
    return sku_img,pid_img

def score_candidate(card, sku, img):
    score=0
    reasons=[]
    pnorm=norm(img["path"])
    sku_n=norm(sku)
    pid=norm(product_id(card))
    name_n=norm(card.get("name",""))
    if sku_n and sku_n in pnorm:
        score+=100; reasons.append("sku")
    if pid and pid in pnorm:
        score+=80; reasons.append("product_id")
    if name_n and name_n in pnorm:
        score+=70; reasons.append("name")
    common=tokens(card.get("name","")+" "+product_id(card)+" "+sku) & img["tokens"]
    if common:
        score += min(30,8*len(common))
        reasons.append("tokens:"+",".join(sorted(common)))
    return score,reasons

master_path,obj=load_master()
cards=[c for c in collection(obj) if source_row(c) is not None]
cards.sort(key=lambda c:source_row(c))
cm=commerce_map()
images=scan_images()
catalog_path,catalog_obj=load_catalog()
catalog_sku_img,catalog_pid_img=build_catalog_image_indexes(catalog_obj)

# Correct counts: content and source are counted separately, once per card.
content_counts=defaultdict(int)
source_counts=defaultdict(int)

card_rows=[]
sku_rows=[]
queue_auto=[]
queue_review=[]
queue_missing=[]

for card in cards:
    sr=source_row(card)
    cstate,missing,sstate=content_state(card)
    content_counts[cstate]+=1
    source_counts[sstate]+=1

    pid=product_id(card)
    card_embedded=image_from_obj(card)
    vv=variants(card)
    variant_results=[]

    for v in vv:
        sku=sku_of(v)
        vimg=image_from_obj(v)
        exact_ref=vimg or catalog_sku_img.get(sku) or card_embedded or (catalog_pid_img.get(pid) if pid else "")
        candidates=[]
        if exact_ref:
            media_status="EXISTING_IMAGE_REFERENCE"
            chosen=exact_ref
            confidence="EXACT"
            top_score=1000
            top_reason="existing reference"
            alt=[]
        else:
            scored=[]
            for img in images:
                sc,rs=score_candidate(card,sku,img)
                if sc>0:
                    scored.append((sc,img["path"],";".join(rs)))
            scored.sort(key=lambda x:(x[0],x[1]), reverse=True)
            alt=scored[:3]
            if not scored:
                media_status="NO_MEDIA_MATCH"
                chosen=""
                confidence="NONE"
                top_score=0
                top_reason=""
            else:
                top_score,chosen,top_reason=scored[0]
                same=[x for x in scored if x[0]==top_score]
                if len(same)>1:
                    media_status="AMBIGUOUS_MEDIA_MATCH"
                    confidence="AMBIGUOUS"
                elif top_score>=100:
                    media_status="MEDIA_MATCH"
                    confidence="HIGH"
                elif top_score>=70:
                    media_status="MEDIA_MATCH"
                    confidence="MEDIUM"
                else:
                    media_status="MEDIA_CANDIDATE"
                    confidence="LOW"

        cc=cm.get(sku,{}) if sku else {}
        r={
            "source_row":sr,
            "card_name":card.get("name",""),
            "product_id":pid,
            "sku":sku,
            "variant":v.get("variant") or v.get("name") or v.get("label") or "",
            "media_status":media_status,
            "chosen_candidate":chosen,
            "confidence":confidence,
            "score":top_score,
            "reason":top_reason,
            "candidate_1":alt[0][1] if len(alt)>0 else "",
            "candidate_2":alt[1][1] if len(alt)>1 else "",
            "candidate_3":alt[2][1] if len(alt)>2 else "",
            "price":effective_price(cc),
            "availability":cc.get("availability","") if isinstance(cc,dict) else "",
            "stock_qty":cc.get("stock_qty","") if isinstance(cc,dict) else "",
            "commerce_enabled":bool(cc.get("enabled")) if isinstance(cc,dict) else False,
            "content_status":cstate,
            "source_status":sstate,
        }
        sku_rows.append(r)
        variant_results.append(r)

        if media_status=="EXISTING_IMAGE_REFERENCE" or (media_status=="MEDIA_MATCH" and confidence=="HIGH"):
            queue_auto.append(r)
        elif media_status in ("MEDIA_MATCH","AMBIGUOUS_MEDIA_MATCH","MEDIA_CANDIDATE"):
            queue_review.append(r)
        else:
            queue_missing.append(r)

    # card-level media result
    statuses=[r["media_status"] for r in variant_results]
    if any(s=="EXISTING_IMAGE_REFERENCE" for s in statuses):
        card_media="HAS_EXISTING_REFERENCE"
    elif any(r["media_status"]=="MEDIA_MATCH" and r["confidence"]=="HIGH" for r in variant_results):
        card_media="HAS_HIGH_CONFIDENCE_MATCH"
    elif any(s=="AMBIGUOUS_MEDIA_MATCH" for s in statuses):
        card_media="AMBIGUOUS"
    elif any(s=="MEDIA_MATCH" for s in statuses):
        card_media="HAS_MEDIUM_MATCH"
    elif any(s=="MEDIA_CANDIDATE" for s in statuses):
        card_media="LOW_CONFIDENCE_CANDIDATE"
    else:
        card_media="NO_MEDIA_MATCH"

    card_rows.append({
        "source_row":sr,
        "card_name":card.get("name",""),
        "product_id":pid,
        "variants":len(vv),
        "content_status":cstate,
        "source_status":sstate,
        "missing_content_fields":"; ".join(missing),
        "card_media_status":card_media,
        "auto_assignable_variants":sum(1 for r in variant_results if r["media_status"]=="EXISTING_IMAGE_REFERENCE" or (r["media_status"]=="MEDIA_MATCH" and r["confidence"]=="HIGH")),
        "review_variants":sum(1 for r in variant_results if r in queue_review),
        "missing_media_variants":sum(1 for r in variant_results if r["media_status"]=="NO_MEDIA_MATCH"),
        "priced_variants":sum(1 for r in variant_results if r["price"] is not None),
        "enabled_variants":sum(1 for r in variant_results if r["commerce_enabled"]),
    })

out=ROOT/"var/import-reports"
out.mkdir(parents=True,exist_ok=True)

paths={
    "card_summary":out/"stage22e_fix1_card_summary_latest.csv",
    "sku_mapping":out/"stage22e_fix1_sku_mapping_latest.csv",
    "auto_queue":out/"stage22e_fix1_auto_media_queue_latest.csv",
    "review_queue":out/"stage22e_fix1_review_media_queue_latest.csv",
    "missing_queue":out/"stage22e_fix1_missing_media_queue_latest.csv",
    "json":out/"stage22e_fix1_exact_media_review_latest.json",
}

def write_csv(path,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        if not rows:
            return
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

write_csv(paths["card_summary"],card_rows)
write_csv(paths["sku_mapping"],sku_rows)
write_csv(paths["auto_queue"],queue_auto)
write_csv(paths["review_queue"],queue_review)
write_csv(paths["missing_queue"],queue_missing)

payload={
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "master":str(master_path),
    "catalog":str(catalog_path) if catalog_path else None,
    "cards":len(card_rows),
    "variants":len(sku_rows),
    "scanned_media_files":len(images),
    "corrected_content_counts":dict(content_counts),
    "corrected_source_counts":dict(source_counts),
    "queues":{
        "auto_assignable":len(queue_auto),
        "manual_review":len(queue_review),
        "missing_media":len(queue_missing),
    },
    "card_summary":card_rows,
}
paths["json"].write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

print("MASTER:",master_path)
print("CATALOG:",catalog_path if catalog_path else "not found")
print("CARDS:",len(card_rows))
print("VARIANTS:",len(sku_rows))
print("SCANNED_MEDIA_FILES:",len(images))
print("")
print("CORRECTED CONTENT COUNTS:")
for k in ("CONTENT_READY","NEED_LABEL","SOURCE_CONFLICT","CONTENT_GAPS"):
    print(f"  {k}: {content_counts.get(k,0)}")
print("")
print("CORRECTED SOURCE COUNTS:")
for k in ("OFFICIAL_MANUFACTURER","TECH_MATCH","SUPPLIER_SOURCE","REGISTRATION_MARKET","NEED_LABEL","SOURCE_CONFLICT"):
    print(f"  {k}: {source_counts.get(k,0)}")
print("")
print("MEDIA QUEUES:")
print("  AUTO_ASSIGNABLE:",len(queue_auto))
print("  MANUAL_REVIEW:",len(queue_review))
print("  MISSING_MEDIA:",len(queue_missing))
print("")
print("COMMERCE:")
print("  PRICE_CONFIGURED:",sum(1 for r in sku_rows if r["price"] is not None))
print("  AVAILABILITY_CONFIGURED:",sum(1 for r in sku_rows if r["availability"] not in (None,"","unknown")))
print("  COMMERCE_ENABLED:",sum(1 for r in sku_rows if r["commerce_enabled"]))
print("")
print("READ-ONLY: no media assignment, no commerce/publication change.")
print("REPORTS:")
for k,p in paths.items():
    print(" ",k,":",p)
