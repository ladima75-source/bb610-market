from __future__ import annotations

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

OLD_ID="prd_pl_zephyr_v2"
MODELS=[
    {"product_id":"prd_pl_1301144","slug":"plantlogic-zephyr-v2-25l","product_no":"1301144","volume":"25 л"},
    {"product_id":"prd_pl_1301153","slug":"plantlogic-zephyr-v2-30l","product_no":"1301153","volume":"30 л"},
    {"product_id":"prd_pl_1301143","slug":"plantlogic-zephyr-v2-40l","product_no":"1301143","volume":"40 л"},
]
BACKUP_ROOT=ROOT/"var"/"release-backups"
REPORT_ROOT=ROOT/"var"/"reports"

def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def attrs(sku):
    return sku.get("attributes") if isinstance(sku.get("attributes"),dict) else {}

def number(sku):
    return str(attrs(sku).get("manufacturer_product_no") or "").strip()

def clean_characteristics(rows,volume,product_no):
    out=[]
    volume_done=False
    product_done=False
    for row in rows or []:
        if not isinstance(row,dict):
            continue
        label=str(row.get("label") or "")
        value=str(row.get("value") or "")
        low=label.lower().replace("’","'")
        if "об'єм" in low or "літраж" in low or "volume" in low:
            value=volume
            volume_done=True
        if "product #" in low or "артикул" in low:
            value=product_no
            product_done=True
        out.append({"label":label,"value":value})
    if not volume_done:
        out.append({"label":"Об'єм","value":volume})
    if not product_done:
        out.append({"label":"Product # Plantlogic","value":product_no})
    return out

def card_for(source,spec):
    work=deepcopy(source)
    work["product_id"]=spec["product_id"]
    work["slug"]=spec["slug"]
    work["enabled"]=True
    content=work["content"]
    title=f"Горщик Zephyr V2 {spec['volume']}"
    content["title"]=title
    content["short_description"]=re.sub(
        r"25\s*[,/]\s*30\s*(?:та|і|/)\s*40\s*л",
        spec["volume"],
        str(content.get("short_description") or ""),
        flags=re.I,
    )
    content["characteristics"]=clean_characteristics(
        content.get("characteristics") or [],spec["volume"],spec["product_no"]
    )
    seo=content.get("seo") if isinstance(content.get("seo"),dict) else {"title":"","description":""}
    seo["title"]=title+" · Plantlogic · BB610 Market"
    seo["description"]=f"Zephyr V2 {spec['volume']}, Product #{spec['product_no']}. Професійний горщик Plantlogic для субстратного вирощування."
    content["seo"]=seo

    showcase=content.get("model_showcase")
    if isinstance(showcase,dict) and isinstance(showcase.get("items"),list):
        items=[x for x in showcase["items"] if isinstance(x,dict) and str(x.get("product_no") or "")==spec["product_no"]]
        if items:
            showcase["items"]=items
            showcase["title"]=title
            content["model_showcase"]=showcase

    all_skus=[
        deepcopy(x) for x in ((source.get("sku_media") or {}).get("skus") or [])
        if isinstance(x,dict) and number(x)==spec["product_no"]
    ]
    if len(all_skus)!=2:
        raise RuntimeError(f"{spec['product_no']}: expected 2 color SKU, got {len(all_skus)}")

    used=set()
    for sku in all_skus:
        primary=str(sku.get("primary_media_id") or "")
        if primary:
            used.add(primary)
        used.update(str(x) for x in (sku.get("gallery_media_ids") or []) if str(x))

    media=[
        deepcopy(x) for x in ((source.get("sku_media") or {}).get("media") or [])
        if isinstance(x,dict) and str(x.get("media_id") or "") in used
    ]
    available={str(x.get("media_id") or "") for x in media}
    for sku in all_skus:
        primary=str(sku.get("primary_media_id") or "")
        gallery=[str(x) for x in (sku.get("gallery_media_ids") or [])]
        if primary and primary not in available:
            raise RuntimeError(f"{spec['product_no']}: missing primary media {primary}")
        if any(x not in available for x in gallery):
            raise RuntimeError(f"{spec['product_no']}: missing gallery media")
        if (1 if primary else 0)+len(gallery)<2:
            raise RuntimeError(f"{spec['product_no']}: SKU {sku.get('sku_code')} has <2 photos")

    work["sku_media"]={"skus":all_skus,"media":media}
    pcv3.validate(work)
    return work

def backup():
    dest=BACKUP_ROOT/f"plantlogic-zephyr-split-{stamp()}"
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(pcv3.BASE,dest/"product_cards_v3")
    return dest

def restore(dest):
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(dest/"product_cards_v3",pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True,exist_ok=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()

    source=pcv3.get(OLD_ID)
    if not isinstance(source,dict):
        raise RuntimeError("grouped Zephyr source card not found")

    desired=[card_for(source,s) for s in MODELS]
    total_skus=sum(len(x["sku_media"]["skus"]) for x in desired)
    if total_skus!=6:
        raise RuntimeError(f"expected 6 Zephyr color SKU, got {total_skus}")

    print("PLANTLOGIC ZEPHYR V2 SPLIT")
    print("OLD GROUPED CARD:",OLD_ID)
    print("NEW CARDS:",len(desired))
    print("COLOR SKU:",total_skus)
    for card in desired:
        print(card["slug"],"|",card["content"]["title"],"| SKU",len(card["sku_media"]["skus"]))
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    before_db=_snapshot_tables()
    before_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    b=backup()
    try:
        for card in desired:
            existing=pcv3.get(card["product_id"])
            if existing is None:
                pcv3.create(card)
            else:
                pcv3.put(card["product_id"],card)

        old=deepcopy(source)
        old["enabled"]=False
        pcv3.put(OLD_ID,old)

        if _snapshot_tables()!=before_db:
            raise RuntimeError("commerce database changed")
        after_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map!=before_map:
            raise RuntimeError("commerce_map changed")

        for spec in MODELS:
            live=pcv3.get(spec["product_id"])
            if not isinstance(live,dict) or not live.get("enabled"):
                raise RuntimeError(f"{spec['product_id']}: new card not enabled")
            if len((live.get("sku_media") or {}).get("skus") or [])!=2:
                raise RuntimeError(f"{spec['product_id']}: SKU count mismatch")
        if pcv3.get(OLD_ID).get("enabled"):
            raise RuntimeError("old grouped card still enabled")

        REPORT_ROOT.mkdir(parents=True,exist_ok=True)
        rp=REPORT_ROOT/f"plantlogic-zephyr-split-{stamp()}.json"
        rp.write_text(json.dumps({
            "old_card":OLD_ID,
            "new_cards":[{"product_id":x["product_id"],"slug":x["slug"],"title":x["content"]["title"],"sku":len(x["sku_media"]["skus"])} for x in desired],
            "commerce_unchanged":True,
            "backup":str(b)
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("OLD GROUPED CARD DISABLED: PASS")
        print("NEW CARDS ENABLED: 3")
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
