from __future__ import annotations

"""Apply Plantlogic blueberry pot architecture R2.

R2 keeps the R1 five-card architecture reversible, but splits the 25 L
short-legs round pot into its own storefront Product card.

R2:
- 6 storefront Product cards
- 17 manufacturer Product # models
- 48 storefront SKU
- customer selection: model -> color
- no price/stock/commerce writes

Rollback:
    python backend/rollback_plantlogic_blueberry_pots_to_5card_20260919.py --apply
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import backend.update_plantlogic_blueberry_pots_v3_20260919 as base

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_blueberry_pots_r2_20260919.json"
EXPECTED_PRODUCTS = 6


def plan() -> dict:
    previous_manifest = base.MANIFEST
    previous_expected = base.EXPECTED_PRODUCTS
    try:
        base.MANIFEST = MANIFEST
        base.EXPECTED_PRODUCTS = EXPECTED_PRODUCTS
        return base.plan()
    finally:
        base.MANIFEST = previous_manifest
        base.EXPECTED_PRODUCTS = previous_expected


def apply_architecture(work: dict) -> dict:
    previous_manifest = base.MANIFEST
    previous_expected = base.EXPECTED_PRODUCTS
    try:
        base.MANIFEST = MANIFEST
        base.EXPECTED_PRODUCTS = EXPECTED_PRODUCTS
        return base.apply_architecture(work)
    finally:
        base.MANIFEST = previous_manifest
        base.EXPECTED_PRODUCTS = previous_expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    work = plan()
    doc = work["doc"]
    products = doc.get("products") or []
    print("BB610 PLANTLOGIC BLUEBERRY POTS — ARCHITECTURE R2")
    print("PRODUCT CARDS:", len(products))
    print("MANUFACTURER MODELS:", sum(len(x.get("models") or []) for x in products))
    print("STOREFRONT SKU:", sum(len(x["sku_media"]["skus"]) for x in work["cards"]))
    print("SHORT LEGS CARD:", "prd_pl_bb_round_short_legs")
    print("SELECTION MODEL: model -> color")
    print("ROLLBACK: rollback_plantlogic_blueberry_pots_to_5card_20260919.py --apply")
    print("PRICE/STOCK/COMMERCE WRITES: NONE")

    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    result = apply_architecture(work)
    print("RESULT:", result["status"])
    print("CREATED:", result["created"])
    print("UPDATED:", result["updated"])
    print("PRODUCTS:", result["products"])
    print("SKU:", result["skus"])
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", result["report"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
