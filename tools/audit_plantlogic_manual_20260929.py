#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.plantlogic_manual_audit_20260929 import (
    COOLING_PRODUCT_ID,
    COOLING_SKU_ID,
    REMOVE_PRODUCTS,
    REFERENCE_ONLY_PRODUCTS,
)


def chars(row: sqlite3.Row) -> dict[str, str]:
    try:
        data = json.loads(row["characteristics_json"] or "[]")
    except Exception:
        data = []
    return {
        str(x.get("label") or "").strip(): str(x.get("value") or "").strip()
        for x in data
        if isinstance(x, dict)
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="bb610-pl-manual-") as td:
        db = Path(td) / "v5.sqlite3"
        subprocess.run(
            [sys.executable, str(ROOT / "v5" / "bootstrap_db.py"), "--out", str(db)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )

        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            from backend.services.product_master_v5_migrations import apply_runtime_migrations
            apply_runtime_migrations(con)

            all_products = con.execute(
                "SELECT * FROM products WHERE lower(brand)='plantlogic' ORDER BY product_id"
            ).fetchall()
            public_products = con.execute(
                """
                SELECT * FROM products
                WHERE lower(brand)='plantlogic' AND public_enabled=1 AND status='active'
                ORDER BY product_id
                """
            ).fetchall()
            public_ids = {r["product_id"] for r in public_products}
            public_skus = con.execute(
                """
                SELECT s.sku_id
                FROM skus s
                JOIN products p ON p.product_id=s.product_id
                WHERE lower(p.brand)='plantlogic'
                  AND p.public_enabled=1 AND p.status='active' AND s.enabled=1
                """
            ).fetchall()

            assert len(all_products) == 79, len(all_products)
            assert len(public_products) == 68, len(public_products)
            assert len(public_skus) == 122, len(public_skus)

            hidden = set(REMOVE_PRODUCTS) | set(REFERENCE_ONLY_PRODUCTS)
            assert not (hidden & public_ids), sorted(hidden & public_ids)
            assert COOLING_PRODUCT_ID in public_ids

            # Cooling Skirt is a separate product with no invented Product #1310110.
            cooling = con.execute(
                "SELECT * FROM products WHERE product_id=?",
                (COOLING_PRODUCT_ID,),
            ).fetchone()
            assert cooling is not None
            assert cooling["manufacturer_product_number"] in (None, "")
            assert cooling["manufacturer_title"] == "Cooling Skirt"
            assert "1310110" not in (cooling["name"] or "")
            assert con.execute(
                "SELECT 1 FROM skus WHERE sku_id=? AND product_id=? AND enabled=1",
                (COOLING_SKU_ID, COOLING_PRODUCT_ID),
            ).fetchone()
            assert con.execute(
                "SELECT availability FROM sku_commerce WHERE sku_id=?",
                (COOLING_SKU_ID,),
            ).fetchone()[0] == "request_price"

            # Explicit REMOVE/LEGACY products remain only as archived backend evidence.
            for pid in hidden:
                row = con.execute(
                    "SELECT public_enabled,status FROM products WHERE product_id=?",
                    (pid,),
                ).fetchone()
                assert row is not None, pid
                assert row["public_enabled"] == 0 and row["status"] == "archived", (pid, dict(row))

            # Product compatibility aliases.
            prod_aliases = {
                r["alias"]: r["product_id"]
                for r in con.execute(
                    "SELECT alias,product_id FROM product_aliases WHERE active=1"
                ).fetchall()
            }
            assert prod_aliases["1309003"] == "plantlogic-25-round-1308125"
            assert prod_aliases["1205001"] == "plantlogic-hose-clip-12050010"
            assert prod_aliases["1205002"] == "plantlogic-hose-clip-12050010"

            # Retired SKU identities must be aliases, not live exact SKUs.
            sku_aliases = {
                r["alias_sku_id"]: r["canonical_sku_id"]
                for r in con.execute(
                    "SELECT alias_sku_id,canonical_sku_id FROM sku_aliases WHERE active=1"
                ).fetchall()
            }
            expected_aliases = {
                "PL-1309003-BK": "PL-BB-1308125-BK",
                "PL-1205001": "PL-12050010",
                "PL-1205002": "PL-12050010",
            }
            for alias, canonical in expected_aliases.items():
                assert sku_aliases.get(alias) == canonical, (alias, sku_aliases.get(alias))
                assert not con.execute("SELECT 1 FROM skus WHERE sku_id=?", (alias,)).fetchone(), alias

            # 40L square U-groove variants: correct article, groove and real-photo primary.
            for pid, article, groove in (
                ("plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400", "13090400", "Ø16 мм"),
                ("plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440", "13090440", "Ø20 мм"),
            ):
                p = con.execute("SELECT * FROM products WHERE product_id=?", (pid,)).fetchone()
                assert p and p["manufacturer_product_number"] == article
                assert chars(p).get("Діаметр U-пазів") == groove
                assert chars(p).get("Висота ніжок") == "30 мм"
                primary = con.execute(
                    """
                    SELECT m.path,m.source_url,m.alt
                    FROM sku_media sm
                    JOIN skus s ON s.sku_id=sm.sku_id
                    JOIN media m ON m.media_id=sm.media_id
                    WHERE s.product_id=? AND sm.is_primary=1
                    LIMIT 1
                    """,
                    (pid,),
                ).fetchone()
                assert primary is not None, pid
                blob = " ".join(str(primary[k] or "") for k in primary.keys()).lower()
                assert ".pdf" not in blob and "tech sheet" not in blob and "techsheet" not in blob, (pid, dict(primary))

            # Zephyr V2: exact sizes, no 25L reuse, and 40L size visual is primary.
            z30 = con.execute(
                "SELECT * FROM products WHERE product_id='plantlogic-blueberry-zephyr-v2-30l-1301153'"
            ).fetchone()
            z40 = con.execute(
                "SELECT * FROM products WHERE product_id='plantlogic-blueberry-zephyr-v2-40l-1301143'"
            ).fetchone()
            assert chars(z30).get("Розміри") == "A 420 мм · B Ø333 мм · C 397 мм · D 70 мм"
            assert chars(z40).get("Розміри") == "A 370 мм · B Ø427 мм · C 500 мм · D 70 мм"
            z40_primary = con.execute(
                """
                SELECT m.path FROM sku_media sm
                JOIN skus s ON s.sku_id=sm.sku_id
                JOIN media m ON m.media_id=sm.media_id
                WHERE s.product_id='plantlogic-blueberry-zephyr-v2-40l-1301143'
                  AND sm.is_primary=1
                """
            ).fetchall()
            assert [r["path"] for r in z40_primary] == ["/assets/img/v5/manual/plantlogic-1301143-zephyr-v2-40l.svg"]

            # 10L square manual correction: 30 mm, never 50 mm.
            p10 = con.execute(
                "SELECT * FROM products WHERE product_id='plantlogic-10l-square-1306010'"
            ).fetchone()
            assert "30 мм" in p10["name"]
            assert "50 мм" not in p10["name"]
            assert chars(p10).get("Висота ніжок") == "30 мм"

            # Request-price / correct product classification.
            assert con.execute(
                """
                SELECT c.availability
                FROM sku_commerce c JOIN skus s ON s.sku_id=c.sku_id
                WHERE s.product_id='plantlogic-cold-storage-bin-1702000'
                LIMIT 1
                """
            ).fetchone()[0] == "request_price"
            assert con.execute(
                "SELECT category_id FROM products WHERE product_id='plantlogic-kratos-rivus-grow-bag-8l-1500010'"
            ).fetchone()[0] == "containers"

            # Nursery Tray exact specs.
            nursery = con.execute(
                "SELECT * FROM products WHERE product_id='plantlogic-nursery-tray-1302048'"
            ).fetchone()
            nc = chars(nursery)
            assert nc.get("Кількість комірок") == "72"
            assert nc.get("Об'єм") == "48 мл/комірка"
            assert nc.get("Розміри") == "545 × 280 × 70 мм"

            # Exact/current hose clip.
            clip = con.execute(
                "SELECT * FROM products WHERE product_id='plantlogic-zephyr-v2-hose-clip-1700149'"
            ).fetchone()
            clip_primary = con.execute(
                """
                SELECT m.path FROM sku_media sm
                JOIN skus s ON s.sku_id=sm.sku_id
                JOIN media m ON m.media_id=sm.media_id
                WHERE s.product_id=? AND sm.is_primary=1
                """,
                ("plantlogic-zephyr-v2-hose-clip-1700149",),
            ).fetchall()
            assert clip and clip["manufacturer_product_number"] == "1700149"
            assert [r["path"] for r in clip_primary] == ["/assets/img/v5/manual/plantlogic-1700149-hose-clip.jpg"]

            # 12010320 and 1302809 must retain exact identity and dimensions.
            vf = con.execute(
                "SELECT * FROM products WHERE product_id='plantlogic-vf-bag-base-hose-fix-12010320'"
            ).fetchone()
            assert vf["manufacturer_product_number"] == "12010320"
            assert "360 × 360" in chars(vf).get("Розміри", "")
            slab = con.execute(
                "SELECT * FROM products WHERE product_id='plantlogic-slab-base-bags-slabs-1302809'"
            ).fetchone()
            assert slab["manufacturer_product_number"] == "1302809"
            assert chars(slab).get("Розміри") == "210 × 1000 мм"

            # Six public sections remain; customer-facing audit language stays hidden.
            sections = set()
            banned = (
                "Дані та Product # звірені",
                "Офіційна модель Plantlogic",
                "Офіційне джерело",
                "не специфікован",
                "Bag Bases",
                "grow bag",
                "open-top grow bags",
            )
            for p in public_products:
                pc = chars(p)
                section = pc.get("__plantlogic_sections")
                if section:
                    sections.update(x.strip() for x in section.split("|") if x.strip())
                public_chars = [
                    {"label": k, "value": v}
                    for k, v in pc.items()
                    if not k.startswith("__")
                ]
                text_blob = " ".join(
                    str(p[k] or "")
                    for k in ("short_description","description","application","composition","how_it_works")
                )
                text_blob += " " + str(p["benefits_json"] or "")
                text_blob += " " + json.dumps(public_chars, ensure_ascii=False)
                assert not any(term.lower() in text_blob.lower() for term in banned), (p["product_id"], text_blob)

            assert sections == {"blueberry","rubus","strawberry","vegetable","universal","accessories"}, sections

            print("PLANTLOGIC MANUAL AUDIT 1-23: PASS")
            print("PUBLIC PRODUCTS: 68")
            print("PUBLIC SKU: 122")
            print("BACKEND PRODUCTS: 79")
            print("REMOVED/REFERENCE: 11")
            print("SKU REPLACEMENT ALIASES: 3")
        finally:
            con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
