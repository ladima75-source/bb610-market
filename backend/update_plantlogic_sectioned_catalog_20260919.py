from __future__ import annotations

"""Switch Plantlogic storefront back to individual model cards and sectioned catalog navigation.

- enables the 34 managed Plantlogic model cards / 37 SKU from the verified master;
- disables the temporary 6 grouped Blueberry cards;
- never changes prices, stock, availability, sku_commerce or commerce_map;
- keeps Product Card v3 media/content intact.
"""

import argparse
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import update_plantlogic_pots_v3_20260918 as master
from backend.services import product_cards_v3 as pcv3
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
GROUPED_IDS = {
    "prd_pl_bb_round",
    "prd_pl_bb_round_short_legs",
    "prd_pl_bb_square",
    "prd_pl_bb_round_u",
    "prd_pl_bb_square_u",
    "prd_pl_bb_zephyr_v2",
}
EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    doc = master.load_manifest()
    specs = doc.get("products") or []
    if len(specs) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} managed products")
    if sum(len(x.get("skus") or []) for x in specs) != EXPECTED_SKUS:
        raise RuntimeError(f"expected {EXPECTED_SKUS} managed SKU")

    managed_ids = [str(x["product_id"]) for x in specs]
    missing = [pid for pid in managed_ids if not isinstance(pcv3.get(pid), dict)]
    if missing:
        raise RuntimeError("missing individual Plantlogic cards: " + ", ".join(missing))

    enable = [pid for pid in managed_ids if pcv3.get(pid).get("enabled") is not True]
    disable = [pid for pid in GROUPED_IDS if isinstance(pcv3.get(pid), dict) and pcv3.get(pid).get("enabled") is not False]

    print("PLANTLOGIC SECTIONED CATALOG MIGRATION")
    print("INDIVIDUAL MODEL CARDS:", EXPECTED_PRODUCTS)
    print("SKU:", EXPECTED_SKUS)
    print("TO ENABLE:", len(enable))
    print("GROUPED CARDS TO DISABLE:", len(disable))
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        print("RESULT: PASS (PLAN ONLY)")
        return 0

    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    backup = BACKUP_ROOT / f"plantlogic-sectioned-catalog-{stamp()}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pcv3.BASE, backup / "product_cards_v3")

    try:
        for pid in managed_ids:
            card = deepcopy(pcv3.get(pid))
            card["enabled"] = True
            pcv3.put(pid, card)

        for pid in GROUPED_IDS:
            card = pcv3.get(pid)
            if not isinstance(card, dict):
                continue
            patched = deepcopy(card)
            patched["enabled"] = False
            pcv3.put(pid, patched)

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce database changed")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed")

        if any(pcv3.get(pid).get("enabled") is not True for pid in managed_ids):
            raise RuntimeError("not all individual Plantlogic cards were enabled")
        if any(isinstance(pcv3.get(pid), dict) and pcv3.get(pid).get("enabled") is not False for pid in GROUPED_IDS):
            raise RuntimeError("a grouped Blueberry card remained enabled")

        print("RESULT: PASS")
        print("ENABLED INDIVIDUAL CARDS:", EXPECTED_PRODUCTS)
        print("DISABLED GROUPED CARDS:", len(disable))
        print("COMMERCE/PRICES UNCHANGED: PASS")
        print("BACKUP:", backup)
        return 0
    except Exception:
        if pcv3.BASE.exists():
            shutil.rmtree(pcv3.BASE)
        shutil.copytree(backup / "product_cards_v3", pcv3.BASE)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
