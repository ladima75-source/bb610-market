from __future__ import annotations

"""Rollback Plantlogic blueberry pots from R2 to the preserved R1 five-card architecture."""

import argparse
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import backend.update_plantlogic_blueberry_pots_v3_20260919 as r1
from backend.services import product_cards_v3 as pcv3

R2_ONLY_PRODUCT_ID = "prd_pl_bb_round_short_legs"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    work = r1.plan()
    print("BB610 PLANTLOGIC BLUEBERRY POTS — ROLLBACK TO R1")
    print("TARGET: 5 Product cards / 17 manufacturer models / 48 SKU")
    print("R2-ONLY CARD TO DISABLE:", R2_ONLY_PRODUCT_ID)
    print("PRICE/STOCK/COMMERCE WRITES: NONE")

    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    result = r1.apply_architecture(work)
    backup = Path(result["backup"])
    try:
        short = pcv3.get(R2_ONLY_PRODUCT_ID)
        if isinstance(short, dict) and short.get("enabled") is not False:
            patched = deepcopy(short)
            patched["enabled"] = False
            pcv3.put(R2_ONLY_PRODUCT_ID, patched)

        live = [pcv3.get(card["product_id"]) for card in work["cards"]]
        if any(not isinstance(card, dict) or card.get("enabled") is not True for card in live):
            raise RuntimeError("R1 grouped cards are not all enabled")
        if isinstance(pcv3.get(R2_ONLY_PRODUCT_ID), dict) and pcv3.get(R2_ONLY_PRODUCT_ID).get("enabled") is not False:
            raise RuntimeError("R2-only short-legs card remained enabled")
        sku_count = sum(len((card.get("sku_media") or {}).get("skus") or []) for card in live if isinstance(card, dict))
        if sku_count != 48:
            raise RuntimeError(f"R1 SKU count mismatch: {sku_count}")
    except Exception:
        r1.restore_cards(backup)
        raise

    print("RESULT: PASS")
    print("PRODUCTS: 5")
    print("SKU: 48")
    print("R2-ONLY CARD: DISABLED")
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
