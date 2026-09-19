from __future__ import annotations

"""Fill the last Plantlogic pot galleries with additional images from each model's own official page.

Safety:
- page identity must verify the expected Plantlogic Product #;
- foreign Product # image candidates are rejected;
- logos/icons/banners/culture headers are rejected;
- existing primary images are preserved;
- only media links are changed;
- no commerce, price, stock, availability or commerce_map writes.
"""

import argparse
import hashlib
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
from backend.tools_collect_plantlogic_official_media_20260918 import (
    SOURCE_OVERRIDES, fetch_html, img_candidates, load_master, product_number_verified
)
from backend.tools_apply_plantlogic_official_media_20260918 import _download_url_variants
from backend.tools_complete_pcv3_preprice_web_media import (
    RUNTIME_MEDIA, _fetch, _image_kind, _safe_slug, _sha256
)
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT=ROOT/"var"/"release-backups"
REPORT_ROOT=ROOT/"var"/"reports"
EXPECTED_PRODUCTS=34
EXPECTED_COLOR_SKUS=108
MIN_BYTES=10_000
MAX_BYTES=12_000_000
MAX_EXTRA_PER_CARD=6
GENERIC=(
    "logo","favicon","banner","header","hero","culture","blueberry-production",
    "rubus-production","strawberry-production","vegetable","hydroponic-system-cover",
    "icon","placeholder","team","contact","footer"
)
PRODUCT_NO_RE=re.compile(r"(?<!\d)(1[0-9]{5,8}|3[0-9]{7,8})(?!\d)")


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def public_file(path):
    raw=str(path or "").strip()
    if raw.startswith("/media/products/") or raw.startswith("media/products/"):
        return RUNTIME_MEDIA/Path(raw).name
    return ROOT/raw.lstrip("/")


def assigned_count(sku,valid):
    ids=[str(sku.get("primary_media_id") or "")]+[str(x) for x in (sku.get("gallery_media_ids") or [])]
    return len({x for x in ids if x and x in valid})


def manufacturer_no(sku):
    a=sku.get("attributes") if isinstance(sku.get("attributes"),dict) else {}
    return str(a.get("manufacturer_product_no") or "").strip()


def deficient(card):
    media_ids={str(x.get("media_id") or "") for x in ((card.get("sku_media") or {}).get("media") or []) if isinstance(x,dict)}
    return [
        x for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x,dict) and x.get("enabled") is not False and assigned_count(x,media_ids)<2
    ]


def download(row,referer):
    errs=[]
    for url in _download_url_variants(str(row.get("url") or "")):
        try:
            data,ctype,resolved=_fetch(
                url,referer=referer,
                accept="image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8"
            )
            if len(data)<MIN_BYTES: raise RuntimeError("too small")
            if len(data)>MAX_BYTES: raise RuntimeError("too large")
            kind=_image_kind(data,ctype,resolved)
            if not kind: raise RuntimeError("unsupported")
            return {"bytes":data,"kind":kind,"resolved":resolved,"sha256":_sha256(data)}
        except Exception as exc:
            errs.append(str(exc))
    raise RuntimeError("; ".join(errs[:2]) or "download failed")


def candidate_ok(row,expected):
    url=str(row.get("url") or "").lower()
    context=" ".join(str(x) for x in [
        row.get("url"),row.get("source")," ".join(row.get("reasons") or [])
    ]).lower()
    if any(x in url for x in GENERIC):
        return False
    found=set(PRODUCT_NO_RE.findall(context))
    exp=set(expected)
    if found and not (found & exp):
        return False
    # Accept exact/identity candidates first, plus own-page product imagery
    # that has no conflicting manufacturer number.
    score=int(row.get("score") or 0)
    if row.get("identity_match"):
        return True
    source=str(row.get("source") or "")
    if source.startswith("img:") and score>=35 and not found:
        return True
    return False


def existing_hashes(card):
    out={}
    for row in ((card.get("sku_media") or {}).get("media") or []):
        if not isinstance(row,dict): continue
        mid=str(row.get("media_id") or "")
        p=public_file(row.get("path"))
        if not mid or not p.exists(): continue
        try: out[_sha256(p.read_bytes())]=mid
        except Exception: pass
    return out


def mid_for(path):
    return "med_pl_page_gallery_"+hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]


def build_plan():
    master=load_master()
    rows=[]
    errors=[]
    total=0
    before=0

    for spec in master["products"]:
        pid=str(spec["product_id"])
        slug=str(spec["slug"])
        card=pcv3.get(pid)
        if not isinstance(card,dict):
            errors.append(f"{pid}: missing card")
            continue
        total+=len([x for x in ((card.get("sku_media") or {}).get("skus") or []) if isinstance(x,dict) and x.get("enabled") is not False])
        bad=deficient(card)
        before+=len(bad)
        if not bad:
            continue

        numbers=sorted({manufacturer_no(x) for x in bad if manufacturer_no(x)})
        page=SOURCE_OVERRIDES.get(slug,str(spec.get("source_url") or ""))
        try:
            final,html=fetch_html(page)
            all_numbers=[str(x.get("product_no") or "") for x in (spec.get("skus") or []) if x.get("product_no")]
            if not product_number_verified(html,all_numbers):
                raise RuntimeError("Product # not verified on official page")
            cands=[
                x for x in img_candidates(
                    final,html,all_numbers,
                    str(spec.get("official_name_en") or spec.get("name") or "")
                )
                if candidate_ok(x,all_numbers)
            ]
            downloads=[]
            seen=set()
            for cand in cands[:24]:
                if len(downloads)>=MAX_EXTRA_PER_CARD: break
                try: item=download(cand,final)
                except Exception: continue
                if item["sha256"] in seen: continue
                seen.add(item["sha256"])
                downloads.append({"candidate":cand,**item})
            rows.append({
                "product_id":pid,"slug":slug,"card":card,"numbers":numbers,
                "page":final,"downloads":downloads
            })
        except Exception as exc:
            errors.append(f"{slug}: {type(exc).__name__}: {exc}")

    if total!=EXPECTED_COLOR_SKUS:
        errors.append(f"color SKU count {total} != {EXPECTED_COLOR_SKUS}")
    return {"rows":rows,"errors":errors,"before":before,"total":total}


def patch(plan):
    card=deepcopy(plan["card"])
    sm=card.setdefault("sku_media",{})
    media=sm.setdefault("media",[])
    by_id={str(x.get("media_id") or ""):x for x in media if isinstance(x,dict) and x.get("media_id")}
    by_path={str(x.get("path") or ""):str(x.get("media_id") or "") for x in media if isinstance(x,dict) and x.get("path") and x.get("media_id")}
    hashes=existing_hashes(card)
    created=[]
    newids=[]
    RUNTIME_MEDIA.mkdir(parents=True,exist_ok=True)

    for item in plan["downloads"]:
        mid=hashes.get(item["sha256"])
        if not mid:
            filename=f"plantlogic-{_safe_slug(plan['slug'])}-page-{item['sha256'][:12]}.{item['kind']}"
            physical=RUNTIME_MEDIA/filename
            if not physical.exists():
                physical.write_bytes(item["bytes"]);created.append(physical)
            public=f"/media/products/{filename}"
            mid=by_path.get(public) or mid_for(public)
            if mid not in by_id:
                row={
                    "media_id":mid,"path":public,
                    "alt":str((card.get("content") or {}).get("title") or plan["slug"]),
                    "kind":"gallery","sort_order":len(media)
                }
                media.append(row);by_id[mid]=row;by_path[public]=mid
            hashes[item["sha256"]]=mid
        if mid and mid not in newids:newids.append(mid)

    valid=set(by_id)
    changed=0
    for sku in ((card.get("sku_media") or {}).get("skus") or []):
        if not isinstance(sku,dict) or sku.get("enabled") is False: continue
        if manufacturer_no(sku) not in plan["numbers"]: continue
        if assigned_count(sku,valid)>=2: continue
        primary=str(sku.get("primary_media_id") or "")
        oldg=[str(x) for x in (sku.get("gallery_media_ids") or []) if str(x)]
        ids=[]
        for mid in [primary]+oldg+newids:
            if mid and mid in valid and mid not in ids:ids.append(mid)
        if len(ids)<2: continue
        if primary not in valid: primary=ids[0]
        gallery=[x for x in ids if x!=primary]
        sku["primary_media_id"]=primary
        sku["gallery_media_ids"]=gallery
        changed+=1

    pcv3.validate(card)
    return card,created,changed


def backup():
    dest=BACKUP_ROOT/f"plantlogic-last-gallery-{stamp()}"
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(pcv3.BASE,dest/"product_cards_v3")
    return dest


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");args=ap.parse_args()
    plan=build_plan()
    print("PLANTLOGIC LAST GALLERY PASS")
    print("COLOR SKU:",plan["total"])
    print("SKU WITH <2 PHOTOS BEFORE:",plan["before"])
    print("TARGET CARDS:",len(plan["rows"]))
    print("PREFLIGHT ERRORS:",len(plan["errors"]))
    if plan["errors"]:
        for e in plan["errors"][:10]:print("ERROR:",e)
    downloaded=sum(len(x["downloads"]) for x in plan["rows"])
    print("ADDITIONAL OFFICIAL PAGE IMAGES:",downloaded)
    print("PRICE/STOCK WRITES: 0")
    if plan["errors"]:
        print("RESULT: FAIL");return 2
    if not args.apply:
        print("RESULT: PASS (DRY RUN)");return 0

    before_db=_snapshot_tables()
    before_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    b=backup();created=[];changed_cards=0;changed_skus=0
    try:
        for row in plan["rows"]:
            patched,files,count=patch(row);created+=files
            if patched!=row["card"]:
                pcv3.put(row["product_id"],patched);changed_cards+=1;changed_skus+=count
        if _snapshot_tables()!=before_db:raise RuntimeError("commerce database changed")
        after_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map!=before_map:raise RuntimeError("commerce_map changed")

        after=0
        for spec in load_master()["products"]:
            card=pcv3.get(str(spec["product_id"]))
            after+=len(deficient(card))
        REPORT_ROOT.mkdir(parents=True,exist_ok=True)
        rp=REPORT_ROOT/f"plantlogic-last-gallery-{stamp()}.json"
        rp.write_text(json.dumps({
            "before":plan["before"],"after":after,
            "changed_cards":changed_cards,"changed_skus":changed_skus,
            "downloaded":downloaded,"backup":str(b)
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("CARDS CHANGED:",changed_cards)
        print("SKU LINKS CHANGED:",changed_skus)
        print("SKU WITH <2 PHOTOS AFTER:",after)
        print("COMMERCE/PRICES UNCHANGED: PASS")
        print("BACKUP:",b)
        print("REPORT:",rp)
        print("RESULT: PASS")
        return 0
    except Exception:
        for p in created:
            try:p.unlink()
            except Exception:pass
        if pcv3.BASE.exists():shutil.rmtree(pcv3.BASE)
        shutil.copytree(b/"product_cards_v3",pcv3.BASE)
        raise

if __name__=="__main__":
    raise SystemExit(main())
