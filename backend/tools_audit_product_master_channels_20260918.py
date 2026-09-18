from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.product_master_runtime import SOURCE_ID, snapshot as master_snapshot
from backend.services.catalog_feeds import (
    channel_snapshot,
    google_csv_from_snapshot,
    meta_csv_from_snapshot,
)


def csv_rows(text: str) -> int:
    return len(list(csv.DictReader(io.StringIO(text.lstrip("\ufeff")))))


def main() -> int:
    master = master_snapshot()
    channel = channel_snapshot()

    products = master.get("products") or []
    skus = master.get("skus") or []
    commerce = master.get("commerce") or {}

    product_ids = {str(x.get("id") or "") for x in products if isinstance(x, dict)}
    sku_ids = [
        str(x.get("id") or x.get("sku") or "")
        for x in skus
        if isinstance(x, dict)
    ]
    bad_owner = [
        x for x in skus
        if isinstance(x, dict) and str(x.get("product_id") or "") not in product_ids
    ]
    duplicates = len(sku_ids) - len(set(sku_ids))

    google_count = csv_rows(google_csv_from_snapshot(channel))
    meta_count = csv_rows(meta_csv_from_snapshot(channel))
    counts = channel.get("counts") or {}
    eligible = int(counts.get("eligible") or 0)

    checks = {
        "source": master.get("source") == SOURCE_ID == channel.get("source"),
        "schema": master.get("schema_version") == "4.0",
        "sku_unique": duplicates == 0,
        "sku_owner": not bad_owner,
        "commerce_subset": set(commerce).issubset(set(sku_ids)),
        "channel_total": int(counts.get("total") or 0) == len(set(sku_ids)),
        "google_parity": google_count == eligible,
        "meta_parity": meta_count == eligible,
    }

    print("===== PRODUCT MASTER / CHANNELS AUDIT =====")
    print("SOURCE=" + str(master.get("source") or ""))
    print("SCHEMA=" + str(master.get("schema_version") or ""))
    print(f"PRODUCTS={len(products)}")
    print(f"SKUS={len(set(sku_ids))}")
    print(f"COMMERCE_ROWS={len(commerce)}")
    print(f"CHANNEL_TOTAL={counts.get('total',0)}")
    print(f"ELIGIBLE={eligible}")
    print(f"BLOCKED={counts.get('blocked',0)}")
    print(f"REVIEW_REQUIRED={counts.get('review_required',0)}")
    print(f"GOOGLE_ROWS={google_count}")
    print(f"META_ROWS={meta_count}")
    print("CHECKS=" + ("PASS" if all(checks.values()) else "FAIL"))
    if not all(checks.values()):
        print("FAILED=" + ",".join(k for k, ok in checks.items() if not ok))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
