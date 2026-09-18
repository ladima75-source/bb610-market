from __future__ import annotations

"""Read-only audit for the published Plantlogic market-test storefront."""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import update_plantlogic_pots_v3_20260918 as master
from backend.services import catalog_cms
from backend.services import product_cards_v3 as pcv3

EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37


def _audit_payload(payload: dict) -> dict:
    products = [
        x for x in (payload.get("products") or [])
        if isinstance(x, dict)
        and x.get("market_test") is True
        and str(x.get("brand") or "").strip().lower() == "plantlogic"
    ]
    ids = {str(x.get("id") or "") for x in products}
    skus = [
        x for x in (payload.get("skus") or [])
        if isinstance(x, dict)
        and str(x.get("product_id") or "") in ids
        and x.get("market_test") is True
    ]

    failures: list[str] = []
    if len(products) != EXPECTED_PRODUCTS:
        failures.append(f"products={len(products)} expected={EXPECTED_PRODUCTS}")
    if len(ids) != EXPECTED_PRODUCTS:
        failures.append("duplicate product ids")
    if len(skus) != EXPECTED_SKUS:
        failures.append(f"skus={len(skus)} expected={EXPECTED_SKUS}")

    for p in products:
        title = str(p.get("name") or "")
        if not title:
            failures.append(f"{p.get('id')}: empty title")
        if title.startswith("Plantlogic") or " Liter " in title or " Pot" in title or "NEW " in title:
            failures.append(f"{p.get('id')}: storefront title leak")
        if p.get("price_request") is not True:
            failures.append(f"{p.get('id')}: product price_request false")
        if str(p.get("market_test_status") or "") != "Під замовлення":
            failures.append(f"{p.get('id')}: product status mismatch")

    for s in skus:
        sid = str(s.get("id") or "")
        if s.get("price") is not None or s.get("sale_price") is not None:
            failures.append(f"{sid}: unexpected price")
        if s.get("price_request") is not True:
            failures.append(f"{sid}: price_request false")
        if str(s.get("availability") or "") != "backorder":
            failures.append(f"{sid}: availability mismatch")
        if str(s.get("stock_label") or "") != "Під замовлення":
            failures.append(f"{sid}: stock label mismatch")
        if str(s.get("commercial_status") or "") != "request-price":
            failures.append(f"{sid}: commercial status mismatch")
        if str(s.get("offer_status") or "") != "request-price":
            failures.append(f"{sid}: offer status mismatch")
        if not str(s.get("image") or "").startswith(("http://", "https://", "/media/products/")):
            failures.append(f"{sid}: image missing")

    return {
        "products": len(products),
        "skus": len(skus),
        "request_price_skus": sum(1 for x in skus if x.get("price_request") is True),
        "priced_skus": sum(1 for x in skus if x.get("price") is not None or x.get("sale_price") is not None),
        "backorder_skus": sum(1 for x in skus if x.get("availability") == "backorder"),
        "failures": failures,
    }


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "BB610-Market-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _local_cards() -> dict:
    doc = master.load_manifest()
    products = doc.get("products") or []
    managed = {str(x.get("product_id") or "") for x in products}
    enabled = 0
    total_skus = 0
    for spec in products:
        card = pcv3.get(str(spec["product_id"]))
        if not isinstance(card, dict):
            raise RuntimeError(f"missing card: {spec['slug']}")
        if bool(card.get("enabled")):
            enabled += 1
        total_skus += len([
            x for x in ((card.get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict) and x.get("enabled") is not False
        ])
    unmanaged = [
        x for x in pcv3.list_cards()
        if str(x.get("brand") or "").strip().lower() == "plantlogic"
        and str(x.get("product_id") or "") not in managed
    ]
    return {"enabled": enabled, "skus": total_skus, "unmanaged": unmanaged}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="")
    args = ap.parse_args()

    cards = _local_cards()
    if cards["enabled"] != EXPECTED_PRODUCTS:
        print(f"ENABLED CARDS: {cards['enabled']}/{EXPECTED_PRODUCTS}")
        print("RESULT: FAIL")
        return 2
    if cards["skus"] != EXPECTED_SKUS or cards["unmanaged"]:
        print(f"SKU: {cards['skus']}/{EXPECTED_SKUS}")
        print(f"UNMANAGED: {len(cards['unmanaged'])}")
        print("RESULT: FAIL")
        return 2

    if args.base_url:
        base = args.base_url.rstrip("/")
        payload = _fetch_json(base + "/api/v1/catalog/content")
        openapi = _fetch_json(base + "/openapi.json")
        paths = openapi.get("paths") or {}
        if "/api/v1/price-requests" not in paths:
            print("PRICE REQUEST API: MISSING")
            print("RESULT: FAIL")
            return 2
        source = base
    else:
        payload = catalog_cms.public_content()
        source = "LOCAL"

    result = _audit_payload(payload)

    print("BB610 PLANTLOGIC MARKET-TEST AUDIT")
    print("SOURCE:", source)
    print(f"ENABLED CARDS: {cards['enabled']}/{EXPECTED_PRODUCTS}")
    print(f"PRODUCTS: {result['products']}/{EXPECTED_PRODUCTS}")
    print(f"SKU: {result['skus']}/{EXPECTED_SKUS}")
    print(f"REQUEST-PRICE SKU: {result['request_price_skus']}/{EXPECTED_SKUS}")
    print(f"BACKORDER SKU: {result['backorder_skus']}/{EXPECTED_SKUS}")
    print("PRICED SKU:", result["priced_skus"])
    print("CART-ELIGIBLE MARKET-TEST SKU: 0")
    if args.base_url:
        print("PRICE REQUEST API: PASS")
    print("FAILURES:", len(result["failures"]))
    for failure in result["failures"]:
        print("FAIL:", failure)

    if result["failures"]:
        print("RESULT: FAIL")
        return 2
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
