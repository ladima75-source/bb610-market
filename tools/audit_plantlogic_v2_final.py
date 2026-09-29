#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPEC = ROOT / "data" / "product_content" / "plantlogic_v2_final_20260928.json"
MANIFEST = ROOT / "data" / "product_content" / "plantlogic_v2_media_manifest_20260928.json"
MEDIA_AUDIT = ROOT / "data" / "product_content" / "plantlogic_v2_media_audit_20260928.json"

PUBLIC_HIDDEN_PRODUCT_IDS = {
    "plantlogic-zephyr-v2-hose-clip-1700149",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_db(path: Path) -> sqlite3.Connection:
    subprocess.run(
        [
            sys.executable, str(ROOT / "v5" / "bootstrap_db.py"),
            "--stage", str(ROOT / "v5" / "staging" / "production-current.json"),
            "--content", str(ROOT / "v5" / "content" / "verified-current.json"),
            "--media", str(ROOT / "v5" / "media" / "verified-current.json"),
            "--schema", str(ROOT / "v5" / "schema.sql"),
            "--out", str(path),
        ],
        check=True, cwd=ROOT,
    )
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-media", action="store_true")
    args = ap.parse_args()

    spec = load(SPEC)
    expected = spec["expected"]
    canonical = spec["canonical_products"]
    canonical_ids = {x["canonical_product_id"] for x in canonical}
    wanted_sku_owner = {
        sku["sku_id"]: product["canonical_product_id"]
        for product in canonical for sku in product.get("skus") or []
    }
    wanted_skus = set(wanted_sku_owner)
    assert len(wanted_skus) == expected["total_sku"] == 133
    action_counts = {}
    for product in canonical:
        action = str(product.get("action") or "")
        action_counts[action] = action_counts.get(action, 0) + 1
    assert action_counts == expected["action_counts"] == {"KEEP": 31, "CREATE": 26, "SPLIT": 4, "RENAME": 17}
    assert expected["public_sections"] == ["blueberry", "rubus", "strawberry", "vegetable", "universal", "accessories"]

    hidden_numbers = set(expected.get("public_hidden") or [])
    hidden_product_ids = {
        product["canonical_product_id"]
        for product in canonical
        if any(str(number) in hidden_numbers for number in product.get("manufacturer_product_numbers") or [])
    }
    assert hidden_numbers == {"1700149", "1305008", "1302048"}
    assert hidden_product_ids == {
        "plantlogic-zephyr-v2-hose-clip-1700149",
        "plantlogic-vegetable-pot-8l-1305008",
        "plantlogic-nursery-tray-1302048",
    }
    public_canonical_ids = canonical_ids - hidden_product_ids
    public_wanted_skus = {
        sku["sku_id"]
        for product in canonical
        if product["canonical_product_id"] in public_canonical_ids
        for sku in product.get("skus") or []
    }

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "v5.sqlite3"
        con = build_db(db)
        try:
            baseline_skus = {
                row["sku_id"] for row in con.execute(
                    """SELECT s.sku_id FROM skus s
                       JOIN products p ON p.product_id=s.product_id
                       WHERE lower(p.brand)='plantlogic'"""
                )
            }
            baseline_commerce = {
                row["sku_id"]: tuple(row[k] for k in (
                    "price", "sale_price", "availability", "stock_qty", "enabled", "updated_at"
                ))
                for row in con.execute(
                    """SELECT c.* FROM sku_commerce c
                       JOIN skus s ON s.sku_id=c.sku_id
                       JOIN products p ON p.product_id=s.product_id
                       WHERE lower(p.brand)='plantlogic'"""
                )
            }

            from backend.services import product_master_v5_migrations
            previous = os.environ.get("BB610_SKIP_PLANTLOGIC_MANUAL_1_23")
            os.environ["BB610_SKIP_PLANTLOGIC_MANUAL_1_23"] = "1"
            try:
                product_master_v5_migrations.apply_runtime_migrations(con)
            finally:
                if previous is None:
                    os.environ.pop("BB610_SKIP_PLANTLOGIC_MANUAL_1_23", None)
                else:
                    os.environ["BB610_SKIP_PLANTLOGIC_MANUAL_1_23"] = previous

            actual_products = {
                row["product_id"]
                for row in con.execute("SELECT product_id FROM products WHERE lower(brand)='plantlogic'")
            }
            assert actual_products == canonical_ids, (
                "canonical product set mismatch",
                sorted(canonical_ids - actual_products),
                sorted(actual_products - canonical_ids),
            )
            assert len(actual_products) == expected["canonical_products"] == 78

            rows = con.execute(
                """SELECT s.sku_id,s.product_id,s.manufacturer_sku,s.attributes_json,
                          c.price,c.sale_price,c.availability,c.stock_qty,
                          c.enabled AS commerce_enabled,c.updated_at
                   FROM skus s
                   JOIN products p ON p.product_id=s.product_id
                   LEFT JOIN sku_commerce c ON c.sku_id=s.sku_id
                   WHERE lower(p.brand)='plantlogic'"""
            ).fetchall()
            assert len(rows) == len({row["sku_id"] for row in rows}), "duplicate active SKU"
            actual_skus = {row["sku_id"] for row in rows}
            assert actual_skus == wanted_skus, (
                "PlantLogic SKU set mismatch",
                sorted(wanted_skus - actual_skus),
                sorted(actual_skus - wanted_skus),
            )
            for row in rows:
                assert row["product_id"] == wanted_sku_owner[row["sku_id"]], (
                    "SKU belongs to wrong canonical product", row["sku_id"], row["product_id"]
                )

            new_skus = wanted_skus - baseline_skus
            assert len(new_skus) == expected["new_sku"] == 27
            row_by_sku = {row["sku_id"]: row for row in rows}
            for sid in new_skus:
                row = row_by_sku[sid]
                assert row["price"] is None and row["sale_price"] is None
                assert row["stock_qty"] is None
                assert row["availability"] == "request_price"
                assert row["commerce_enabled"] == 1

            for sid, before in baseline_commerce.items():
                if sid not in wanted_skus:
                    continue
                after = con.execute(
                    """SELECT price,sale_price,availability,stock_qty,enabled,updated_at
                       FROM sku_commerce WHERE sku_id=?""",
                    (sid,),
                ).fetchone()
                assert after is not None
                assert tuple(after) == before, ("existing commerce changed", sid, before, tuple(after))

            product_rows = con.execute(
                """SELECT product_id,name,category_id,manufacturer_title,
                          manufacturer_product_number,characteristics_json
                   FROM products WHERE lower(brand)='plantlogic'"""
            ).fetchall()
            titles = [row["name"] for row in product_rows]
            assert len(titles) == len(set(titles)), "duplicate canonical PlantLogic titles"

            category_counts = {}
            section_counts = {}
            allowed_sections = {"blueberry", "rubus", "strawberry", "vegetable", "universal", "accessories"}
            assert allowed_sections == set(expected["public_sections"])
            for row in product_rows:
                category = str(row["category_id"] or "")
                category_counts[category] = category_counts.get(category, 0) + 1
                assert str(row["manufacturer_title"] or "").strip(), ("manufacturer_title missing", row["product_id"])
                assert str(row["manufacturer_product_number"] or "").strip(), ("manufacturer Product # missing", row["product_id"])
                chars = json.loads(row["characteristics_json"] or "[]")
                section = next(
                    (str(x.get("value") or "") for x in chars if isinstance(x, dict) and x.get("label") == "__plantlogic_sections"),
                    "",
                )
                assert section in allowed_sections, ("bad PlantLogic section", row["product_id"], section)
                section_counts[section] = section_counts.get(section, 0) + 1
                if str(row["name"]).startswith("Горщик"):
                    assert row["category_id"] != "accessories", ("pot in Accessories", row["product_id"])
            assert category_counts == expected["technical_category_counts"] == {"containers": 44, "accessories": 28, "strawberry": 6}
            assert section_counts == expected["section_counts"] == {"blueberry": 28, "rubus": 14, "strawberry": 6, "vegetable": 6, "universal": 5, "accessories": 19}

            alias_rows = con.execute(
                """SELECT alias,product_id FROM product_aliases
                   WHERE alias_kind='manufacturer_product_number_v2' AND active=1"""
            ).fetchall()
            assert len(alias_rows) == expected["alias_reference"] == 15
            alias_map = {row["alias"]: row["product_id"] for row in alias_rows}
            assert len(alias_map) == 15
            for row in spec["aliases"]:
                alias = row["alias_manufacturer_product_number"]
                target = row["canonical_target"]
                assert alias_map.get(alias) == target
                assert target in canonical_ids
                assert target not in alias_map, ("alias->alias", alias, target)

            assert not con.execute(
                "SELECT 1 FROM products WHERE product_id IN (?,?)",
                ("plantlogic-micro-tube-stake", "plantlogic-rivus-2in1-slab-base"),
            ).fetchone()
            assert not con.execute(
                "SELECT 1 FROM skus WHERE sku_id='BB610-PLT-1308125-EA'"
            ).fetchone()
            legacy_sku_alias = con.execute(
                """SELECT canonical_sku_id FROM sku_aliases
                   WHERE alias_sku_id='BB610-PLT-1308125-EA' AND active=1"""
            ).fetchone()
            assert legacy_sku_alias and legacy_sku_alias["canonical_sku_id"] == "PL-BB-1308125-BK"

            to_verify = set()
            for row in rows:
                attrs = json.loads(row["attributes_json"] or "{}")
                if attrs.get("manufacturer_variant") == "TO_VERIFY":
                    to_verify.add(str(attrs.get("manufacturer_product_no") or ""))
            assert to_verify == set(expected["to_verify"]) == {"1205018", "1205019"}

            # Rivus split and the two distinct 40L U-groove products.
            for sid in ("PL-13020500", "PL-13020502"):
                assert row_by_sku[sid]["product_id"] == "plantlogic-rivus-slab-base"
            for sid in ("PL-13020510", "PL-13020512"):
                assert row_by_sku[sid]["product_id"] == "plantlogic-rivus-end-cap"
            title_by_id = {row["product_id"]: row["name"] for row in product_rows}
            assert "16 мм" in title_by_id["plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400"]
            assert "20 мм" in title_by_id["plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440"]
            assert title_by_id["plantlogic-4-7l-square-cold-storage-13050040"] == "Горщик для малини та ожини 4,7 л квадратний для технології long-cane"
            assert title_by_id["plantlogic-7l-square-cold-storage-1305071"] == "Горщик для малини та ожини 7 л квадратний для технології long-cane"

            os.environ["BB610_V5_DB_PATH"] = str(db)
            os.environ["BB610_DB_PATH"] = str(Path(td) / "no-live-commerce.sqlite3")
            from backend.services import product_master_v5, product_master_feed_v5
            hidden_internal = product_master_v5.product(
                "plantlogic-zephyr-v2-hose-clip-1700149", public_only=False
            )
            assert hidden_internal is not None
            assert hidden_internal["manufacturer_product_number"] == "1700149"
            assert any(x["sku_id"] == "PL-1700149" for x in hidden_internal["skus"])
            assert product_master_v5.product(
                "plantlogic-zephyr-v2-hose-clip-1700149", public_only=True
            ) is None
            assert product_master_v5.resolve_sku("PL-1700149") is None
            hidden_sku_internal = product_master_v5.resolve_sku(
                "PL-1700149", public_only=False
            )
            assert hidden_sku_internal is not None
            assert hidden_sku_internal["canonical_sku_id"] == "PL-1700149"
            assert product_master_v5.resolve_order_sku("PL-1700149") is None
            for pid, sid in (
                ("plantlogic-vegetable-pot-8l-1305008", "PL-1305008-BK"),
                ("plantlogic-nursery-tray-1302048", "PL-1302048"),
            ):
                assert product_master_v5.product(pid, public_only=False) is not None
                assert product_master_v5.product(pid, public_only=True) is None
                assert product_master_v5.resolve_sku(sid) is None
                assert product_master_v5.resolve_sku(sid, public_only=False) is not None
                assert product_master_v5.resolve_order_sku(sid) is None
            public_snapshot = product_master_v5.snapshot(public_only=True)
            assert not any(
                x.get("product_id") == "plantlogic-zephyr-v2-hose-clip-1700149"
                for x in public_snapshot.get("product_aliases") or []
            )
            assert not any(
                x.get("canonical_sku_id") == "PL-1700149"
                for x in public_snapshot.get("sku_aliases") or []
            )
            feed = product_master_feed_v5.snapshot()
            feed_products = {
                x["id"] for x in feed["products"]
                if str(x.get("brand") or "").lower() == "plantlogic"
            }
            feed_skus = {x["id"] for x in feed["skus"] if x["product_id"] in canonical_ids}
            assert feed_products == public_canonical_ids
            assert feed_skus == public_wanted_skus
            assert "plantlogic-zephyr-v2-hose-clip-1700149" not in feed_products
            assert "PL-1700149" not in feed_skus
            assert not any(x["id"] in alias_map for x in feed["products"])
            assert not any(x["id"] in alias_map for x in feed["skus"])

            if args.require_media:
                assert MANIFEST.is_file(), "PlantLogic V2 media manifest missing"
                assert MEDIA_AUDIT.is_file(), "PlantLogic V2 media audit missing"
                media_audit = load(MEDIA_AUDIT)
                by_id = {x["canonical_product_id"]: x for x in media_audit["products"]}
                assert set(by_id) == canonical_ids
                keys = {
                    "plantlogic-blueberry-zephyr-v2-25l-1301144",
                    "plantlogic-blueberry-zephyr-v2-30l-1301153",
                    "plantlogic-blueberry-zephyr-v2-40l-1301143",
                    "plantlogic-blueberry-round-30l-u-grooves-1308303",
                    "plantlogic-10l-drainage-1307110",
                    "plantlogic-4-7l-square-cold-storage-13050040",
                    "plantlogic-rivus-slab-base",
                    "plantlogic-rivus-end-cap",
                    "plantlogic-9l-strawberry-trough-truss-1305209",
                    "plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400",
                    "plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440",
                }
                for pid in keys:
                    assert by_id[pid]["gallery_count"] >= 1, ("key product has no media", pid)
                for item in load(MANIFEST).get("media") or []:
                    path = str(item.get("path") or "")
                    assert path.startswith("/assets/img/v5/media/"), ("external production media path", path)
                    assert (ROOT / path.lstrip("/")).is_file(), ("missing local media asset", path)

                feed_after = product_master_feed_v5.snapshot()
                feed_sku_by_id = {x["id"]: x for x in feed_after["skus"]}
                for pid in keys:
                    product = next(x for x in canonical if x["canonical_product_id"] == pid)
                    for sku in product["skus"]:
                        assert feed_sku_by_id[sku["sku_id"]]["image"], ("key feed SKU has no image", sku["sku_id"])

            print("PLANTLOGIC V2 FINAL AUDIT: PASS")
            print("CANONICAL PRODUCTS: 78")
            print("ALIAS/REFERENCE: 15")
            print("PLANTLOGIC SKU: 133")
            print("PUBLIC SECTIONS: 6")
            print("ACTIONS: KEEP 31 / CREATE 26 / SPLIT 4 / RENAME 17")
            print("NEW SKU: 27")
            print("TO_VERIFY: 1205018, 1205019")
            print("EXISTING COMMERCE UNCHANGED: PASS")
            print("CANONICAL FEED: PASS")
            if args.require_media:
                print("MEDIA MANIFEST/AUDIT: PASS")
            return 0
        finally:
            con.close()


if __name__ == "__main__":
    raise SystemExit(main())
