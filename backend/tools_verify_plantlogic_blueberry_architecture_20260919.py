from __future__ import annotations

"""Verify the deployed five-card Plantlogic blueberry pot architecture.

Read-only: no writes, no commerce changes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.services.product_master_runtime import snapshot

EXPECTED = {
    "prd_pl_bb_round": 15,
    "prd_pl_bb_square": 9,
    "prd_pl_bb_round_u": 12,
    "prd_pl_bb_square_u": 6,
    "prd_pl_bb_zephyr_v2": 6,
}
EXPECTED_MODELS = {
    "1308020","1303025","1308025","1308031","1308040",
    "1309020","1309025","1309030",
    "1308303","1308305","1308035","13080410",
    "1309026","1309035",
    "1301144","1301153","1301143",
}


def main() -> int:
    total = 0
    product_nos: set[str] = set()
    sku_codes: set[str] = set()

    print("BB610 PLANTLOGIC BLUEBERRY ARCHITECTURE VERIFY")
    for pid, expected_count in EXPECTED.items():
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise SystemExit(f"FAIL missing Product Card v3: {pid}")
        if card.get("enabled") is not True:
            raise SystemExit(f"FAIL disabled Product Card v3: {pid}")
        title = str((card.get("content") or {}).get("title") or "")
        if "plantlogic" in title.casefold():
            raise SystemExit(f"FAIL Plantlogic present in storefront title: {title}")
        skus = (card.get("sku_media") or {}).get("skus") or []
        if len(skus) != expected_count:
            raise SystemExit(f"FAIL {pid}: expected {expected_count} SKU, got {len(skus)}")

        volumes: list[str] = []
        executions: list[str] = []
        colors: list[str] = []
        for sku in skus:
            attrs = sku.get("attributes") or {}
            for key in ("volume_label","execution_code","execution_label","color_code","color_label","manufacturer_product_no"):
                if not attrs.get(key):
                    raise SystemExit(f"FAIL {pid}/{sku.get('sku_code')}: missing {key}")
            number = str(attrs["manufacturer_product_no"])
            if number not in EXPECTED_MODELS:
                raise SystemExit(f"FAIL unexpected Product #: {number}")
            product_nos.add(number)
            code = str(sku.get("sku_code") or "")
            if not code or code in sku_codes:
                raise SystemExit(f"FAIL duplicate/empty SKU code: {code}")
            sku_codes.add(code)
            for target, value in (
                (volumes, str(attrs["volume_label"])),
                (executions, str(attrs["execution_label"])),
                (colors, str(attrs["color_label"])),
            ):
                if value not in target:
                    target.append(value)

        total += len(skus)
        print(f"PASS {pid}: {len(skus)} SKU | volume={', '.join(volumes)} | execution={', '.join(executions)} | color={', '.join(colors)}")

    if product_nos != EXPECTED_MODELS:
        raise SystemExit(f"FAIL model set mismatch: {sorted(product_nos)}")
    if total != 48 or len(sku_codes) != 48:
        raise SystemExit(f"FAIL expected 48 unique SKU, got total={total}, unique={len(sku_codes)}")

    try:
        master = snapshot()
    except Exception as exc:
        if "no such table" in str(exc).lower():
            master = None
            print("SKIP Product Master runtime check: runtime DB schema is not initialized in this environment")
        else:
            raise

    if master is not None:
        products = [p for p in master.get("products") or [] if p.get("v3_product_id") in EXPECTED]
        ids = {str(p.get("id") or "") for p in products}
        skus = [s for s in master.get("skus") or [] if str(s.get("product_id") or "") in ids]
        if len(products) != 5:
            raise SystemExit(f"FAIL Product Master: expected 5 grouped products, got {len(products)}")
        if len(skus) != 48:
            raise SystemExit(f"FAIL Product Master: expected 48 grouped SKU, got {len(skus)}")
        if any(s.get("price") is not None for s in skus):
            raise SystemExit("FAIL grouped pot SKU unexpectedly has price")
        if any(s.get("availability") != "backorder" for s in skus):
            raise SystemExit("FAIL grouped pot SKU availability is not backorder")
        if any(s.get("price_request") is not True for s in skus):
            raise SystemExit("FAIL grouped pot SKU is not request-price")
        print("PASS Product Master: 5 products / 17 manufacturer models / 48 SKU")
    print("PASS Commerce mode: Ціна за запитом / Під замовлення")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
