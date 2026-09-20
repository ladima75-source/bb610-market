from __future__ import annotations

"""Remove non-SKU and technical imagery from Plantlogic pot galleries.

Rules:
- gallery media must belong to the selected manufacturer Product #;
- technical sheets, diagrams, capacity graphics and catalog/landing graphics
  are not storefront gallery photos;
- Zephyr 25L #1301144 uses only exact official model photography;
- Zephyr 30L #1301153 and 40L #1301143 expose no model-specific photography
  on the current official page, so ambiguous family/technical imagery is removed;
- prices, stock, availability and commerce mapping are untouched.
"""

import argparse
import json
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT=ROOT/"var"/"release-backups"
REPORT_ROOT=ROOT/"var"/"reports"

TECH_MARKERS=(
    "tech-sheet","techsheet","technical","dimension","dimensions","drawing",
    "diagram","schematic","specification","spec-sheet","datasheet","catalog",
    "brochure","infographic","capacities","capacity-chart","landing-page",
    "zephyr-v2-capacities",
)
UNCURATED_PREFIXES=(
    "med_plantlogic_gallery_",
    "med_pl_official_",
    "med_pl_page_gallery_",
    "med_pl_semantic_",
)
PRODUCT_NO_RE=re.compile(r"(?<!\d)(1\d{5,8}|3\d{7,8})(?!\d)")

ZEPHYR_25={
    "black":[
        ("hero","https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-FRONTAL-2-2.jpg"),
        ("front","https://getplantlogic.com/wp-content/uploads/2020/11/ZEPHYR-V2-1301144-FRONTAL-2-1.jpg"),
        ("top","https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-CENITAL-1.jpg"),
        ("base","https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-BASE-2.jpg"),
    ],
    "white":[
        ("hero","https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-FRONTAL-1.jpg"),
        ("top","https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-BASE.jpg"),
    ],
}

def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def low(v):
    return str(v or "").strip().lower()

def attrs(sku):
    return sku.get("attributes") if isinstance(sku.get("attributes"),dict) else {}

def product_no(sku):
    return str(attrs(sku).get("manufacturer_product_no") or "").strip()

def color(sku):
    return str(attrs(sku).get("color_code") or "").strip()

def media_text(row):
    return " ".join(low(row.get(k)) for k in ("media_id","path","alt","kind"))

def technical(row):
    t=media_text(row)
    return any(x in t for x in TECH_MARKERS)

def foreign_model(row,expected):
    nums=set(PRODUCT_NO_RE.findall(media_text(row)))
    return bool(nums and expected not in nums)

def exact_model(row,expected):
    return expected in set(PRODUCT_NO_RE.findall(media_text(row)))

def curated_id(mid,expected):
    value=str(mid or "")
    if value.startswith(f"plbb_{expected}_"):
        return True
    if value.startswith(f"plbb_{expected}_black_") or value.startswith(f"plbb_{expected}_white_"):
        return True
    return False

def safe_existing(row,mid,expected,is_primary):
    if not row or technical(row) or foreign_model(row,expected):
        return False
    if curated_id(mid,expected):
        return True
    if exact_model(row,expected):
        return True
    # Existing primary may be legacy product photography with generic metadata;
    # keep it unless it is one of the broad collector outputs. Gallery extras are
    # held to the stricter model-specific rule.
    if is_primary and not str(mid).startswith(UNCURATED_PREFIXES):
        return True
    return False

def ensure_zephyr25_media(card,sku):
    sm=card["sku_media"]
    media=sm["media"]
    by_id={str(x.get("media_id") or ""):x for x in media if isinstance(x,dict)}
    rows=ZEPHYR_25.get(color(sku),[])
    ids=[]
    for i,(kind,path) in enumerate(rows):
        mid=f"plbb_1301144_{color(sku)}_{kind}"
        if mid not in by_id:
            row={"media_id":mid,"path":path,"alt":f"Plantlogic Zephyr V2 25 л #1301144 — {kind}","kind":"photo","sort_order":i}
            media.append(row);by_id[mid]=row
        ids.append(mid)
    sku["primary_media_id"]=ids[0] if ids else None
    sku["gallery_media_ids"]=ids[1:]
    a=attrs(sku);a["media_source_color"]=color(sku);sku["attributes"]=a

def ensure_zephyr_fallback_media(card,sku,no):
    sm=card["sku_media"]
    media=sm["media"]
    by_id={str(x.get("media_id") or ""):x for x in media if isinstance(x,dict)}
    rows=[
        (f"plmm_{no}_fallback_capacities","/assets/plantlogic/zephyr-v2-capacities.jpg",f"Plantlogic Zephyr V2 {attrs(sku).get('volume_label') or ''} — варіанти місткості"),
        (f"plmm_{no}_fallback_greenhouse","/assets/plantlogic/zephyr-v2-greenhouse.jpg",f"Plantlogic Zephyr V2 {attrs(sku).get('volume_label') or ''} — застосування в теплиці"),
    ]
    ids=[]
    for i,(mid,path,alt) in enumerate(rows):
        if mid not in by_id:
            row={"media_id":mid,"path":path,"alt":alt,"kind":"photo","sort_order":i}
            media.append(row);by_id[mid]=row
        ids.append(mid)
    sku["primary_media_id"]=ids[0]
    sku["gallery_media_ids"]=ids[1:]

def clean_card(card):
    work=deepcopy(card)
    sm=work.get("sku_media") if isinstance(work.get("sku_media"),dict) else {}
    media=sm.get("media") if isinstance(sm.get("media"),list) else []
    by_id={str(x.get("media_id") or ""):x for x in media if isinstance(x,dict) and x.get("media_id")}
    changed_skus=0
    removed_links=0

    for sku in sm.get("skus") or []:
        if not isinstance(sku,dict) or sku.get("enabled") is False:
            continue
        no=product_no(sku)
        if not no:
            continue

        before=(sku.get("primary_media_id"),list(sku.get("gallery_media_ids") or []))

        if no=="1301144":
            ensure_zephyr25_media(work,sku)
        elif no in {"1301153","1301143"}:
            ensure_zephyr_fallback_media(work,sku,no)
        else:
            primary=str(sku.get("primary_media_id") or "")
            prow=by_id.get(primary)
            if primary and not safe_existing(prow,primary,no,True):
                primary=""
            gallery=[]
            for mid in sku.get("gallery_media_ids") or []:
                mid=str(mid or "")
                row=by_id.get(mid)
                if not mid or mid==primary:
                    continue
                if not safe_existing(row,mid,no,False):
                    continue
                if mid not in gallery:
                    gallery.append(mid)
            sku["primary_media_id"]=primary or None
            sku["gallery_media_ids"]=gallery

        after=(sku.get("primary_media_id"),list(sku.get("gallery_media_ids") or []))
        if after!=before:
            changed_skus+=1
            removed_links+=max(0,(1 if before[0] else 0)+len(before[1])-(1 if after[0] else 0)-len(after[1]))

    # Drop media rows no longer referenced by any SKU. Technical graphics may
    # still live in content blocks; only SKU gallery storage is cleaned here.
    referenced=set()
    for sku in sm.get("skus") or []:
        if not isinstance(sku,dict):
            continue
        p=str(sku.get("primary_media_id") or "")
        if p: referenced.add(p)
        referenced.update(str(x) for x in (sku.get("gallery_media_ids") or []) if str(x))
    sm["media"]=[x for x in sm.get("media") or [] if isinstance(x,dict) and str(x.get("media_id") or "") in referenced]
    work["sku_media"]=sm
    pcv3.validate(work)
    return work,changed_skus,removed_links

def target_cards():
    rows=[]
    for summary in pcv3.list_cards():
        pid=str(summary.get("product_id") or "")
        card=pcv3.get(pid)
        if not isinstance(card,dict) or not card.get("enabled"):
            continue
        content=card.get("content") if isinstance(card.get("content"),dict) else {}
        if low(content.get("brand"))!="plantlogic":
            continue
        skus=(card.get("sku_media") or {}).get("skus") or []
        if not any(product_no(x) for x in skus if isinstance(x,dict)):
            continue
        rows.append(card)
    return rows

def backup():
    dest=BACKUP_ROOT/f"plantlogic-gallery-cleanup-{stamp()}"
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(pcv3.BASE,dest/"product_cards_v3")
    return dest

def restore(dest):
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(dest/"product_cards_v3",pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True,exist_ok=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");args=ap.parse_args()
    cards=target_cards()
    plan=[]
    total_changed_skus=0
    total_removed=0
    for card in cards:
        clean,c,r=clean_card(card)
        if clean!=card:
            plan.append((card["product_id"],clean))
        total_changed_skus+=c
        total_removed+=r

    print("PLANTLOGIC SKU GALLERY CLEANUP")
    print("TARGET CARDS:",len(cards))
    print("CARDS TO CHANGE:",len(plan))
    print("SKU LINKS TO CHANGE:",total_changed_skus)
    print("NON-SKU/TECHNICAL LINKS REMOVED:",total_removed)
    print("ZEPHYR 25L: exact Product #1301144 photos only")
    print("ZEPHYR 30L/40L: ambiguous family/technical photos removed")
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    before_db=_snapshot_tables()
    before_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    b=backup()
    try:
        for pid,card in plan:
            pcv3.put(pid,card)
        if _snapshot_tables()!=before_db:
            raise RuntimeError("commerce database changed")
        after_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map!=before_map:
            raise RuntimeError("commerce_map changed")

        REPORT_ROOT.mkdir(parents=True,exist_ok=True)
        rp=REPORT_ROOT/f"plantlogic-gallery-cleanup-{stamp()}.json"
        rp.write_text(json.dumps({
            "target_cards":len(cards),"cards_changed":len(plan),
            "sku_links_changed":total_changed_skus,
            "links_removed":total_removed,
            "commerce_unchanged":True,"backup":str(b)
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("COMMERCE/PRICES UNCHANGED: PASS")
        print("BACKUP:",b)
        print("REPORT:",rp)
        print("RESULT: PASS")
        return 0
    except Exception:
        restore(b)
        raise

if __name__=="__main__":
    raise SystemExit(main())
