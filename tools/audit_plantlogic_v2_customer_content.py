#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.plantlogic_v2_customer_content import (
    LIMITED_OFFICIAL_DATA,
    PUBLIC_CHARACTERISTIC_LABELS,
)

SPEC = ROOT / "data" / "product_content" / "plantlogic_v2_final_20260928.json"
SOURCE = ROOT / "v5" / "content" / "verified-current.json"

BANNED = [
    r"Дані та Product # звірені",
    r"Офіційна модель Plantlogic",
    r"Офіційне джерело",
    r"не специфікован",
    r"\bBag Bases\b",
    r"\bgrow bag\b",
    r"\bgrow bags\b",
    r"\bopen-top grow bags\b",
    r"https?://",
    r"характеристики звірені",
    r"не вигадуємо",
    r"поточна сторінка виробника",
    r"\btech sheet\b",
    r"офіційні матеріали",
    r"підтверджен",
    r"не публіку",
    r"публічній картці",
]
BAN_RE = re.compile("|".join(BANNED), re.I)

EXAMPLES = [
    "plantlogic-ground-cover-1600201",
    "plantlogic-pot-anchor",
    "plantlogic-culti-base",
    "plantlogic-vf-bag-base-12010300",
    "plantlogic-bag-base-drainage-1301036",
    "plantlogic-blueberry-round-25l-u-grooves-1308026",
    "plantlogic-25l-round-drainage-1304125",
    "plantlogic-4-7l-square-cold-storage-13050040",
    "plantlogic-18l-strawberry-trough-1305909",
    "plantlogic-kratos-slab-base-1301081",
]


def main() -> int:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    canonical = {x["canonical_product_id"]: x for x in spec["canonical_products"]}
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    before = {x["product_id"]: x for x in source.get("products") or []}

    with tempfile.TemporaryDirectory(prefix="bb610-pl-copy-") as td:
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
                SELECT product_id,short_description,description,application,composition,
                       benefits_json,how_it_works,characteristics_json
                FROM products
                WHERE lower(brand)='plantlogic'
                ORDER BY product_id
                """
            ).fetchall()
            assert len(rows) == 78, len(rows)
            seen = {row["product_id"] for row in rows}
            assert seen == set(canonical)
            empty_fields = {"composition": []}
            for row in rows:
                pid = row["product_id"]
                for field in ("short_description", "description", "application", "how_it_works"):
                    value = str(row[field] or "").strip()
                    assert value, (pid, field, "empty")
                    assert not BAN_RE.search(value), (pid, field, value)
                composition = str(row["composition"] or "").strip()
                if not composition:
                    empty_fields["composition"].append(pid)
                else:
                    assert not BAN_RE.search(composition), (pid, "composition", composition)
                benefits = json.loads(row["benefits_json"] or "[]")
                assert 3 <= len(benefits) <= 5, (pid, "benefits", len(benefits))
                for benefit in benefits:
                    text = (str(benefit.get("title") or "") + " " + str(benefit.get("text") or "")).strip()
                    assert text and not BAN_RE.search(text), (pid, "benefit", text)
                characteristics = json.loads(row["characteristics_json"] or "[]")
                assert characteristics, (pid, "characteristics empty")
                for item in characteristics:
                    label = str(item.get("label") or "").strip()
                    value = str(item.get("value") or "").strip()
                    assert label in PUBLIC_CHARACTERISTIC_LABELS, (pid, "bad label", label)
                    assert not label.startswith("__")
                    assert value and not BAN_RE.search(value), (pid, label, value)
                labels = {x["label"] for x in characteristics}
                assert "Виробник" in labels and "Артикул виробника" in labels, (pid, labels)

            sources = con.execute(
                """
                SELECT p.product_id, COUNT(ps.source_id) n
                FROM products p
                LEFT JOIN product_sources ps ON ps.product_id=p.product_id
                WHERE lower(p.brand)='plantlogic'
                GROUP BY p.product_id
                """
            ).fetchall()
            assert all(int(x["n"]) >= 1 for x in sources), "source metadata was lost"

            print("PLANTLOGIC CUSTOMER CONTENT: PASS")
            print("CANONICAL NORMALIZED: 78")
            print("LIMITED OFFICIAL DATA:", ", ".join(sorted(LIMITED_OFFICIAL_DATA)))
            print("EMPTY COMPOSITION:", len(empty_fields["composition"]))
            print("EMPTY COMPOSITION IDS:", ", ".join(empty_fields["composition"]))
            print("BANNED PUBLIC TEXT: 0")
            print("PUBLIC SOURCE URLS IN CUSTOMER FIELDS: 0")
            print("SOURCE METADATA PRESERVED: PASS")
            print("BEFORE / AFTER EXAMPLES:")
            by_id = {row["product_id"]: row for row in rows}
            for pid in EXAMPLES:
                old = before.get(pid) or {}
                new = by_id[pid]
                print(json.dumps({
                    "product_id": pid,
                    "before": {
                        "short_description": old.get("short_description") or "",
                        "application": old.get("application") or "",
                    },
                    "after": {
                        "short_description": new["short_description"],
                        "application": new["application"],
                    },
                }, ensure_ascii=False))
        finally:
            con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
