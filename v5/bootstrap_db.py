#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_id(product_id: str, source: dict, index: int) -> str:
    raw = "|".join([
        product_id,
        str(source.get("source_type") or ""),
        str(source.get("url") or ""),
        str(source.get("provenance") or ""),
        str(index),
    ])
    return "src_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="v5/staging/production-current.json")
    ap.add_argument("--content", default="v5/content/verified-current.json")
    ap.add_argument("--schema", default="v5/schema.sql")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    stage_path = Path(args.stage)
    content_path = Path(args.content)
    schema_path = Path(args.schema)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    stage = load(stage_path)
    verified = load(content_path)
    now = stage.get("summary", {}).get("snapshot_created_at") or datetime.now(timezone.utc).isoformat()

    stage_products = list(stage.get("products") or []) + list(stage.get("plantlogic_products") or [])
    stage_product_ids = {row["product_id"] for row in stage_products}
    content_map = {row["product_id"]: row for row in verified.get("products") or []}

    if set(content_map) != stage_product_ids:
        missing = sorted(stage_product_ids - set(content_map))
        extra = sorted(set(content_map) - stage_product_ids)
        raise SystemExit(f"Verified content coverage mismatch: missing={missing}, extra={extra}")

    con = sqlite3.connect(out)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(schema_path.read_text(encoding="utf-8"))

        for stage_row in stage_products:
            row = content_map[stage_row["product_id"]]
            con.execute(
                """
                INSERT INTO products (
                    product_id, slug, name, brand, manufacturer, category_id,
                    short_description, description, application, composition,
                    benefits_json, how_it_works, characteristics_json,
                    seo_title, seo_description,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
                """,
                (
                    stage_row["product_id"],
                    stage_row["slug"],
                    row.get("name") or stage_row["name"],
                    row.get("brand") or stage_row.get("brand"),
                    row.get("manufacturer"),
                    row.get("category_id") or stage_row.get("category_id") or "other",
                    row.get("short_description"),
                    row.get("description"),
                    row.get("application"),
                    row.get("composition"),
                    json.dumps(row.get("benefits") or [], ensure_ascii=False, separators=(",", ":")),
                    row.get("how_it_works"),
                    json.dumps(row.get("characteristics") or [], ensure_ascii=False, separators=(",", ":")),
                    row.get("seo_title"),
                    row.get("seo_description"),
                    now,
                    now,
                ),
            )

            sources = row.get("sources") or []
            for index, source in enumerate(sources):
                sid = source_id(stage_row["product_id"], source, index)
                con.execute(
                    """
                    INSERT INTO product_sources(
                        source_id, product_id, source_type, source_url,
                        source_label, verified_at, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sid,
                        stage_row["product_id"],
                        source.get("source_type") or "verified_reference",
                        source.get("url"),
                        source.get("label"),
                        source.get("verified_at"),
                        source.get("status") or "verified",
                        source.get("provenance"),
                    ),
                )

            con.execute(
                """
                INSERT INTO migration_evidence(
                    entity_type, entity_id, field_name, source_kind,
                    source_ref, decision, note
                ) VALUES ('product', ?, 'content', ?, ?, 'accepted', ?)
                """,
                (
                    stage_row["product_id"],
                    row.get("content_status") or "verified_source_content",
                    sources[0].get("url") if sources else None,
                    f"V5 content imported from {len(sources)} recorded source(s).",
                ),
            )

        for row in stage.get("product_aliases") or []:
            con.execute(
                """
                INSERT OR IGNORE INTO product_aliases(alias, product_id, alias_kind, active)
                VALUES (?, ?, ?, 1)
                """,
                (row["alias"], row["product_id"], row.get("kind") or "legacy"),
            )

        all_skus = []
        for row in stage.get("skus") or []:
            item = dict(row)
            item["commerce_state"] = "live"
            all_skus.append(item)
        for row in stage.get("plantlogic_skus") or []:
            item = dict(row)
            item.setdefault("price", None)
            item.setdefault("sale_price", None)
            item.setdefault("availability", "request_price")
            item.setdefault("stock_qty", None)
            item["commerce_state"] = row.get("commerce_state") or "request_price"
            all_skus.append(item)

        media_by_path = {}
        for index, row in enumerate(all_skus):
            attrs = dict(row.get("attributes") or {})
            if row.get("v3_sku_id"):
                attrs["legacy_v3_sku_id"] = row["v3_sku_id"]

            con.execute(
                """
                INSERT INTO skus (
                    sku_id, product_id, manufacturer_sku,
                    package_value, package_unit, package_label, package_group,
                    attributes_json, sort_order, enabled
                ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["sku_id"],
                    row["product_id"],
                    row.get("package_value"),
                    row.get("package_unit"),
                    row.get("package_label"),
                    row.get("package_group"),
                    json.dumps(attrs, ensure_ascii=False, separators=(",", ":")),
                    index,
                    1 if row.get("enabled", True) else 0,
                ),
            )

            commerce_state = row.get("commerce_state")
            if commerce_state == "request_price":
                enabled = 1 if row.get("enabled", True) else 0
                con.execute(
                    """
                    INSERT INTO sku_commerce(
                        sku_id, price, sale_price, availability, stock_qty, enabled, updated_at
                    ) VALUES (?, NULL, NULL, 'request_price', NULL, ?, ?)
                    """,
                    (row["sku_id"], enabled, now),
                )
            elif commerce_state == "legacy_disabled":
                con.execute(
                    """
                    INSERT INTO sku_commerce(
                        sku_id, price, sale_price, availability, stock_qty, enabled, updated_at
                    ) VALUES (?, NULL, NULL, 'legacy_disabled', NULL, 0, ?)
                    """,
                    (row["sku_id"], now),
                )
            else:
                con.execute(
                    """
                    INSERT INTO sku_commerce(
                        sku_id, price, sale_price, availability, stock_qty, enabled, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["sku_id"],
                        row.get("price"),
                        row.get("sale_price"),
                        row.get("availability"),
                        row.get("stock_qty"),
                        1 if row.get("enabled") == 1 else 0,
                        row.get("updated_at") or now,
                    ),
                )

            for sort_order, media in enumerate(row.get("media") or []):
                media_id = media.get("media_id")
                path = media.get("path")
                if not media_id or not path:
                    continue

                canonical_media_id = media_by_path.get(path)
                if canonical_media_id is None:
                    canonical_media_id = media_id
                    con.execute(
                        """
                        INSERT INTO media(
                            media_id, path, sha256, kind, source_url,
                            verification_status, alt, created_at
                        ) VALUES (?, ?, NULL, ?, NULL, 'candidate', ?, ?)
                        """,
                        (
                            canonical_media_id,
                            path,
                            media.get("kind") or "image",
                            media.get("alt"),
                            now,
                        ),
                    )
                    media_by_path[path] = canonical_media_id

                con.execute(
                    """
                    INSERT OR IGNORE INTO sku_media(sku_id, media_id, is_primary, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        row["sku_id"],
                        canonical_media_id,
                        1 if media.get("is_primary") else 0,
                        sort_order,
                    ),
                )

        for row in stage.get("sku_aliases") or []:
            con.execute(
                """
                INSERT INTO sku_aliases(alias_sku_id, canonical_sku_id, alias_kind, active)
                VALUES (?, ?, 'legacy_duplicate', 1)
                """,
                (row["alias_sku_id"], row["canonical_sku_id"]),
            )

        for row in stage.get("price_conflicts") or []:
            con.execute(
                """
                INSERT INTO migration_evidence(
                    entity_type, entity_id, field_name, source_kind,
                    source_ref, decision, note
                ) VALUES ('sku', ?, 'price', 'production_conflict', ?, 'accepted', ?)
                """,
                (
                    row["selected_canonical_sku"],
                    row["product_id"],
                    "Canonical SKU selected by exact current binding / commerce precedence; legacy value remains recorded in staging evidence.",
                ),
            )

        con.commit()

        fk = list(con.execute("PRAGMA foreign_key_check"))
        if fk:
            raise SystemExit(f"Foreign key violations: {fk[:10]}")

        summary = {
            "products": con.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "content_products": con.execute(
                "SELECT COUNT(*) FROM migration_evidence WHERE entity_type='product' AND field_name='content' AND decision='accepted'"
            ).fetchone()[0],
            "product_sources": con.execute("SELECT COUNT(*) FROM product_sources").fetchone()[0],
            "skus": con.execute("SELECT COUNT(*) FROM skus").fetchone()[0],
            "sku_aliases": con.execute("SELECT COUNT(*) FROM sku_aliases").fetchone()[0],
            "media": con.execute("SELECT COUNT(*) FROM media").fetchone()[0],
            "sku_media": con.execute("SELECT COUNT(*) FROM sku_media").fetchone()[0],
            "commerce": con.execute("SELECT COUNT(*) FROM sku_commerce").fetchone()[0],
            "request_price": con.execute(
                "SELECT COUNT(*) FROM sku_commerce WHERE availability='request_price'"
            ).fetchone()[0],
            "legacy_disabled": con.execute(
                "SELECT COUNT(*) FROM sku_commerce WHERE availability='legacy_disabled'"
            ).fetchone()[0],
            "active_priced": con.execute(
                "SELECT COUNT(*) FROM sku_commerce WHERE enabled=1 AND price IS NOT NULL"
            ).fetchone()[0],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        con.close()


if __name__ == "__main__":
    main()
