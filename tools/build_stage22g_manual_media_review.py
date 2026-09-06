#!/usr/bin/env python3
from pathlib import Path
import csv, json, sys, html
from collections import defaultdict, Counter
from datetime import datetime, timezone

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/bb610-market").resolve()
REPORTS = ROOT/"var/import-reports"

REVIEW = REPORTS/"stage22e_fix1_review_media_queue_latest.csv"
MISSING = REPORTS/"stage22e_fix1_missing_media_queue_latest.csv"
MASTER_CANDIDATES = [
    ROOT/"data/product_cards.master.json",
    ROOT/"data/product-cards.master.json",
]

def read_csv(p):
    if not p.exists():
        return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def load_master():
    for p in MASTER_CANDIDATES:
        if p.exists():
            return p, json.loads(p.read_text(encoding="utf-8"))
    raise SystemExit("ERROR: product card master not found")

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
                if m.get(k) is not None:return int(m.get(k))
            except:pass
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

master_path,obj=load_master()
cards=[c for c in collection(obj) if source_row(c) is not None]
cards.sort(key=lambda c:source_row(c))
by_row={source_row(c):c for c in cards}

review=read_csv(REVIEW)
missing=read_csv(MISSING)

review_by=defaultdict(list)
missing_by=defaultdict(list)
for r in review:
    try: review_by[int(r.get("source_row") or 0)].append(r)
    except: pass
for r in missing:
    try: missing_by[int(r.get("source_row") or 0)].append(r)
    except: pass

summary=[]
detail=[]

for sr,card in by_row.items():
    vv=variants(card)
    existing={sku_of(v):img_of(v) for v in vv if sku_of(v)}
    rr=review_by.get(sr,[])
    mm=missing_by.get(sr,[])
    if not rr and not mm:
        continue

    top_candidates=[]
    for r in rr:
        c1=(r.get("candidate_1") or "").strip()
        if c1: top_candidates.append(c1)

    top_count=Counter(top_candidates)
    common_top, common_top_n = ("",0)
    if top_count:
        common_top, common_top_n = top_count.most_common(1)[0]

    review_skus=len(rr)
    missing_skus=len(mm)
    existing_skus=sum(1 for x in existing.values() if x)
    total_skus=len(vv)

    if rr and common_top and common_top_n==review_skus:
        decision="ONE_COMMON_IMAGE"
    elif rr and common_top and review_skus>=2 and common_top_n/review_skus>=0.70:
        decision="MOSTLY_COMMON_IMAGE"
    elif rr:
        decision="VARIANT_SPECIFIC"
    else:
        decision="MISSING_ONLY"

    summary.append({
        "source_row":sr,
        "card_name":card.get("name",""),
        "brand":card.get("brand",""),
        "total_variants":total_skus,
        "existing_image_variants":existing_skus,
        "manual_review_variants":review_skus,
        "missing_media_variants":missing_skus,
        "decision_group":decision,
        "common_candidate":common_top,
        "common_candidate_votes":common_top_n,
        "review_note":(
            "Один кандидат повторяется для всех спорных SKU — можно проверять как общее фото карточки."
            if decision=="ONE_COMMON_IMAGE" else
            "Один кандидат доминирует — проверить, можно ли использовать одно фото для нескольких фасовок."
            if decision=="MOSTLY_COMMON_IMAGE" else
            "Кандидаты различаются по SKU — требуется вариантная проверка."
            if decision=="VARIANT_SPECIFIC" else
            "Локальных кандидатов нет — нужно новое или внешнее фото."
        )
    })

    for r in rr:
        detail.append({
            "source_row":sr,
            "card_name":card.get("name",""),
            "sku":r.get("sku",""),
            "variant":r.get("variant",""),
            "state":"MANUAL_REVIEW",
            "current_image":existing.get(r.get("sku",""),""),
            "candidate_1":r.get("candidate_1",""),
            "candidate_2":r.get("candidate_2",""),
            "candidate_3":r.get("candidate_3",""),
            "confidence":r.get("confidence",""),
            "score":r.get("score",""),
            "reason":r.get("reason",""),
            "group_decision":decision,
        })
    for r in mm:
        detail.append({
            "source_row":sr,
            "card_name":card.get("name",""),
            "sku":r.get("sku",""),
            "variant":r.get("variant",""),
            "state":"MISSING_MEDIA",
            "current_image":existing.get(r.get("sku",""),""),
            "candidate_1":"",
            "candidate_2":"",
            "candidate_3":"",
            "confidence":"",
            "score":"",
            "reason":"",
            "group_decision":decision,
        })

gcounts=Counter(x["decision_group"] for x in summary)

def write_csv(path,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        if not rows: return
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader();w.writerows(rows)

out_summary=REPORTS/"stage22g_manual_media_card_groups_latest.csv"
out_detail=REPORTS/"stage22g_manual_media_sku_review_latest.csv"
out_json=REPORTS/"stage22g_manual_media_review_latest.json"
out_html=REPORTS/"stage22g_manual_media_review_latest.html"

write_csv(out_summary,summary)
write_csv(out_detail,detail)

payload={
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "master":str(master_path),
    "review_queue_rows":len(review),
    "missing_queue_rows":len(missing),
    "cards_requiring_attention":len(summary),
    "decision_groups":dict(gcounts),
    "summary":summary,
}
out_json.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

rows_html=[]
for s in summary:
    rows_html.append(f"""
    <tr>
      <td>{s['source_row']}</td>
      <td><strong>{html.escape(s['card_name'])}</strong><br><small>{html.escape(s['brand'])}</small></td>
      <td>{s['total_variants']}</td>
      <td>{s['existing_image_variants']}</td>
      <td>{s['manual_review_variants']}</td>
      <td>{s['missing_media_variants']}</td>
      <td><span class="tag">{s['decision_group']}</span></td>
      <td>{html.escape(s['common_candidate'])}</td>
      <td>{html.escape(s['review_note'])}</td>
    </tr>
    """)

html_doc=f"""<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><title>BB610 Stage 22G Media Review</title>
<style>
body{{font-family:Arial,sans-serif;background:#0b0f10;color:#e7ecef;margin:24px}}
h1{{font-size:24px}} .meta{{color:#9aa6ac;margin-bottom:18px}}
table{{width:100%;border-collapse:collapse;background:#11181b}}
th,td{{border:1px solid #283238;padding:8px;vertical-align:top;font-size:13px}}
th{{background:#182126;text-align:left;position:sticky;top:0}}
.tag{{display:inline-block;padding:3px 6px;border:1px solid #53616a;border-radius:4px;font-size:11px}}
small{{color:#91a0a8}}
</style></head><body>
<h1>BB610 Market — Stage 22G Manual Media Review</h1>
<div class="meta">
77 product cards / 195 variants. Manual review queue: {len(review)} SKU. Missing media: {len(missing)} SKU.
<br>Groups: {dict(gcounts)}
</div>
<table><thead><tr>
<th>Row</th><th>Card</th><th>Variants</th><th>Existing</th><th>Review</th><th>Missing</th><th>Group</th><th>Common candidate</th><th>Note</th>
</tr></thead><tbody>{''.join(rows_html)}</tbody></table>
</body></html>"""
out_html.write_text(html_doc,encoding="utf-8")

print("CARDS_REQUIRING_ATTENTION:",len(summary))
print("MANUAL_REVIEW_SKUS:",len(review))
print("MISSING_MEDIA_SKUS:",len(missing))
print("DECISION_GROUPS:")
for k in ("ONE_COMMON_IMAGE","MOSTLY_COMMON_IMAGE","VARIANT_SPECIFIC","MISSING_ONLY"):
    print(f"  {k}: {gcounts.get(k,0)}")
print("REPORTS:")
print(" ",out_summary)
print(" ",out_detail)
print(" ",out_json)
print(" ",out_html)
print("READ-ONLY: nothing was assigned or published.")
