#!/usr/bin/env python3
from pathlib import Path
import csv, json, re, sys
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/bb610-market").resolve()
REPORTS = ROOT/"var/import-reports"
MASTER_CANDIDATES = [ROOT/"data/product_cards.master.json", ROOT/"data/product-cards.master.json"]
IMAGE_EXTS={".jpg",".jpeg",".png",".webp",".avif"}

GENERIC={"master","plus","npk","fertilizer","fertiliser","dobryvo","удобрение","добриво","valagro","haifa","icl","syngenta","plantlogic","organic","planet","product","image","photo","real","assets","media","stage16b","stage16","img"}

def load_json(p): return json.loads(p.read_text(encoding="utf-8"))
def collection(obj):
    if isinstance(obj,list): return [x for x in obj if isinstance(x,dict)]
    if isinstance(obj,dict):
        for k in ("products","cards","items"):
            v=obj.get(k)
            if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
            if isinstance(v,dict): return [x for x in v.values() if isinstance(x,dict)]
        return [x for x in obj.values() if isinstance(x,dict)]
    return []
def source_row(card):
    m=card.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None: return int(m.get(k))
            except: pass
    return None
def variants(card):
    for k in ("variants","skus","offers"):
        v=card.get(k)
        if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
        if isinstance(v,dict): return [x for x in v.values() if isinstance(x,dict)]
    return []
def sku_of(v):
    for k in ("sku","id","variant_id"):
        x=v.get(k)
        if isinstance(x,str) and x.strip(): return x.strip()
    return ""
def img_of(v):
    for k in ("image","image_url","primary_image","main_image","photo","photo_url","thumbnail"):
        x=v.get(k) if isinstance(v,dict) else None
        if isinstance(x,str) and x.strip(): return x.strip()
    return ""
def norm(s):
    s=str(s or "").lower().replace("ё","е").replace("–","-").replace("—","-")
    s=re.sub(r"[^a-z0-9а-яіїєґ+.-]+"," ",s,flags=re.I)
    return re.sub(r"\s+"," ",s).strip()
def formula(s):
    m=re.search(r'(?<!\d)(\d{1,2}(?:[.,]\d+)?\s*-\s*\d{1,2}(?:[.,]\d+)?\s*-\s*\d{1,2}(?:[.,]\d+)?(?:\s*\+\s*\d{1,2}(?:[.,]\d+)?)?)(?!\d)',norm(s))
    return re.sub(r"\s+","",m.group(1)).replace(",",".") if m else ""
def tokens(s):
    raw=re.split(r"[\s/_,.;:()\[\]{}]+",norm(s))
    out=set()
    for t in raw:
        t=t.strip("-+.")
        if len(t)<3 or t in GENERIC: continue
        if re.fullmatch(r"\d+(?:[.,]\d+)?",t): continue
        out.add(t)
    return out
def scan_images():
    roots=[ROOT/"assets/img/real",ROOT/"assets/img/imported",ROOT/"assets/media",ROOT/"assets/img",ROOT/"media"]
    seen=set(); out=[]
    for base in roots:
        if not base.exists(): continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS: continue
            try: rel=p.relative_to(ROOT).as_posix()
            except: rel=str(p)
            if rel in seen: continue
            seen.add(rel)
            txt=p.stem+" "+rel
            out.append({"path":rel,"formula":formula(txt),"tokens":tokens(txt)})
    return out
def score(card,img):
    cf=formula(card.get("name","")); imf=img["formula"]
    cts=tokens(card.get("name",""))
    if cf and imf and cf != imf:
        return None,"formula_conflict"
    if cf:
        if imf==cf:
            return 300+20*len(cts & img["tokens"]),"exact_formula"
        return None,"formula_missing_or_not_exact"
    common=cts & img["tokens"]
    if not common: return None,"no_distinctive_token"
    return 60+20*len(common),"distinctive_tokens:"+",".join(sorted(common))

master_path=next((p for p in MASTER_CANDIDATES if p.exists()),None)
if not master_path: raise SystemExit("ERROR: product card master not found")
cards=[c for c in collection(load_json(master_path)) if source_row(c) is not None]
cards.sort(key=lambda c:source_row(c))
images=scan_images()

summary=[]; detail=[]; counts=Counter()
for card in cards:
    sr=source_row(card); vv=variants(card)
    unresolved=[v for v in vv if sku_of(v) and not img_of(v)]
    if not unresolved: continue

    scored=[]
    for im in images:
        sc,reason=score(card,im)
        if sc is not None: scored.append((sc,im["path"],reason))
    scored.sort(key=lambda x:(x[0],x[1]),reverse=True)

    cf=formula(card.get("name",""))
    if scored:
        top_score=scored[0][0]
        top=[x for x in scored if x[0]==top_score]
        if len(top)==1 and ((cf and top[0][2]=="exact_formula") or (not cf and top_score>=80)):
            decision="ONE_COMMON_IMAGE"; common_candidate=top[0][1]
        else:
            decision="VARIANT_SPECIFIC"; common_candidate=""
    else:
        decision="MISSING_ONLY"; common_candidate=""
    counts[decision]+=1

    summary.append({
        "source_row":sr,"card_name":card.get("name",""),"brand":card.get("brand",""),
        "total_variants":len(vv),"existing_image_variants":len(vv)-len(unresolved),
        "manual_review_variants":len(unresolved) if decision!="MISSING_ONLY" else 0,
        "missing_media_variants":len(unresolved) if decision=="MISSING_ONLY" else 0,
        "decision_group":decision,"common_candidate":common_candidate,
        "common_candidate_votes":len(unresolved) if common_candidate else 0,
        "formula":cf,
        "review_note":"Строге точне співпадіння за формулою/назвою продукту." if decision=="ONE_COMMON_IMAGE" else ("Потрібен вибір між точними кандидатами." if decision=="VARIANT_SPECIFIC" else "Точного локального кандидата не знайдено.")
    })
    pool=scored[:3]
    for v in unresolved:
        detail.append({
            "source_row":sr,"card_name":card.get("name",""),"sku":sku_of(v),
            "variant":v.get("variant") or v.get("name") or v.get("label") or "",
            "state":"MANUAL_REVIEW" if decision!="MISSING_ONLY" else "MISSING_MEDIA",
            "current_image":"",
            "candidate_1":pool[0][1] if len(pool)>0 else "",
            "candidate_2":pool[1][1] if len(pool)>1 else "",
            "candidate_3":pool[2][1] if len(pool)>2 else "",
            "confidence":"EXACT_PRODUCT" if decision=="ONE_COMMON_IMAGE" else ("REVIEW" if decision=="VARIANT_SPECIFIC" else ""),
            "score":pool[0][0] if pool else "",
            "reason":pool[0][2] if pool else "",
            "group_decision":decision
        })

out_json=REPORTS/"stage22j_exact_media_review_latest.json"
out_csv=REPORTS/"stage22j_exact_media_sku_review_latest.csv"
out_json.write_text(json.dumps({
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "master":str(master_path),
    "scanned_media_files":len(images),
    "cards_requiring_attention":len(summary),
    "decision_groups":dict(counts),
    "summary":summary
},ensure_ascii=False,indent=2),encoding="utf-8")
with out_csv.open("w",encoding="utf-8-sig",newline="") as f:
    if detail:
        w=csv.DictWriter(f,fieldnames=list(detail[0].keys())); w.writeheader(); w.writerows(detail)

print("CARDS_REQUIRING_ATTENTION:",len(summary))
print("DECISION_GROUPS:")
for k in ("ONE_COMMON_IMAGE","VARIANT_SPECIFIC","MISSING_ONLY"):
    print(f"  {k}: {counts.get(k,0)}")
print("SCANNED_MEDIA_FILES:",len(images))
print("REPORTS:")
print(" ",out_json)
print(" ",out_csv)
print("IMPORTANT: wrong-formula candidates are rejected.")
print("IMPORTANT: product master/images/commerce/publication were NOT modified.")
