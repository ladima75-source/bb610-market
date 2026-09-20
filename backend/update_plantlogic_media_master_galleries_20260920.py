from __future__ import annotations

"""Rebuild Plantlogic pot SKU galleries from PlantLogic Media Master 2026.

Only exact Product #, PRODUCT, no-text images from the curated Drive manifest
are admitted. Technical drawings/diagrams/infographics/text-bearing images are
not gallery media. Zephyr 30L/40L use the previously approved family fallback.
Commerce, prices, stock and availability are untouched.
"""

import argparse
import hashlib
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.tools_complete_pcv3_preprice_web_media import RUNTIME_MEDIA, _fetch, _image_kind, _sha256
from backend.tools_prepare_pcv3_release import _snapshot_tables

CURATED=ROOT/"data"/"product_content"/"plantlogic_media_master_gallery_20260920.json"
BACKUP_ROOT=ROOT/"var"/"release-backups"
REPORT_ROOT=ROOT/"var"/"reports"
MIN_BYTES=8_000
MAX_BYTES=16_000_000


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def attrs(sku):
    return sku.get("attributes") if isinstance(sku.get("attributes"),dict) else {}


def product_no(sku):
    return str(attrs(sku).get("manufacturer_product_no") or "").strip()


def color_code(sku):
    return str(attrs(sku).get("color_code") or "").strip()


def download_one(no,item,referer):
    errors=[]
    for url in item.get("direct_urls") or []:
        try:
            data,ctype,resolved=_fetch(
                url,
                referer=referer,
                accept="image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
            )
            if len(data)<MIN_BYTES:
                raise RuntimeError("image too small")
            if len(data)>MAX_BYTES:
                raise RuntimeError("image too large")
            kind=_image_kind(data,ctype,resolved)
            if not kind:
                raise RuntimeError("unsupported image")
            return {
                "ok":True,
                "product_no":no,
                "manifest_media_id":str(item["media_id"]),
                "filename":str(item["filename"]),
                "data":data,
                "kind":kind,
                "resolved_url":resolved,
                "download_sha256":_sha256(data),
                "manifest_sha256":str(item.get("sha256") or ""),
            }
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    return {
        "ok":False,
        "product_no":no,
        "manifest_media_id":str(item.get("media_id") or ""),
        "filename":str(item.get("filename") or ""),
        "error":"; ".join(errors[:4]) or "download failed",
    }


def media_id(no,manifest_id):
    clean="".join(ch.lower() for ch in str(manifest_id) if ch.isalnum())
    return f"plmm_{no}_{clean}"


def public_path(no,manifest_id,kind):
    clean="".join(ch.lower() for ch in str(manifest_id) if ch.isalnum())
    return f"/media/products/plantlogic-{no}-{clean}.{kind}"


def enabled_plantlogic_cards():
    out=[]
    for row in pcv3.list_cards():
        card=pcv3.get(str(row.get("product_id") or ""))
        if not isinstance(card,dict) or not card.get("enabled"):
            continue
        content=card.get("content") if isinstance(card.get("content"),dict) else {}
        if str(content.get("brand") or "").strip().lower()!="plantlogic":
            continue
        out.append(card)
    return out


def build_downloads(doc,cards):
    active=set()
    for card in cards:
        for sku in ((card.get("sku_media") or {}).get("skus") or []):
            if isinstance(sku,dict) and sku.get("enabled") is not False:
                no=product_no(sku)
                if no:
                    active.add(no)

    jobs=[]
    for no,model in (doc.get("models") or {}).items():
        if no not in active:
            continue
        for item in model.get("items") or []:
            jobs.append((no,item,str(model.get("source_page_url") or "")))
    return jobs


def store_downloads(results):
    RUNTIME_MEDIA.mkdir(parents=True,exist_ok=True)
    stored={}
    for r in results:
        if not r.get("ok"):
            continue
        no=r["product_no"]
        mid=r["manifest_media_id"]
        path=public_path(no,mid,r["kind"])
        physical=RUNTIME_MEDIA/Path(path).name
        if not physical.exists() or _sha256(physical.read_bytes())!=r["download_sha256"]:
            physical.write_bytes(r["data"])
        stored[(no,mid)]={
            "media_id":media_id(no,mid),
            "path":path,
            "alt":f"Plantlogic {no} — {r['filename']}",
            "kind":"photo",
            "sort_order":0,
            "filename":r["filename"],
        }
    return stored


def ensure_media_row(media,row):
    mid=row["media_id"]
    for existing in media:
        if isinstance(existing,dict) and str(existing.get("media_id") or "")==mid:
            existing.update({k:v for k,v in row.items() if k!="filename"})
            return
    media.append({k:v for k,v in row.items() if k!="filename"})


def fallback_rows(doc,no):
    return [
        {
            "media_id":str(x["media_id"]),
            "path":str(x["path"]),
            "alt":str(x.get("alt") or f"Plantlogic Zephyr V2 {no}"),
            "kind":"photo",
            "sort_order":i,
            "filename":Path(str(x["path"])).name,
        }
        for i,x in enumerate((doc.get("zephyr_fallbacks") or {}).get(no) or [])
    ]


def selected_rows_for_sku(doc,stored,sku):
    no=product_no(sku)
    if no in {"1301153","1301143"}:
        return fallback_rows(doc,no)

    model=(doc.get("models") or {}).get(no) or {}
    rows=[]
    by_filename={}
    for item in model.get("items") or []:
        row=stored.get((no,str(item.get("media_id") or "")))
        if not row:
            continue
        rows.append(row)
        by_filename[str(item.get("filename") or "")]=row

    if no=="1301144":
        wanted=((doc.get("zephyr_25_color_files") or {}).get(color_code(sku)) or [])
        exact=[by_filename[x] for x in wanted if x in by_filename]
        if exact:
            return exact
    return rows


def patch_card(doc,stored,card):
    work=deepcopy(card)
    sm=work.setdefault("sku_media",{})
    media=sm.setdefault("media",[])
    changed_skus=0
    photo_counts={}

    for sku in sm.get("skus") or []:
        if not isinstance(sku,dict) or sku.get("enabled") is False:
            continue
        no=product_no(sku)
        if not no:
            continue
        rows=selected_rows_for_sku(doc,stored,sku)
        if not rows:
            continue

        for i,row in enumerate(rows):
            row=deepcopy(row)
            row["sort_order"]=i
            ensure_media_row(media,row)

        ids=[str(x["media_id"]) for x in rows]
        before=(sku.get("primary_media_id"),list(sku.get("gallery_media_ids") or []))
        sku["primary_media_id"]=ids[0]
        sku["gallery_media_ids"]=ids[1:]
        after=(sku.get("primary_media_id"),list(sku.get("gallery_media_ids") or []))
        if after!=before:
            changed_skus+=1
        photo_counts[no]=max(photo_counts.get(no,0),len(ids))

    referenced=set()
    for sku in sm.get("skus") or []:
        if not isinstance(sku,dict):
            continue
        p=str(sku.get("primary_media_id") or "")
        if p:
            referenced.add(p)
        referenced.update(str(x) for x in (sku.get("gallery_media_ids") or []) if str(x))
    sm["media"]=[
        x for x in media
        if isinstance(x,dict) and str(x.get("media_id") or "") in referenced
    ]
    work["sku_media"]=sm
    pcv3.validate(work)
    return work,changed_skus,photo_counts


def backup():
    dest=BACKUP_ROOT/f"plantlogic-media-master-gallery-{stamp()}"
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

    doc=json.loads(CURATED.read_text(encoding="utf-8"))
    cards=enabled_plantlogic_cards()
    jobs=build_downloads(doc,cards)

    print("PLANTLOGIC MEDIA MASTER GALLERY")
    print("MEDIA MASTER CURATED IMAGES:",doc["statistics"]["curated_product_images"])
    print("ACTIVE DOWNLOAD JOBS:",len(jobs))
    print("ZEPHYR 30L/40L FALLBACK: capacities + greenhouse")
    print("TECHNICAL/TEXT MEDIA IN SKU GALLERIES: FORBIDDEN")
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    results=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(download_one,no,item,referer) for no,item,referer in jobs]
        for future in as_completed(futures):
            results.append(future.result())

    failures=[x for x in results if not x.get("ok")]
    stored=store_downloads(results)

    before_db=_snapshot_tables()
    before_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    b=backup()
    changed_cards=0
    changed_skus=0
    counts={}
    try:
        for card in cards:
            patched,c,pc=patch_card(doc,stored,card)
            if patched!=card:
                pcv3.put(card["product_id"],patched)
                changed_cards+=1
            changed_skus+=c
            for no,n in pc.items():
                counts[no]=max(counts.get(no,0),n)

        if _snapshot_tables()!=before_db:
            raise RuntimeError("commerce database changed")
        after_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map!=before_map:
            raise RuntimeError("commerce_map changed")

        REPORT_ROOT.mkdir(parents=True,exist_ok=True)
        rp=REPORT_ROOT/f"plantlogic-media-master-gallery-{stamp()}.json"
        report={
            "curated_images":doc["statistics"]["curated_product_images"],
            "download_jobs":len(jobs),
            "download_ok":sum(1 for x in results if x.get("ok")),
            "download_failures":[
                {k:v for k,v in x.items() if k in {"product_no","manifest_media_id","filename","error"}}
                for x in failures
            ],
            "cards_changed":changed_cards,
            "sku_links_changed":changed_skus,
            "photos_per_model":dict(sorted(counts.items())),
            "commerce_unchanged":True,
            "backup":str(b),
        }
        rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

        print("DOWNLOAD OK:",report["download_ok"])
        print("DOWNLOAD FAILURES:",len(failures))
        print("CARDS CHANGED:",changed_cards)
        print("SKU LINKS CHANGED:",changed_skus)
        print("MODELS WITH CURATED/FALLBACK GALLERY:",len(counts))
        print("PHOTO COUNTS:",json.dumps(dict(sorted(counts.items())),ensure_ascii=False))
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
