from __future__ import annotations

"""Build a proper Rivus SKU gallery from official Plantlogic media.

Official page family Product #1302050 maps to commercial variants:
- 13020500 Rivus slab base, black
- 13020502 Rivus slab base, black/white
- 13020510 Rivus end cap, black
- 13020512 Rivus end cap, black/white

Storefront rule:
- slab-base SKUs get slab/base product photos only;
- end-cap SKUs get end-cap product photos only;
- Rivus_Graphic, tech sheets, drawings and other technical media never enter
  the storefront SKU gallery;
- commerce/prices/stock remain untouched.
"""

import argparse
import hashlib
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.tools_complete_pcv3_preprice_web_media import RUNTIME_MEDIA, _fetch, _image_kind, _sha256
from backend.tools_prepare_pcv3_release import _snapshot_tables

PRODUCT_ID="prd_pl_rivus"
SOURCE_PAGE="https://getplantlogic.com/portfolio-items/rivus-slab-base/"
BACKUP_ROOT=ROOT/"var"/"release-backups"
REPORT_ROOT=ROOT/"var"/"reports"
MIN_BYTES=8_000
MAX_BYTES=16_000_000

BASE_MEDIA=[
    ("PL9C36A0F7","RIVUS-130205000-ISOMETRICO.jpg","https://getplantlogic.com/wp-content/uploads/2024/04/RIVUS-130205000-ISOMETRICO.jpg"),
    ("PL08785CE4","RIVUS-130205000-ISOMETRICO-1.jpg","https://getplantlogic.com/wp-content/uploads/2024/04/RIVUS-130205000-ISOMETRICO-1.jpg"),
    ("PL907D14D6","RIVUS-130205000-FRONTAL.jpg","https://getplantlogic.com/wp-content/uploads/2024/04/RIVUS-130205000-FRONTAL.jpg"),
    ("PL62AF4A9B","product_Rivus_A-1.jpg","https://getplantlogic.com/wp-content/uploads/2021/11/product_Rivus_A-1.jpg"),
    ("PLB2A564D1","ftr_Rivus_A.jpg","https://getplantlogic.com/wp-content/uploads/2021/11/ftr_Rivus_A.jpg"),
    ("PL6DAC3B12","ftr_Rivus_B.jpg","https://getplantlogic.com/wp-content/uploads/2021/11/ftr_Rivus_B.jpg"),
    ("PL6E7573D2","ftr_Rivus_C.jpg","https://getplantlogic.com/wp-content/uploads/2021/11/ftr_Rivus_C.jpg"),
]

ENDCAP_MEDIA=[
    ("PL87973314","RIVUS-130205000-ENDCAP-1.jpg","https://getplantlogic.com/wp-content/uploads/2024/04/RIVUS-130205000-ENDCAP-1.jpg"),
    ("PL0C624F87","RIVUS-130205000-ENDCAP-2.jpg","https://getplantlogic.com/wp-content/uploads/2024/04/RIVUS-130205000-ENDCAP-2.jpg"),
]

BASE_SKUS={"13020500","13020502"}
ENDCAP_SKUS={"13020510","13020512"}


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def attrs(sku):
    return sku.get("attributes") if isinstance(sku.get("attributes"),dict) else {}


def product_no(sku):
    return str(attrs(sku).get("manufacturer_product_no") or "").strip()


def download(media_id,filename,url):
    data,ctype,resolved=_fetch(
        url,
        referer=SOURCE_PAGE,
        accept="image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
    )
    if len(data)<MIN_BYTES:
        raise RuntimeError(f"{filename}: image too small")
    if len(data)>MAX_BYTES:
        raise RuntimeError(f"{filename}: image too large")
    kind=_image_kind(data,ctype,resolved)
    if not kind:
        raise RuntimeError(f"{filename}: unsupported image")
    return {
        "source_media_id":media_id,
        "filename":filename,
        "source_url":resolved,
        "data":data,
        "kind":kind,
        "sha256":_sha256(data),
    }


def local_media_id(source_media_id):
    return "plmm_rivus_"+str(source_media_id).lower()


def store(row):
    RUNTIME_MEDIA.mkdir(parents=True,exist_ok=True)
    filename=f"plantlogic-rivus-{row['source_media_id'].lower()}.{row['kind']}"
    physical=RUNTIME_MEDIA/filename
    if not physical.exists() or _sha256(physical.read_bytes())!=row["sha256"]:
        physical.write_bytes(row["data"])
    return {
        "media_id":local_media_id(row["source_media_id"]),
        "path":f"/media/products/{filename}",
        "alt":f"Plantlogic Rivus — {row['filename']}",
        "kind":"photo",
        "sort_order":0,
    }


def backup():
    dest=BACKUP_ROOT/f"plantlogic-rivus-gallery-{stamp()}"
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(pcv3.BASE,dest/"product_cards_v3")
    return dest


def restore(dest):
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(dest/"product_cards_v3",pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True,exist_ok=True)


def apply_rows(card,base_rows,endcap_rows):
    work=deepcopy(card)
    sm=work.setdefault("sku_media",{})
    media=sm.setdefault("media",[])
    by_id={str(x.get("media_id") or ""):x for x in media if isinstance(x,dict) and x.get("media_id")}

    for i,row in enumerate(base_rows+endcap_rows):
        x=deepcopy(row)
        x["sort_order"]=i
        if x["media_id"] in by_id:
            by_id[x["media_id"]].update(x)
        else:
            media.append(x)
            by_id[x["media_id"]]=x

    changed=0
    counts={}
    for sku in sm.get("skus") or []:
        if not isinstance(sku,dict) or sku.get("enabled") is False:
            continue
        no=product_no(sku)
        if no in BASE_SKUS:
            selected=base_rows
        elif no in ENDCAP_SKUS:
            selected=endcap_rows
        else:
            continue
        ids=[x["media_id"] for x in selected]
        before=(sku.get("primary_media_id"),list(sku.get("gallery_media_ids") or []))
        sku["primary_media_id"]=ids[0] if ids else None
        sku["gallery_media_ids"]=ids[1:]
        after=(sku.get("primary_media_id"),list(sku.get("gallery_media_ids") or []))
        if after!=before:
            changed+=1
        counts[no]=len(ids)

    referenced=set()
    for sku in sm.get("skus") or []:
        if not isinstance(sku,dict):
            continue
        p=str(sku.get("primary_media_id") or "")
        if p:
            referenced.add(p)
        referenced.update(str(x) for x in (sku.get("gallery_media_ids") or []) if str(x))
    sm["media"]=[x for x in media if isinstance(x,dict) and str(x.get("media_id") or "") in referenced]
    work["sku_media"]=sm
    pcv3.validate(work)
    return work,changed,counts


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()

    card=pcv3.get(PRODUCT_ID)
    if not isinstance(card,dict):
        raise RuntimeError("Rivus Product Card v3 not found")

    skus=(card.get("sku_media") or {}).get("skus") or []
    live_numbers={product_no(x) for x in skus if isinstance(x,dict) and product_no(x)}
    expected=BASE_SKUS|ENDCAP_SKUS
    if not expected.issubset(live_numbers):
        raise RuntimeError(f"Rivus SKU set incomplete: {sorted(live_numbers)}")

    print("PLANTLOGIC RIVUS SKU GALLERY")
    print("FAMILY PRODUCT #: 1302050")
    print("BASE SKU:",", ".join(sorted(BASE_SKUS)))
    print("END CAP SKU:",", ".join(sorted(ENDCAP_SKUS)))
    print("BASE PHOTOS:",len(BASE_MEDIA))
    print("END CAP PHOTOS:",len(ENDCAP_MEDIA))
    print("TECHNICAL/DRAWING MEDIA IN GALLERY: 0")
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    downloaded_base=[download(*x) for x in BASE_MEDIA]
    downloaded_end=[download(*x) for x in ENDCAP_MEDIA]
    base_rows=[store(x) for x in downloaded_base]
    endcap_rows=[store(x) for x in downloaded_end]

    before_db=_snapshot_tables()
    before_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    b=backup()
    try:
        patched,changed,counts=apply_rows(card,base_rows,endcap_rows)
        pcv3.put(PRODUCT_ID,patched)

        if _snapshot_tables()!=before_db:
            raise RuntimeError("commerce database changed")
        after_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map!=before_map:
            raise RuntimeError("commerce_map changed")

        REPORT_ROOT.mkdir(parents=True,exist_ok=True)
        rp=REPORT_ROOT/f"plantlogic-rivus-gallery-{stamp()}.json"
        rp.write_text(json.dumps({
            "product_id":PRODUCT_ID,
            "family_product_no":"1302050",
            "sku_photo_counts":counts,
            "sku_links_changed":changed,
            "technical_gallery_media":0,
            "commerce_unchanged":True,
            "backup":str(b),
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

        print("SKU LINKS CHANGED:",changed)
        print("PHOTO COUNTS:",json.dumps(counts,ensure_ascii=False,sort_keys=True))
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
