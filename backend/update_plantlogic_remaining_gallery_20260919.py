from __future__ import annotations

"""Fill remaining Plantlogic pot galleries from BB610 media library by model identity.

This runs after the official-gallery pass. It only touches Plantlogic pot media links.
No price, stock, commerce, availability or commerce_map writes.
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
from backend.services import product_cards_v3_media as repo_media
try:
    from backend.services import media_library as runtime_media
except Exception:
    runtime_media=None
from backend.tools_prepare_pcv3_release import _snapshot_tables

MASTER=ROOT/"data"/"product_content"/"plantlogic_pots_v1_20260918.json"
BACKUP_ROOT=ROOT/"var"/"release-backups"
REPORT_ROOT=ROOT/"var"/"reports"
EXPECTED_PRODUCTS=34
EXPECTED_COLOR_SKUS=108

STOP={
 "plantlogic","liter","litre","pot","container","professional","hydroponic",
 "горщик","контейнер","для","with","new","the","and","арт"
}
ALIASES={
 "round":{"round","круглий","круглый"},
 "square":{"square","квадратний","квадратный"},
 "groove":{"groove","grooves","u","паз","пази","пазами"},
 "drainage":{"drainage","дренаж","collection"},
 "short":{"short","коротких","короткі"},
 "wide":{"wide","широких","широкі"},
 "parallel":{"parallel","паралельні","параллельные"},
 "zephyr":{"zephyr","v2"},
}


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def norm(v):
    return re.sub(r"\s+"," ",str(v or "").strip().lower())


def media_text(row):
    return norm(" ".join(str(row.get(k) or "") for k in (
        "path","url","name","title","description","filename","stored_name",
        "alt_text","tags","category","kind"
    )))


def media_path(row):
    return str(row.get("path") or row.get("url") or "").strip()


def stable_mid(path):
    return "med_pl_semantic_"+hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]


def master():
    doc=json.loads(MASTER.read_text(encoding="utf-8"))
    products=doc.get("products") or []
    if len(products)!=EXPECTED_PRODUCTS:
        raise RuntimeError("Plantlogic master count changed")
    return doc


def library():
    out=[];seen=set()
    def add(row,source):
        if not isinstance(row,dict):return
        path=media_path(row)
        if not path or path in seen:return
        seen.add(path);x=deepcopy(row);x["_source"]=source;out.append(x)
    try:
        for x in (repo_media.list_existing_media().get("items") or []):
            add(x,"repo")
    except Exception:
        pass
    if runtime_media is not None:
        try:
            for x in (runtime_media.list_media() or []):
                add(x,"runtime")
        except Exception:
            pass
    return out


def tokens(v):
    return {x for x in re.findall(r"[a-zа-яіїє0-9.]+",norm(v)) if len(x)>=2 and x not in STOP}


def volume_tokens(spec):
    vals=set()
    for sku in spec.get("skus") or []:
        p=norm(sku.get("package"))
        m=re.search(r"(\d+(?:[.,]\d+)?)\s*[лl]\b",p)
        if m:
            v=m.group(1).replace(",",".")
            vals|={v+"l",v+" л",v+" liter",v+" litre"}
    return vals


def identity_tokens(spec):
    raw=" ".join([
        str(spec.get("official_name_en") or ""),
        str(spec.get("name") or ""),
        str(spec.get("family") or ""),
        str(spec.get("slug") or ""),
    ])
    t=tokens(raw)
    out=set(t)
    for canonical,words in ALIASES.items():
        if any(w in t for w in words):
            out.add(canonical)
    return out


def score(item,spec):
    text=media_text(item)
    if not text:return -999
    score=0
    its=tokens(text)
    ids=identity_tokens(spec)
    vols=volume_tokens(spec)

    # Strong exact model number match.
    for sku in spec.get("skus") or []:
        no=str(sku.get("product_no") or "")
        if no and re.search(rf"(?<!\d){re.escape(no)}(?!\d)",text):
            score+=220

    # Volume + shape/family identity.
    if any(v in text for v in vols):
        score+=70
    common=ids & its
    score+=min(120,len(common)*22)

    # Alias-aware shape/features.
    for canonical,words in ALIASES.items():
        if canonical in ids and any(w in text for w in words):
            score+=26

    # Avoid obvious unrelated assets.
    bad={"logo","banner","icon","favicon","placeholder","culture","blueberry","raspberry","strawberry","vegetable"}
    if any(x in text for x in bad):
        score-=120
    return score


def enabled_skus(card):
    return [x for x in ((card.get("sku_media") or {}).get("skus") or [])
            if isinstance(x,dict) and x.get("enabled") is not False]


def product_no(sku):
    a=sku.get("attributes") if isinstance(sku.get("attributes"),dict) else {}
    return str(a.get("manufacturer_product_no") or "").strip()


def assigned_count(sku,valid):
    ids=[str(sku.get("primary_media_id") or "")]+[str(x) for x in (sku.get("gallery_media_ids") or [])]
    return len({x for x in ids if x and x in valid})


def patch(spec,card,lib):
    work=deepcopy(card)
    sm=work.setdefault("sku_media",{})
    media=sm.setdefault("media",[])
    by_id={str(x.get("media_id") or ""):x for x in media if isinstance(x,dict) and x.get("media_id")}
    by_path={str(x.get("path") or ""):str(x.get("media_id") or "") for x in media if isinstance(x,dict) and x.get("path") and x.get("media_id")}
    valid=set(by_id)

    ranked=[]
    for item in lib:
        s=score(item,spec)
        if s>=95:
            ranked.append((s,item))
    ranked.sort(key=lambda x:(-x[0],media_path(x[1])))

    added=0
    chosen=[]
    for s,item in ranked[:12]:
        path=media_path(item)
        if not path:continue
        mid=by_path.get(path)
        if not mid:
            mid=stable_mid(path)
            if mid not in by_id:
                row={
                    "media_id":mid,
                    "path":path,
                    "alt":str(item.get("alt_text") or item.get("title") or item.get("name") or spec.get("name") or "Plantlogic"),
                    "kind":"gallery",
                    "sort_order":len(media),
                }
                media.append(row);by_id[mid]=row;by_path[path]=mid;valid.add(mid);added+=1
        if mid not in chosen:
            chosen.append(mid)

    changed_skus=0
    rescued=0
    for sku in enabled_skus(work):
        if assigned_count(sku,valid)>=2:
            continue
        oldp=str(sku.get("primary_media_id") or "")
        oldg=[str(x) for x in (sku.get("gallery_media_ids") or []) if str(x)]
        ids=[]
        for mid in [oldp]+oldg+chosen:
            if mid and mid in valid and mid not in ids:
                ids.append(mid)
        if len(ids)<2:
            continue
        primary=oldp if oldp in valid else ids[0]
        gallery=[x for x in ids if x!=primary]
        sku["primary_media_id"]=primary
        sku["gallery_media_ids"]=gallery
        changed_skus+=1
        rescued+=1

    pcv3.validate(work)
    return work,{"library_added":added,"sku_links_changed":changed_skus,"sku_rescued":rescued,"candidates":len(ranked)}


def build_plan():
    doc=master();lib=library();rows=[]
    before_deficient=0;after_deficient=0;total=0
    for spec in doc["products"]:
        pid=str(spec["product_id"])
        card=pcv3.get(pid)
        if not isinstance(card,dict):
            raise RuntimeError(f"missing card {pid}")
        valid={str(x.get("media_id") or "") for x in ((card.get("sku_media") or {}).get("media") or []) if isinstance(x,dict)}
        before_deficient+=sum(1 for s in enabled_skus(card) if assigned_count(s,valid)<2)
        patched,stats=patch(spec,card,lib)
        valid2={str(x.get("media_id") or "") for x in ((patched.get("sku_media") or {}).get("media") or []) if isinstance(x,dict)}
        after_deficient+=sum(1 for s in enabled_skus(patched) if assigned_count(s,valid2)<2)
        total+=len(enabled_skus(patched))
        rows.append({"product_id":pid,"card":patched,"changed":patched!=card,"stats":stats})
    if total!=EXPECTED_COLOR_SKUS:
        raise RuntimeError(f"color SKU count {total}")
    return {
        "rows":rows,"library_items":len(lib),"total":total,
        "before_deficient":before_deficient,"after_deficient":after_deficient,
        "changed":sum(1 for x in rows if x["changed"]),
        "media_added":sum(x["stats"]["library_added"] for x in rows),
        "sku_links":sum(x["stats"]["sku_links_changed"] for x in rows),
    }


def backup():
    dest=BACKUP_ROOT/f"plantlogic-semantic-media-{stamp()}"
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(pcv3.BASE,dest/"product_cards_v3")
    return dest


def apply(plan):
    before_db=_snapshot_tables()
    before_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    b=backup()
    try:
        for row in plan["rows"]:
            if row["changed"]:
                pcv3.put(row["product_id"],deepcopy(row["card"]))
        if _snapshot_tables()!=before_db:
            raise RuntimeError("commerce database changed")
        after_map=pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map!=before_map:
            raise RuntimeError("commerce_map changed")
        return str(b)
    except Exception:
        if pcv3.BASE.exists():shutil.rmtree(pcv3.BASE)
        shutil.copytree(b/"product_cards_v3",pcv3.BASE)
        raise


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");args=ap.parse_args()
    plan=build_plan()
    print("PLANTLOGIC REMAINING GALLERY FILL")
    print("COLOR SKU:",plan["total"])
    print("MEDIA LIBRARY ITEMS:",plan["library_items"])
    print("SKU WITH <2 PHOTOS BEFORE:",plan["before_deficient"])
    print("SKU WITH <2 PHOTOS AFTER:",plan["after_deficient"])
    print("CARDS TO CHANGE:",plan["changed"])
    print("MEDIA TO ADD:",plan["media_added"])
    print("SKU LINKS TO CHANGE:",plan["sku_links"])
    print("PRICE/STOCK WRITES: 0")
    if not args.apply:
        print("RESULT: PASS (DRY RUN)");return 0
    b=apply(plan)
    REPORT_ROOT.mkdir(parents=True,exist_ok=True)
    rp=REPORT_ROOT/f"plantlogic-semantic-media-{stamp()}.json"
    rp.write_text(json.dumps({k:v for k,v in plan.items() if k!="rows"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("RESULT: PASS")
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:",b)
    print("REPORT:",rp)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
