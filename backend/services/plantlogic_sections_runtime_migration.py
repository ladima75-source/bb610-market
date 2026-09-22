from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATION_ID = "20260922_plantlogic_application_sections_v5"
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "backend/runtime/bb610-v5.sqlite3"
STAGE_PATH = ROOT / "v5/staging/production-current.json"
CONTENT_PATH = ROOT / "v5/content/verified-current.json"
MEDIA_PATH = ROOT / "v5/media/verified-current.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _source_id(product_id: str, source: dict, index: int) -> str:
    raw = "|".join([
        product_id,
        str(source.get("source_type") or ""),
        str(source.get("url") or ""),
        str(source.get("provenance") or ""),
        str(index),
    ])
    return "src_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def apply() -> bool:
    if not all(path.is_file() for path in (DB_PATH, STAGE_PATH, CONTENT_PATH, MEDIA_PATH)):
        return False

    stage = _load(STAGE_PATH)
    content = _load(CONTENT_PATH)
    media_doc = _load(MEDIA_PATH)

    plant_products = list(stage.get("plantlogic_products") or [])
    if int((stage.get("summary") or {}).get("plantlogic_sectioned_products") or 0) < 1:
        return False

    product_ids = {row["product_id"] for row in plant_products}
    plant_skus = list(stage.get("plantlogic_skus") or [])
    sku_ids = {row["sku_id"] for row in plant_skus if row.get("product_id") in product_ids}
    content_map = {
        row["product_id"]: row
        for row in (content.get("products") or [])
        if row.get("product_id") in product_ids
    }
    media_map = {row["media_id"]: row for row in (media_doc.get("media") or [])}
    now = _now()

    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_migrations (
              migration_id TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL
            )
            """
        )
        if con.execute(
            "SELECT 1 FROM runtime_migrations WHERE migration_id=?",
            (MIGRATION_ID,),
        ).fetchone():
            return False

        with con:
            existing_products = {
                row["product_id"]
                for row in con.execute(
                    "SELECT product_id FROM products WHERE product_id IN (%s)"
                    % ",".join("?" for _ in product_ids),
                    tuple(sorted(product_ids)),
                ).fetchall()
            }

            for stage_row in plant_products:
                product_id = stage_row["product_id"]
                row = content_map.get(product_id)
                if not row:
                    raise RuntimeError(f"Missing verified Plantlogic content for {product_id}")
                characteristics_json = json.dumps(row.get("characteristics") or [], ensure_ascii=False, separators=(",", ":"))

                if product_id in existing_products:
                    # Existing grouped blueberry cards keep all live/admin content;
                    # only the explicit application-section marker is refreshed.
                    con.execute(
                        "UPDATE products SET characteristics_json=?, updated_at=? WHERE product_id=?",
                        (characteristics_json, now, product_id),
                    )
                else:
                    con.execute(
                        """
                        INSERT INTO products(
                          product_id,slug,name,brand,manufacturer,category_id,
                          short_description,description,application,composition,
                          benefits_json,how_it_works,characteristics_json,
                          seo_title,seo_description,public_enabled,status,created_at,updated_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'active',?,?)
                        """,
                        (
                            product_id,
                            stage_row.get("slug") or product_id,
                            row.get("name") or stage_row.get("name") or product_id,
                            row.get("brand") or stage_row.get("brand"),
                            row.get("manufacturer"),
                            row.get("category_id") or stage_row.get("category_id") or "containers",
                            row.get("short_description"),
                            row.get("description"),
                            row.get("application"),
                            row.get("composition"),
                            json.dumps(row.get("benefits") or [], ensure_ascii=False, separators=(",", ":")),
                            row.get("how_it_works"),
                            characteristics_json,
                            row.get("seo_title"),
                            row.get("seo_description"),
                            1 if row.get("public_enabled", True) else 0,
                            now,
                            now,
                        ),
                    )
                    for index, source in enumerate(row.get("sources") or []):
                        con.execute(
                            """
                            INSERT OR IGNORE INTO product_sources(
                              source_id,product_id,source_type,source_url,source_label,
                              verified_at,status,notes
                            ) VALUES(?,?,?,?,?,?,?,?)
                            """,
                            (
                                _source_id(product_id, source, index),
                                product_id,
                                source.get("source_type") or "verified_reference",
                                source.get("url"),
                                source.get("label"),
                                source.get("verified_at"),
                                source.get("status") or "verified",
                                source.get("provenance"),
                            ),
                        )

            existing_skus = {row["sku_id"] for row in con.execute("SELECT sku_id FROM skus").fetchall()}
            for index, row in enumerate(plant_skus):
                if row.get("product_id") not in product_ids or row["sku_id"] in existing_skus:
                    continue
                attrs = dict(row.get("attributes") or {})
                if row.get("v3_sku_id"):
                    attrs["legacy_v3_sku_id"] = row["v3_sku_id"]
                con.execute(
                    """
                    INSERT INTO skus(
                      sku_id,product_id,manufacturer_sku,package_value,package_unit,
                      package_label,package_group,attributes_json,sort_order,enabled
                    ) VALUES(?,?,NULL,?,?,?,?,?,?,?)
                    """,
                    (
                        row["sku_id"], row["product_id"], row.get("package_value"),
                        row.get("package_unit"), row.get("package_label"), row.get("package_group"),
                        json.dumps(attrs, ensure_ascii=False, separators=(",", ":")),
                        10000 + index, 1 if row.get("enabled", True) else 0,
                    ),
                )
                con.execute(
                    """
                    INSERT INTO sku_commerce(
                      sku_id,price,sale_price,availability,stock_qty,enabled,updated_at
                    ) VALUES(?,NULL,NULL,'request_price',NULL,?,?)
                    """,
                    (row["sku_id"], 1 if row.get("enabled", True) else 0, now),
                )

            required_media_ids = {
                b["media_id"]
                for b in (media_doc.get("product_bindings") or [])
                if b.get("product_id") in product_ids
            } | {
                b["media_id"]
                for b in (media_doc.get("sku_bindings") or [])
                if b.get("sku_id") in sku_ids
            }
            for media_id in required_media_ids:
                row = media_map.get(media_id)
                if not row:
                    raise RuntimeError(f"Missing media record {media_id}")
                con.execute(
                    """
                    INSERT OR IGNORE INTO media(
                      media_id,path,sha256,kind,source_url,verification_status,alt,created_at
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        media_id, row["path"], row.get("sha256"), row.get("kind") or "image",
                        row.get("source_url"),
                        row.get("verification_status") if row.get("verification_status") in {"candidate","verified","rejected"} else "candidate",
                        row.get("alt"), now,
                    ),
                )

            for b in media_doc.get("product_bindings") or []:
                if b.get("product_id") not in product_ids:
                    continue
                con.execute(
                    """
                    INSERT OR IGNORE INTO product_media(
                      product_id,media_id,sort_order,source_kind,source_url
                    ) VALUES(?,?,?,?,?)
                    """,
                    (b["product_id"], b["media_id"], int(b.get("sort_order") or 0), b.get("source_kind"), b.get("source_url")),
                )

            for b in media_doc.get("sku_bindings") or []:
                if b.get("sku_id") not in sku_ids:
                    continue
                # Preserve an existing primary if the live DB already has one.
                is_primary = 1 if b.get("is_primary") else 0
                if is_primary and con.execute(
                    "SELECT 1 FROM sku_media WHERE sku_id=? AND is_primary=1",
                    (b["sku_id"],),
                ).fetchone():
                    is_primary = 0
                con.execute(
                    """
                    INSERT OR IGNORE INTO sku_media(
                      sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
                    ) VALUES(?,?,?,?, 'exact',?,?)
                    """,
                    (b["sku_id"], b["media_id"], is_primary, int(b.get("sort_order") or 0), b.get("source_kind"), b.get("source_url")),
                )

            con.execute(
                "INSERT INTO runtime_migrations(migration_id,applied_at) VALUES(?,?)",
                (MIGRATION_ID, now),
            )

        # Hard post-conditions: all sectioned products and SKUs must exist.
        db_products = con.execute(
            "SELECT COUNT(*) FROM products WHERE category_id='containers'"
        ).fetchone()[0]
        missing_products = [pid for pid in product_ids if not con.execute("SELECT 1 FROM products WHERE product_id=?", (pid,)).fetchone()]
        missing_skus = [sid for sid in sku_ids if not con.execute("SELECT 1 FROM skus WHERE sku_id=?", (sid,)).fetchone()]
        if missing_products or missing_skus:
            raise RuntimeError(f"Plantlogic migration incomplete: products={missing_products} skus={missing_skus}")
        print(f"PLANTLOGIC_RUNTIME_MIGRATION PASS products={len(product_ids)} skus={len(sku_ids)} container_products={db_products}")
        return True
    finally:
        con.close()
