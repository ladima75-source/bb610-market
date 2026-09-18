from __future__ import annotations

"""Read-only audit for public storefront products that have no SKU/price path.

The storefront currently has 77 published public products but only 68 products
with runtime SKU. This audit enumerates every public product, classifies the gap,
looks for a matching Product Card v3 card, and searches the approved 2026-09-16
195-row price source for deterministic package/price candidates.

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
from backend.services import product_cards_v3 as pcv3

PRICE_SOURCE = ROOT / "data" / "catalog_sources" / "bb610_market_prices_2026-09-16.json"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PUBLIC = 77
EXPECTED_WITH_SKU = 68
EXPECTED_NO_SKU = 9


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def norm(value: Any) -> str:
    s = unicodedata.normalize("NFKC", str(value or "")).lower()
    replacements = {
        "ё": "е",
        "ґ": "г",
        "і": "i",
        "ї": "i",
        "є": "е",
        "–": "-",
        "—": "-",
        "−": "-",
        "міс.": "m",
        "міс": "m",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r"[^0-9a-zа-я+%-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def formula(value: Any) -> tuple[str, str, str] | None:
    s = str(value or "").replace("–", "-").replace("—", "-")
    m = re.search(r"(?<!\d)(\d{1,2})\s*[-+]\s*(\d{1,2})\s*[-+]\s*(\d{1,2})(?!\d)", s)
    return tuple(m.groups()) if m else None


def family(value: Any) -> str:
    n = norm(value)
    if "osmocote" in n or "осмокот" in n:
        return "osmocote"
    if "pekacid" in n or "пекацид" in n:
        return "pekacid"
    if "plantafol" in n or "плантафол" in n:
        return "plantafol"
    if "master" in n or "мастер" in n:
        return "master"
    if "brexil" in n or "брекс" in n:
        return "brexil"
    if "solupotasse" in n or "сульфат кал" in n:
        return "solupotasse"
    if "haifa" in n or "хаiфа" in n or "хайфа" in n:
        return "haifa"
    return ""


def osmocote_variant(value: Any) -> str:
    n = norm(value)
    aliases = [
        (("quick start", "швидкий старт", "быстрый старт"), "quick-start"),
        (("landscape", "ландшафт"), "landscape"),
        (("potassium", "калiйний", "калийный"), "potassium"),
        (("bloom", "квiтучий", "цветущий"), "bloom"),
        (("decor", "декор"), "decor"),
        (("start", "старт"), "start"),
    ]
    for words, result in aliases:
        if any(w in n for w in words):
            return result
    return ""


def score_name(product_name: str, source_name: str) -> tuple[int, list[str]]:
    pn, sn = norm(product_name), norm(source_name)
    pf, sf = family(product_name), family(source_name)
    pform, sform = formula(product_name), formula(source_name)
    score = 0
    reasons: list[str] = []

    if pn == sn and pn:
        score += 1000
        reasons.append("normalized_name_exact")

    if pf and pf == sf:
        score += 250
        reasons.append("family="+pf)

    if pform and pform == sform:
        score += 500
        reasons.append("formula="+"-".join(pform))
    elif pform and sform and pform != sform:
        return -1000, ["formula_conflict"]

    if pf == "osmocote" and sf == "osmocote":
        pv, sv = osmocote_variant(product_name), osmocote_variant(source_name)
        if pv and sv and pv == sv:
            score += 350
            reasons.append("osmocote_variant="+pv)
        elif pv and sv and pv != sv:
            return -1000, ["osmocote_variant_conflict"]

    # Token overlap adds only tie-breaking confidence.
    pt = {x for x in pn.split() if len(x) >= 4}
    st = {x for x in sn.split() if len(x) >= 4}
    overlap = sorted(pt & st)
    if overlap:
        score += min(100, len(overlap) * 20)
        reasons.append("tokens="+",".join(overlap[:8]))

    return score, reasons


def load_prices() -> list[dict]:
    doc = json.loads(PRICE_SOURCE.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if not isinstance(rows, list) or len(rows) != 195:
        raise RuntimeError(f"expected 195 approved price rows, got {len(rows or [])}")
    return rows


def v3_cards() -> list[dict]:
    out = []
    for summary in pcv3.list_cards():
        pid = str(summary.get("product_id") or "")
        card = pcv3.get(pid) if pid else None
        if isinstance(card, dict):
            out.append(card)
    return out


def v3_match(product: dict, cards: list[dict]) -> dict:
    pid = str(product.get("id") or "")
    direct = next((c for c in cards if str(c.get("product_id") or "") == pid), None)
    if direct:
        return {"mode": "product_id", "card": direct}

    pname = str(product.get("name") or "")
    scored = []
    for card in cards:
        title = str((card.get("content") or {}).get("title") or "")
        sc, reasons = score_name(pname, title)
        if sc > 0:
            scored.append((sc, card, reasons))
    scored.sort(key=lambda x: -x[0])
    if scored and (len(scored) == 1 or scored[0][0] > scored[1][0]):
        sc, card, reasons = scored[0]
        return {"mode": "name_score", "score": sc, "reasons": reasons, "card": card}
    return {"mode": "none", "card": None}


def main() -> int:
    public_doc = public_content()
    public_products = [
        dict(p) for p in (public_doc.get("products") or [])
        if isinstance(p, dict) and p.get("id") and not p.get("runtime_hidden")
    ]
    public_skus = [
        dict(s) for s in (public_doc.get("skus") or [])
        if isinstance(s, dict) and s.get("product_id")
    ]
    sku_by_product: dict[str, list[dict]] = defaultdict(list)
    for sku in public_skus:
        sku_by_product[str(sku.get("product_id"))].append(sku)

    prices = load_prices()
    cards = v3_cards()

    no_sku_products = [
        p for p in public_products if not sku_by_product.get(str(p.get("id")))
    ]

    gaps = []
    for product in no_sku_products:
        pid = str(product.get("id") or "")
        pname = str(product.get("name") or product.get("official_name") or "")
        slug = str(product.get("slug") or pid)
        detail = admin_detail(pid) or {}

        candidates = []
        for idx, src in enumerate(prices, start=2):
            sc, reasons = score_name(pname, str(src.get("source_name") or ""))
            if sc <= 0:
                continue
            candidates.append({
                "source_row": idx,
                "source_name": src.get("source_name"),
                "package": src.get("package"),
                "price": src.get("price"),
                "score": sc,
                "reasons": reasons,
            })
        candidates.sort(key=lambda x: (-x["score"], x["source_row"]))

        # A safe match is a unique source product-name identity. All of its package
        # rows may then be restored later, but this audit itself never writes.
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in candidates:
            grouped[str(row["source_name"])].append(row)
        ranked_groups = sorted(
            grouped.items(),
            key=lambda kv: -max(x["score"] for x in kv[1]),
        )
        safe_group = None
        if ranked_groups:
            top_name, top_rows = ranked_groups[0]
            top_score = max(x["score"] for x in top_rows)
            next_score = (
                max(x["score"] for x in ranked_groups[1][1])
                if len(ranked_groups) > 1 else -1
            )
            # formula+family, exact name, or Osmocote family+variant+formula
            # produces >= 700. Require a clear winning identity.
            if top_score >= 700 and top_score > next_score:
                safe_group = {
                    "source_name": top_name,
                    "score": top_score,
                    "rows": top_rows,
                }

        vm = v3_match(product, cards)
        card = vm.get("card")
        card_skus = [
            x for x in (((card or {}).get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict)
        ]

        gaps.append({
            "product_id": pid,
            "slug": slug,
            "name": pname,
            "brand": product.get("brand"),
            "category_id": product.get("category_id"),
            "published": bool(detail.get("published", True)),
            "default_sku_id": detail.get("default_sku_id"),
            "public_sku_count": 0,
            "v3_match_mode": vm.get("mode"),
            "v3_product_id": (card or {}).get("product_id"),
            "v3_slug": (card or {}).get("slug"),
            "v3_sku_count": len(card_skus),
            "v3_packages": [
                x.get("package") or x.get("label") for x in card_skus
            ],
            "safe_price_source_match": safe_group,
            "top_price_candidates": candidates[:12],
        })

    safe_count = sum(1 for x in gaps if x["safe_price_source_match"])
    v3_count = sum(1 for x in gaps if x["v3_product_id"])

    report = {
        "mode": "READ_ONLY",
        "public_products": len(public_products),
        "public_skus": len(public_skus),
        "products_with_sku": len(public_products) - len(no_sku_products),
        "products_without_sku": len(no_sku_products),
        "no_sku_with_v3_card": v3_count,
        "no_sku_with_safe_price_source_match": safe_count,
        "gaps": gaps,
    }

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"storefront-public-sku-price-gaps-{stamp()}.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("BB610 STOREFRONT PUBLIC SKU / PRICE GAP AUDIT")
    print("MODE: READ_ONLY")
    print("PUBLIC PRODUCTS:", len(public_products))
    print("PRODUCTS WITH SKU:", len(public_products) - len(no_sku_products))
    print("PRODUCTS WITHOUT SKU:", len(no_sku_products))
    print("NO-SKU WITH V3 CARD:", v3_count)
    print("NO-SKU WITH SAFE PRICE SOURCE MATCH:", safe_count)
    print()

    for i, row in enumerate(gaps, start=1):
        match = row["safe_price_source_match"]
        print(
            f"{i:02d}. {row['slug']} | {row['name']} | "
            f"v3={row['v3_slug'] or '-'} sku={row['v3_sku_count']}"
        )
        if match:
            packages = ", ".join(
                f"{x['package']}={x['price']}" for x in match["rows"]
            )
            print(
                f"    SOURCE SAFE: {match['source_name']} | score={match['score']} | {packages}"
            )
        else:
            print("    SOURCE SAFE: NONE")
            for cand in row["top_price_candidates"][:3]:
                print(
                    "    CANDIDATE:",
                    cand["source_name"],
                    "|", cand["package"],
                    "=", cand["price"],
                    "| score=", cand["score"],
                )

    print()
    print("REPORT:", path)
    if (
        len(public_products) == EXPECTED_PUBLIC
        and len(public_products) - len(no_sku_products) == EXPECTED_WITH_SKU
        and len(no_sku_products) == EXPECTED_NO_SKU
    ):
        print("RESULT: PASS (READ_ONLY)")
    else:
        print("RESULT: REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
