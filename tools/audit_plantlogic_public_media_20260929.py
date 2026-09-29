#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="bb610-pl-media-") as td:
        db = Path(td) / "v5.sqlite3"
        subprocess.run(
            [sys.executable, str(ROOT / "v5" / "bootstrap_db.py"), "--out", str(db)],
            cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
        )
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            from backend.services.product_master_v5_migrations import apply_runtime_migrations
            apply_runtime_migrations(con)

            rows = con.execute(
                """
                SELECT p.product_id,p.name,p.category_id,
                       COUNT(DISTINCT pm.media_id) AS product_media,
                       COUNT(DISTINCT sm.media_id) AS sku_media,
                       SUM(CASE WHEN sm.is_primary=1 THEN 1 ELSE 0 END) AS primary_count
                FROM products p
                LEFT JOIN product_media pm ON pm.product_id=p.product_id
                LEFT JOIN skus s ON s.product_id=p.product_id AND s.enabled=1
                LEFT JOIN sku_media sm ON sm.sku_id=s.sku_id
                WHERE lower(p.brand)='plantlogic'
                  AND p.public_enabled=1 AND p.status='active'
                GROUP BY p.product_id,p.name,p.category_id
                ORDER BY p.product_id
                """
            ).fetchall()

            assert len(rows) == 67, len(rows)
            zero, one, two_plus, no_primary = [], [], [], []
            for row in rows:
                count = max(int(row["product_media"] or 0), int(row["sku_media"] or 0))
                item = (row["product_id"], row["name"], count)
                if count == 0:
                    zero.append(item)
                elif count == 1:
                    one.append(item)
                else:
                    two_plus.append(item)
                if int(row["primary_count"] or 0) == 0:
                    no_primary.append(item)

            print(f"PUBLIC PLANTLOGIC MEDIA: products={len(rows)} zero={len(zero)} one={len(one)} two_plus={len(two_plus)} no_primary={len(no_primary)}")
            print("ZERO_MEDIA")
            for pid,name,count in zero:
                print(f"{pid}\t{name}\t{count}")
            print("ONE_MEDIA")
            for pid,name,count in one:
                print(f"{pid}\t{name}\t{count}")
            print("NO_PRIMARY")
            for pid,name,count in no_primary:
                print(f"{pid}\t{name}\t{count}")
        finally:
            con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
