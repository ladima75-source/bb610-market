from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "v5/staging/production-current.json"
SCHEMA = ROOT / "v5/schema.sql"
BOOTSTRAP = ROOT / "v5/bootstrap_db.py"
DB_PATH = Path(os.getenv("BB610_V5_DB_PATH", str(ROOT / "backend/runtime/bb610-v5.sqlite3")))
_LOCK = threading.Lock()


def _needs_rebuild() -> bool:
    if not DB_PATH.is_file():
        return True
    db_mtime = DB_PATH.stat().st_mtime
    return any(path.is_file() and path.stat().st_mtime > db_mtime for path in (STAGE, SCHEMA, BOOTSTRAP))


def ensure_db() -> Path:
    if not _needs_rebuild():
        return DB_PATH
    with _LOCK:
        if not _needs_rebuild():
            return DB_PATH
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = DB_PATH.with_suffix(DB_PATH.suffix + ".tmp")
        if tmp.exists():
            tmp.unlink()
        subprocess.check_call(
            [
                sys.executable,
                str(BOOTSTRAP),
                "--stage",
                str(STAGE),
                "--schema",
                str(SCHEMA),
                "--out",
                str(tmp),
            ],
            cwd=str(ROOT),
        )
        os.replace(tmp, DB_PATH)
    return DB_PATH


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(ensure_db())
    con.row_factory = sqlite3.Row
    return con


def _json(value: str | None):
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def resolve_product_id(value: str) -> str | None:
    with _connect() as con:
        row = con.execute("SELECT product_id FROM products WHERE product_id=? OR slug=? LIMIT 1", (value, value)).fetchone()
        if row:
            return row["product_id"]
        row = con.execute(
            "SELECT product_id FROM product_aliases WHERE alias=? AND active=1 LIMIT 1",
            (value,),
        ).fetchone()
        return row["product_id"] if row else None


def resolve_sku_id(value: str) -> str | None:
    with _connect() as con:
        row = con.execute("SELECT sku_id FROM skus WHERE sku_id=? LIMIT 1", (value,)).fetchone()
        if row:
            return row["sku_id"]
        row = con.execute(
            "SELECT canonical_sku_id FROM sku_aliases WHERE alias_sku_id=? AND active=1 LIMIT 1",
            (value,),
        ).fetchone()
        return row["canonical_sku_id"] if row else None


def _media_for_sku(con: sqlite3.Connection, sku_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT m.media_id,m.path,m.kind,m.alt,m.verification_status,
               sm.is_primary,sm.sort_order
        FROM sku_media sm
        JOIN media m ON m.media_id=sm.media_id
        WHERE sm.sku_id=?
        ORDER BY sm.is_primary DESC, sm.sort_order ASC, m.media_id ASC
        """,
        (sku_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _sku_rows(con: sqlite3.Connection, product_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT s.sku_id,s.product_id,s.manufacturer_sku,
               s.package_value,s.package_unit,s.package_label,s.package_group,
               s.attributes_json,s.sort_order,s.enabled,
               c.price,c.sale_price,c.availability,c.stock_qty,
               c.enabled AS commerce_enabled,c.updated_at
        FROM skus s
        LEFT JOIN sku_commerce c ON c.sku_id=s.sku_id
        WHERE s.product_id=?
        ORDER BY s.sort_order ASC,s.sku_id ASC
        """,
        (product_id,),
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["attributes"] = _json(item.pop("attributes_json", None))
        item["media"] = _media_for_sku(con, item["sku_id"])
        result.append(item)
    return result


def product(product_id_or_alias: str) -> dict | None:
    canonical = resolve_product_id(product_id_or_alias)
    if not canonical:
        return None
    with _connect() as con:
        row = con.execute(
            """
            SELECT product_id,slug,name,brand,manufacturer,category_id,
                   short_description,description,application,composition,
                   characteristics_json,status,created_at,updated_at
            FROM products WHERE product_id=?
            """,
            (canonical,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["characteristics"] = _json(item.pop("characteristics_json", None))
        item["skus"] = _sku_rows(con, canonical)
        item["aliases"] = [
            r["alias"]
            for r in con.execute(
                "SELECT alias FROM product_aliases WHERE product_id=? AND active=1 ORDER BY alias",
                (canonical,),
            )
        ]
        return item


def snapshot() -> dict:
    with _connect() as con:
        products = [
            dict(row)
            for row in con.execute(
                """
                SELECT product_id,slug,name,brand,manufacturer,category_id,
                       short_description,description,application,composition,
                       characteristics_json,status,created_at,updated_at
                FROM products
                ORDER BY category_id,brand,name,product_id
                """
            )
        ]
        for item in products:
            item["characteristics"] = _json(item.pop("characteristics_json", None))
            item["skus"] = _sku_rows(con, item["product_id"])

        counts = {
            "products": con.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "skus": con.execute("SELECT COUNT(*) FROM skus").fetchone()[0],
            "sku_aliases": con.execute("SELECT COUNT(*) FROM sku_aliases").fetchone()[0],
            "media": con.execute("SELECT COUNT(*) FROM media").fetchone()[0],
            "request_price": con.execute(
                "SELECT COUNT(*) FROM sku_commerce WHERE availability='request_price'"
            ).fetchone()[0],
        }
        return {
            "schema_version": "5.0",
            "source": "bb610-product-master-v5",
            "counts": counts,
            "products": products,
        }
