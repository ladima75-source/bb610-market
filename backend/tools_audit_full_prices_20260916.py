from __future__ import annotations

"""Read-only production audit for the approved 2026-09-16 BB610 Market price file.

The audit composes the already-reviewed import paths instead of inventing a new
matcher:
- 49 Valagro/Syngenta rows use the deterministic runtime reconciler;
- 138 non-Valagro exact rows use the conservative exact importer classifier;
- 8 reviewed ambiguous rows use the explicit title+package resolver.

Expected production contract:
- source rows: 195;
- positive-price rows: 194, each mapped to exactly one commerce SKU;
- every positive row has exact base price, availability=in_stock,
  stock_qty=NULL and enabled=1;
- storefront runtime is bound and projects the same base price with active
  offer/commercial status;
- the only zero-price row is MASTER 15-5-30 / 20 g and remains disabled/paused;
- no writes are performed.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import tools_apply_remaining_prices_20260916_exact as remaining
from backend import tools_apply_valagro_prices_20260916_runtime as valagro
from backend import tools_resolve_remaining_ambiguous_prices_20260916 as reviewed
from backend.db import connect
from backend.services import product_cards_v3 as pcv3
from backend.services import product_cards_v3_runtime as runtime

SOURCE = ROOT / "data" / "catalog_sources" / "bb610_market_prices_2026-09-16.json"
EXPECTED_TOTAL = 195
EXPECTED_POSITIVE = 194
EXPECTED_ZERO = 1
EXPECTED_VALAGRO = 49
EXPECTED_REMAINING_EXACT = 138
EXPECTED_REVIEWED = 8


def _f(value):
    return None if value is None else float(value)


def _source_rows() -> list[dict]:
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if doc.get("source_file") != "цены_сайт_Market_160926.xlsx":
        raise RuntimeError(f"unexpected source_file: {doc.get('source_file')!r}")
    if doc.get("source_date") != "2026-09-16":
        raise RuntimeError(f"unexpected source_date: {doc.get('source_date')!r}")
    if not isinstance(rows, list) or len(rows) != EXPECTED_TOTAL:
        raise RuntimeError(f"expected {EXPECTED_TOTAL} source rows; got {len(rows or [])}")
    return [dict(x, source_row=i) for i, x in enumerate(rows, start=2)]


def _runtime_index(product_id: str, cache: dict[str, dict]) -> dict[str, dict]:
    if product_id in cache:
        return cache[product_id]
    card = pcv3.get(product_id)
    if not isinstance(card, dict):
        raise RuntimeError(f"PCV3 card missing: {product_id}")
    slug = str(card.get("slug") or "").strip()
    doc = runtime.storefront_runtime(slug)
    if not isinstance(doc, dict):
        raise RuntimeError(f"storefront runtime missing: {slug or product_id}")
    index = {
        str(x.get("commerce_key") or ""): x
        for x in (doc.get("skus") or [])
        if isinstance(x, dict) and x.get("commerce_key")
    }
    cache[product_id] = index
    return index


def audit() -> dict:
    source = _source_rows()
    positive_source_rows = {int(x["source_row"]) for x in source if float(x.get("price") or 0) > 0}
    zero_source = [x for x in source if float(x.get("price") or 0) <= 0]
    if len(positive_source_rows) != EXPECTED_POSITIVE or len(zero_source) != EXPECTED_ZERO:
        raise RuntimeError(
            f"source price cardinality drift: positive={len(positive_source_rows)} zero={len(zero_source)}"
        )

    v = valagro.build_plan()
    r = remaining.classify()
    m = reviewed.build_plan()

    errors: list[str] = []
    if v.get("source_target_rows") != EXPECTED_VALAGRO:
        errors.append(f"Valagro source rows: {v.get('source_target_rows')} != {EXPECTED_VALAGRO}")
    if len(v.get("actions") or []) != 48:
        errors.append(f"Valagro positive actions: {len(v.get('actions') or [])} != 48")
    if len(v.get("zero_price_skipped") or []) != 1:
        errors.append(f"Valagro zero rows: {len(v.get('zero_price_skipped') or [])} != 1")
    if v.get("source_without_current_sku"):
        errors.append(f"Valagro source_without_current_sku={len(v['source_without_current_sku'])}")
    if v.get("current_without_source_price"):
        errors.append(f"Valagro current_without_source_price={len(v['current_without_source_price'])}")

    if r.get("source_rows") != 146:
        errors.append(f"remaining source rows: {r.get('source_rows')} != 146")
    if len(r.get("actions") or []) != EXPECTED_REMAINING_EXACT:
        errors.append(f"remaining exact actions: {len(r.get('actions') or [])} != {EXPECTED_REMAINING_EXACT}")
    if len(r.get("ambiguous") or []) != EXPECTED_REVIEWED:
        errors.append(f"remaining ambiguous rows: {len(r.get('ambiguous') or [])} != {EXPECTED_REVIEWED}")
    if r.get("unmatched"):
        errors.append(f"remaining unmatched={len(r['unmatched'])}")
    if r.get("missing_commerce"):
        errors.append(f"remaining missing_commerce={len(r['missing_commerce'])}")
    if r.get("zero_price"):
        errors.append(f"unexpected non-Valagro zero rows={len(r['zero_price'])}")
    if len(m.get("actions") or []) != EXPECTED_REVIEWED:
        errors.append(f"reviewed actions: {len(m.get('actions') or [])} != {EXPECTED_REVIEWED}")

    positive = []
    for row in v.get("actions") or []:
        positive.append({
            "source_row": int(row["source_row"]),
            "price": float(row["price"]),
            "product_id": str(row["product_id"]),
            "commerce_key": str(row["commerce_key"]),
            "live": {
                "price": row.get("current_price"),
                "availability": row.get("current_availability"),
                "stock_qty": row.get("current_stock_qty"),
                "enabled": row.get("current_enabled"),
            },
            "scope": "valagro",
        })
    for row in r.get("actions") or []:
        positive.append({
            "source_row": int(row["source_row"]),
            "price": float(row["price"]),
            "product_id": str(row["product_id"]),
            "commerce_key": str(row["commerce_key"]),
            "live": row.get("before") or {},
            "scope": "remaining_exact",
        })
    for row in m.get("actions") or []:
        positive.append({
            "source_row": int(row["source_row"]),
            "price": float(row["price"]),
            "product_id": str(row["product_id"]),
            "commerce_key": str(row["commerce_key"]),
            "live": row.get("before") or {},
            "scope": "reviewed",
        })

    row_ids = [x["source_row"] for x in positive]
    keys = [x["commerce_key"] for x in positive]
    if len(positive) != EXPECTED_POSITIVE:
        errors.append(f"positive mapped rows={len(positive)} != {EXPECTED_POSITIVE}")
    if len(row_ids) != len(set(row_ids)):
        errors.append("duplicate positive source_row mapping")
    if set(row_ids) != positive_source_rows:
        errors.append(
            f"positive source coverage mismatch missing={sorted(positive_source_rows-set(row_ids))} extra={sorted(set(row_ids)-positive_source_rows)}"
        )
    if len(keys) != len(set(keys)):
        errors.append("duplicate positive commerce mapping")

    runtime_cache: dict[str, dict] = {}
    for item in positive:
        live = item["live"]
        key = item["commerce_key"]
        if _f(live.get("price")) != item["price"]:
            errors.append(f"row {item['source_row']} {key}: base price {live.get('price')} != {item['price']}")
        if live.get("availability") != "in_stock":
            errors.append(f"row {item['source_row']} {key}: availability={live.get('availability')}")
        if live.get("stock_qty") is not None:
            errors.append(f"row {item['source_row']} {key}: stock_qty must be NULL")
        if not bool(live.get("enabled")):
            errors.append(f"row {item['source_row']} {key}: enabled is false")

        try:
            idx = _runtime_index(item["product_id"], runtime_cache)
            sku = idx.get(key)
            if not isinstance(sku, dict):
                errors.append(f"row {item['source_row']} {key}: storefront SKU missing")
                continue
            if not sku.get("commerce_bound"):
                errors.append(f"row {item['source_row']} {key}: storefront unbound")
            commerce = sku.get("commerce") or {}
            if _f(commerce.get("base_price")) != item["price"]:
                errors.append(f"row {item['source_row']} {key}: storefront base_price={commerce.get('base_price')}")
            if commerce.get("availability") != "in_stock":
                errors.append(f"row {item['source_row']} {key}: storefront availability={commerce.get('availability')}")
            if commerce.get("offer_status") != "active" or commerce.get("commercial_status") != "active":
                errors.append(
                    f"row {item['source_row']} {key}: storefront status={commerce.get('offer_status')}/{commerce.get('commercial_status')}"
                )
        except Exception as exc:
            errors.append(f"row {item['source_row']} {key}: storefront audit error: {exc}")

    zero = (v.get("zero_price_skipped") or [None])[0]
    zero_summary = None
    if isinstance(zero, dict):
        key = str(zero.get("commerce_key") or "")
        with connect() as con:
            dbrow = con.execute(
                "SELECT sku,price,sale_price,availability,stock_qty,enabled FROM sku_commerce WHERE sku=?",
                (key,),
            ).fetchone()
        if not dbrow:
            errors.append(f"zero-price commerce row missing: {key}")
        else:
            live = dict(dbrow)
            if live.get("price") not in (None, 0, 0.0):
                errors.append(f"zero-price row {key}: price must stay NULL/0, got {live.get('price')}")
            if bool(live.get("enabled")):
                errors.append(f"zero-price row {key}: enabled must stay false")
            doc = runtime.storefront_runtime(str(zero.get("slug") or ""))
            sku = next(
                (x for x in (doc or {}).get("skus", []) if str(x.get("commerce_key") or "") == key),
                None,
            )
            if not isinstance(sku, dict):
                errors.append(f"zero-price row {key}: storefront SKU missing")
            else:
                commerce = sku.get("commerce") or {}
                if commerce.get("offer_status") != "draft" or commerce.get("commercial_status") != "paused":
                    errors.append(
                        f"zero-price row {key}: storefront status={commerce.get('offer_status')}/{commerce.get('commercial_status')}"
                    )
            zero_summary = {
                "source_row": zero.get("source_row"),
                "slug": zero.get("slug"),
                "package": zero.get("package"),
                "commerce_key": key,
                "price": live.get("price"),
                "enabled": bool(live.get("enabled")),
            }
    else:
        errors.append("zero-price source row not resolved")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "source_rows": EXPECTED_TOTAL,
        "positive_source_rows": EXPECTED_POSITIVE,
        "zero_source_rows": EXPECTED_ZERO,
        "mapped_positive_rows": len(positive),
        "valagro_positive": len(v.get("actions") or []),
        "remaining_exact_positive": len(r.get("actions") or []),
        "reviewed_positive": len(m.get("actions") or []),
        "storefront_products_checked": len(runtime_cache),
        "zero_policy": zero_summary,
        "errors": errors,
    }
    return result


def main() -> int:
    result = audit()
    print("BB610 FULL PRICE PRODUCTION AUDIT — 2026-09-16")
    print(f"SOURCE ROWS: {result['source_rows']}")
    print(f"POSITIVE SOURCE ROWS: {result['positive_source_rows']}")
    print(f"MAPPED POSITIVE ROWS: {result['mapped_positive_rows']}")
    print(f"VALAGRO POSITIVE: {result['valagro_positive']}")
    print(f"REMAINING EXACT POSITIVE: {result['remaining_exact_positive']}")
    print(f"REVIEWED POSITIVE: {result['reviewed_positive']}")
    print(f"STOREFRONT PRODUCTS CHECKED: {result['storefront_products_checked']}")
    print(f"ZERO POLICY: {json.dumps(result['zero_policy'], ensure_ascii=False)}")
    print(f"RESULT: {result['status']}")
    if result["errors"]:
        for err in result["errors"][:100]:
            print("ERROR:", err)
        return 1
    print("FULL PRICE AUDIT: 195/195 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
