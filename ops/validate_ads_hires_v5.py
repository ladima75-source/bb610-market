#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/tmp/bb610-v5.sqlite3")
    ap.add_argument("--manifest", default="ops/ads-hires-media-import.json")
    args = ap.parse_args()

    root = Path.cwd()
    manifest = json.loads((root / args.manifest).read_text(encoding="utf-8"))
    rows = manifest.get("media") or []
    if len(rows) != 36:
        raise SystemExit(f"Expected 36 Ads HiRes rows, got {len(rows)}")

    con = sqlite3.connect(args.db)
    failures = []
    verified = []

    for row in rows:
        sku_id = row["sku_id"]
        product_id = row["product_id"]
        expected_path = "/" + str(row["target"]).lstrip("/")
        expected_source = row["source_page"]

        bindings = con.execute(
            """
            SELECT m.media_id,m.path,m.verification_status,
                   sm.is_primary,sm.binding_kind,sm.source_kind,sm.source_url
            FROM sku_media sm
            JOIN media m ON m.media_id=sm.media_id
            WHERE sm.sku_id=?
            ORDER BY sm.is_primary DESC, sm.sort_order, m.media_id
            """,
            (sku_id,),
        ).fetchall()

        if len(bindings) != 1:
            failures.append(f"{sku_id}: expected exactly 1 SKU media binding, got {len(bindings)}")
            continue

        media_id,path,status,is_primary,binding_kind,source_kind,source_url = bindings[0]
        checks = {
            "path": path == expected_path,
            "verified": status == "verified",
            "primary": int(is_primary or 0) == 1,
            "binding_kind": binding_kind == "exact",
            "source_kind": source_kind == "verified_package_hires_original",
            "source_url": source_url == expected_source,
            "asset_exists": (root / expected_path.lstrip("/")).is_file(),
        }
        bad = [k for k,v in checks.items() if not v]
        if bad:
            failures.append(
                f"{sku_id}: failed {','.join(bad)}; "
                f"path={path!r} source_kind={source_kind!r} source_url={source_url!r}"
            )
            continue

        product_binding = con.execute(
            """
            SELECT 1
            FROM product_media pm
            JOIN media m ON m.media_id=pm.media_id
            WHERE pm.product_id=? AND m.media_id=? AND m.path=?
              AND pm.source_kind='exact_sku_rollup'
            """,
            (product_id, media_id, expected_path),
        ).fetchone()
        if not product_binding:
            failures.append(f"{sku_id}: missing exact_sku_rollup product binding")
            continue

        verified.append(
            {
                "product_id": product_id,
                "sku_id": sku_id,
                "path": expected_path,
                "media_id": media_id,
            }
        )

    if failures:
        print(json.dumps({"status":"FAIL","failures":failures}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(json.dumps({
        "status":"PASS",
        "verified_bindings":len(verified),
        "source_kind":"verified_package_hires_original",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
