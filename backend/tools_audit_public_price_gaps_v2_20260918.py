from __future__ import annotations

"""Accurate read-only audit for public storefront price gaps.

Unlike the earlier audit, this one uses admin_detail(product_id), which merges
STATIC + DYNAMIC SKU and live sku_commerce, so published products are not
incorrectly classified as SKU-less.

Classification per public product:
- NO_SKU: no static/dynamic SKU at all;
- NO_COMMERCE: SKU exists but no sku_commerce row;
- NO_PRICE: commerce exists but every SKU has effective_price=None;
- PRICED: at least one SKU has a real price.

It also checks whether the storefront display selection would have a priced SKU
available, and searches the approved 195-row price source for deterministic
matches for any true gap.

NO WRITES.
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.catalog_cms import public_content, admin_detail
from backend.services.product_commerce import commerce_map

PRICE_SOURCE = ROOT / "data" / "catalog_sources" / "bb610_market_prices_2026-09-16.json"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PUBLIC = 77


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def norm(value: Any) -> str:
    s = unicodedata.normalize("NFKC", str(value or "")).lower()
    table = {
        "ё":"е","ґ":"г","і":"i","ї":"i","є":"е",
        "–":"-","—":"-","−":"-",
    }
    for a,b in table.items():
        s=s.replace(a,b)
    s=re.sub(r"[^0-9a-zа-я+%-]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()


def formula(value: Any) -> tuple[str,str,str] | None:
    s=str(value or "").replace("–","-").replace("—","-")
    m=re.search(r"(?<!\d)(\d{1,2})\s*[-+]\s*(\d{1,2})\s*[-+]\s*(\d{1,2})(?!\d)",s)
    return tuple(m.groups()) if m else None


def family(value: Any) -> str:
    n=norm(value)
    for needles,result in [
        (("osmocote","осмокот"),"osmocote"),
        (("pekacid","пекацид"),"pekacid"),
        (("plantafol","плантафол"),"plantafol"),
        (("master","мастер"),"master"),
        (("brexil","брекс"),"brexil"),
        (("megafol","мегафол"),"megafol"),
        (("radifarm","радифарм"),"radifarm"),
        (("viva","вива"),"viva"),
        (("blackjak","blackjak"),"blackjak"),
    ]:
        if any(x in n for x in needles):
            return result
    return ""


def osmocote_variant(value: Any) -> str:
    n=norm(value)
    for needles,result in [
        (("quick start","швидкий старт","быстрый старт"),"quick-start"),
        (("landscape","ландшафт"),"landscape"),
        (("potassium","калiйний","калийный"),"potassium"),
        (("bloom","квiтучий","цветущий"),"bloom"),
        (("decor","декор"),"decor"),
        (("start","старт"),"start"),
    ]:
        if any(x in n for x in needles):
            return result
    return ""


def score_name(product_name: str, source_name: str) -> tuple[int,list[str]]:
    pn,sn=norm(product_name),norm(source_name)
    pf,sf=family(product_name),family(source_name)
    pform,sform=formula(product_name),formula(source_name)
    score=0
    reasons=[]

    if pn and pn==sn:
        score+=1000; reasons.append("normalized_name_exact")
    if pf and pf==sf:
        score+=250; reasons.append("family="+pf)

    if pform and sform:
        if pform!=sform:
            return -1000,["formula_conflict"]
        score+=500; reasons.append("formula="+"-".join(pform))

    if pf=="osmocote" and sf=="osmocote":
        pv,sv=osmocote_variant(product_name),osmocote_variant(source_name)
        if pv and sv:
            if pv!=sv:
                return -1000,["osmocote_variant_conflict"]
            score+=350; reasons.append("osmocote_variant="+pv)

    pt={x for x in pn.split() if len(x)>=4}
    st={x for x in sn.split() if len(x)>=4}
    overlap=sorted(pt&st)
    if overlap:
        score+=min(120,len(overlap)*20)
        reasons.append("tokens="+",".join(overlap[:8]))

    return score,reasons


def load_prices() -> list[dict]:
    doc=json.loads(PRICE_SOURCE.read_text(encoding="utf-8"))
    rows=doc.get("rows") if isinstance(doc,dict) else None
    if not isinstance(rows,list) or len(rows)!=195:
        raise RuntimeError(f"expected 195 approved price rows, got {len(rows or [])}")
    return rows


def safe_price_match(name: str, rows: list[dict]) -> dict | None:
    candidates=[]
    for idx,row in enumerate(rows,start=2):
        sc,reasons=score_name(name,str(row.get("source_name") or ""))
        if sc>0:
            candidates.append({
                "source_row":idx,
                "source_name":row.get("source_name"),
                "package":row.get("package"),
                "price":row.get("price"),
                "score":sc,
                "reasons":reasons,
            })
    grouped=defaultdict(list)
    for row in candidates:
        grouped[str(row["source_name"])].append(row)
    ranked=sorted(grouped.items(),key=lambda kv:-max(x["score"] for x in kv[1]))
    if not ranked:
        return None
    top_name,top_rows=ranked[0]
    top_score=max(x["score"] for x in top_rows)
    next_score=max((x["score"] for x in ranked[1][1]),default=-1) if len(ranked)>1 else -1
    if top_score>=700 and top_score>next_score:
        return {"source_name":top_name,"score":top_score,"rows":top_rows}
    return None


def sku_id(row: dict) -> str:
    return str(row.get("id") or row.get("sku") or "").strip()


def effective_price(row: dict) -> Any:
    if row.get("sale_price") is not None:
        return row.get("sale_price")
    return row.get("price")


def main() -> int:
    public_doc=public_content()
    products=[
        dict(p) for p in (public_doc.get("products") or [])
        if isinstance(p,dict) and p.get("id") and not p.get("runtime_hidden")
    ]
    cm=commerce_map()
    prices=load_prices()

    audits=[]
    counts=defaultdict(int)

    for p in products:
        pid=str(p.get("id") or "")
        detail=admin_detail(pid) or {}
        name=str(detail.get("name") or p.get("name") or p.get("official_name") or pid)
        slug=str(detail.get("slug") or p.get("slug") or pid)
        skus=[dict(x) for x in (detail.get("skus") or []) if isinstance(x,dict)]

        sku_rows=[]
        for s in skus:
            sid=sku_id(s)
            live=cm.get(sid)
            sku_rows.append({
                "sku":sid,
                "variant":s.get("variant") or s.get("package") or s.get("label"),
                "commerce_exists":isinstance(live,dict),
                "price":(live or {}).get("price") if isinstance(live,dict) else None,
                "sale_price":(live or {}).get("sale_price") if isinstance(live,dict) else None,
                "effective_price":effective_price(live) if isinstance(live,dict) else None,
                "availability":(live or {}).get("availability") if isinstance(live,dict) else None,
                "enabled":bool((live or {}).get("enabled")) if isinstance(live,dict) else None,
            })

        if not skus:
            status="NO_SKU"
        elif not any(x["commerce_exists"] for x in sku_rows):
            status="NO_COMMERCE"
        elif not any(x["effective_price"] is not None for x in sku_rows):
            status="NO_PRICE"
        else:
            status="PRICED"

        counts[status]+=1
        match=safe_price_match(name,prices) if status!="PRICED" else None

        audits.append({
            "product_id":pid,
            "slug":slug,
            "name":name,
            "brand":detail.get("brand") or p.get("brand"),
            "published":bool(detail.get("published",True)),
            "status":status,
            "sku_count":len(skus),
            "priced_sku_count":sum(1 for x in sku_rows if x["effective_price"] is not None),
            "active_priced_sku_count":sum(1 for x in sku_rows if x["effective_price"] is not None and x["enabled"]),
            "skus":sku_rows,
            "safe_price_source_match":match,
        })

    gaps=[x for x in audits if x["status"]!="PRICED"]

    REPORT_ROOT.mkdir(parents=True,exist_ok=True)
    path=REPORT_ROOT/f"storefront-public-price-gaps-v2-{stamp()}.json"
    payload={
        "mode":"READ_ONLY",
        "public_products":len(products),
        "priced_products":counts["PRICED"],
        "no_sku":counts["NO_SKU"],
        "no_commerce":counts["NO_COMMERCE"],
        "no_price":counts["NO_PRICE"],
        "gaps":gaps,
    }
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    print("BB610 STOREFRONT PUBLIC PRICE GAP AUDIT V2")
    print("MODE: READ_ONLY")
    print("PUBLIC PRODUCTS:",len(products))
    print("PRICED PRODUCTS:",counts["PRICED"])
    print("NO SKU:",counts["NO_SKU"])
    print("NO COMMERCE:",counts["NO_COMMERCE"])
    print("NO PRICE:",counts["NO_PRICE"])
    print("TOTAL PRICE GAPS:",len(gaps))
    print()

    for i,row in enumerate(gaps,start=1):
        print(f"{i:02d}. [{row['status']}] {row['slug']} | {row['name']} | sku={row['sku_count']} priced={row['priced_sku_count']} active_priced={row['active_priced_sku_count']}")
        for s in row["skus"]:
            print(
                "    SKU",s["sku"],"|",s["variant"],
                "| commerce=",s["commerce_exists"],
                "| price=",s["effective_price"],
                "| enabled=",s["enabled"],
                "| availability=",s["availability"],
            )
        match=row["safe_price_source_match"]
        if match:
            packs=", ".join(f"{x['package']}={x['price']}" for x in match["rows"])
            print("    SOURCE SAFE:",match["source_name"],"|",packs)
        else:
            print("    SOURCE SAFE: NONE")

    print()
    print("REPORT:",path)
    print("RESULT: PASS (READ_ONLY)" if len(products)==EXPECTED_PUBLIC else "RESULT: REVIEW")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
