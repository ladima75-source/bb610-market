from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path

from . import product_master_v5_migrations

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "v5/staging/production-current.json"
CONTENT = ROOT / "v5/content/verified-current.json"
MEDIA = ROOT / "v5/media/verified-current.json"
SCHEMA = ROOT / "v5/schema.sql"
BOOTSTRAP = ROOT / "v5/bootstrap_db.py"
DB_PATH = Path(os.getenv("BB610_V5_DB_PATH", str(ROOT / "backend/runtime/bb610-v5.sqlite3")))
LIVE_DB_PATH = Path(os.getenv("BB610_DB_PATH", str(ROOT / "backend/runtime/bb610-orders.sqlite3")))
_LOCK = threading.Lock()
_INVARIANT_LOCK = threading.Lock()
_PACKAGE_GROUP_INVARIANT_DONE = False
_MIGRATION_LOCK = threading.Lock()
_RUNTIME_MIGRATIONS_DONE = False

_CANONICAL_NONPOT_TITLES = {
    "actiwave": "Actiwave — кореневий біостимулятор Valagro",
    "actiwin-20-5-10": "Actiwin 20-5-10 — гранульоване NPK-добриво Valagro",
    "agriflex-amino-aminokysloty-50": "Agriflex Amino (Амінокислоти 50%) — амінокислотний біостимулятор CityMax",
    "agriflex-aminovix": "Agriflex AminoVix — амінокислотний біостимулятор CityMax",
    "agriflex-bio": "Agriflex Bio — фульвокислотний біостимулятор CityMax",
    "agriflex-fulvix-fulvokysloty-60": "Agriflex Fulvix (Фульвокислоти 50%) — фульвокислотний біостимулятор CityMax",
    "agriflex-humic-humat-kaliyu": "Agriflex Humic (Гумат калію) — гуміновий біостимулятор CityMax",
    "agriflex-zn": "Agriflex Zn — цинкове мікродобриво CityMax",
    "agroblen-granula-max-14-20-5-te-56m": "Agroblen Granula-MAX 14-20-5+TE (5–6M) — добриво контрольованого вивільнення ICL",
    "aktara-25-wg": "Актара 25 WG — системний інсектицид Syngenta",
    "benefit-pz": "Benefit PZ — біостимулятор Valagro",
    "blackjak": "BlackJak — гуміновий біостимулятор Sofbey",
    "boroplus": "Boroplus — борне мікродобриво Valagro",
    "brexil-ca": "Brexil Ca — хелатне мікродобриво з кальцієм Valagro",
    "brexil-combi": "Brexil Combi — комплексне хелатне мікродобриво Valagro",
    "brexil-duo": "Brexil Duo — кальцієво-магнієве мікродобриво Valagro",
    "brexil-fe": "Brexil Fe — хелатне мікродобриво із залізом Valagro",
    "brexil-mix": "Brexil Mix — комплексне хелатне мікродобриво Valagro",
    "brexil-mn": "Brexil Mn — хелатне мікродобриво з марганцем Valagro",
    "brexil-multi": "Brexil Multi — комплексне хелатне мікродобриво Valagro",
    "brexil-nutre": "Brexil Nutre — комплексне мікродобриво Valagro",
    "brexil-zn": "Brexil Zn — хелатне мікродобриво з цинком Valagro",
    "control-dmp": "Control DMP — NP-добриво з підкислювальною дією Valagro",
    "eraiz": "Ерайз — регулятор росту Miller",
    "ferrilen-trium": "Ferrilene Trium — хелат заліза Valagro",
    "ferrilene-4-8-orto-orto": "Ferrilene 4.8 Orto-Orto — хелат заліза Valagro",
    "haifa-mkp-0-52-34": "Haifa MKP 0-52-34 — водорозчинне PK-добриво Haifa Group",
    "kemira-balans-nitrate-balancer": "Кеміра Баланс / Nitrate Balancer — борно-молібденовий продукт Organic Planet",
    "kemira-dlya-hazonu-npk-12-11-18": "Кеміра для газону NPK 12-11-18 — гранульоване NPK-добриво",
    "kemira-grunt-kropker-npk-11-11-21": "Кеміра Ґрунт (Кропкер) NPK 11-11-21 — гранульоване NPK-добриво",
    "kemira-lyuks-npk-14-11-25": "Кеміра Люкс NPK 14-11-25 — водорозчинне NPK-добриво",
    "kemira-npk-12-46-8": "Кеміра NPK 12-46-8 — водорозчинне NPK-добриво",
    "kemira-npk-18-18-18": "Кеміра NPK 18-18-18 — водорозчинне NPK-добриво",
    "kemira-ukorinyuvach": "Кеміра Укорінювач — біостимулятор коренеутворення Organic Planet",
    "kemira-zav-yaz": "Кеміра Зав'язь — фосфорно-калійне добриво",
    "kendal": "Kendal — біостимулятор захисних реакцій рослин Valagro",
    "kendal-root": "Kendal Root — кореневий біостимулятор Valagro",
    "kendal-te": "Kendal TE — мікроелементний біостимулятор Valagro",
    "master-npk-13-40-13": "MASTER 13-40-13 — водорозчинне NPK-добриво Valagro",
    "master-npk-15-5-30": "MASTER 15-5-30+2 — водорозчинне NPK-добриво Valagro",
    "master-npk-17-6-18": "MASTER 17-6-18 — водорозчинне NPK-добриво Valagro",
    "master-npk-18-18-18": "MASTER 18-18-18 — водорозчинне NPK-добриво Valagro",
    "master-npk-20-20-20": "MASTER 20-20-20 — водорозчинне NPK-добриво Valagro",
    "master-npk-3-11-38": "MASTER 3-11-38 — водорозчинне NPK-добриво Valagro",
    "max-600-seasailer": "MAX 600 SeaSailer — біостимулятор з екстрактом водоростей CityMax",
    "maxicrop-cream": "Maxicrop Cream — біостимулятор Valagro",
    "maxicrop-extra": "MC Extra (Maxicrop Extra) — біостимулятор Valagro",
    "maxicrop-set-maksikrop-zav-yaz": "Maxicrop Set — біостимулятор Valagro",
    "megafol": "Megafol — антистресовий біостимулятор Valagro",
    "micro-np": "Micro NP — мікрогранульоване NP-добриво Valagro",
    "neocore": "NeoCore — кореневий біостимулятор Neova",
    "neoflora": "NeoFlora — біостимулятор Neova",
    "neoterra-aqua": "NeoTerra Aquafix™ — органічний кондиціонер ґрунту Neova",
    "neoterra-organic-c": "NeoTerra Organic-C — органічний кондиціонер ґрунту Neova",
    "neovivo": "NeoVivo — антистресовий біостимулятор Neova",
    "osmocote-bloom-12-7-18-23m": "Osmocote Bloom 12-7-18 (2–3M) — добриво контрольованого вивільнення ICL",
    "osmocote-decor-16-8-12-56m": "Osmocote 5 16-8-12 (5–6M) — добриво контрольованого вивільнення ICL",
    "osmocote-granula-max-14-8-11-te-56m": "Osmocote Granula-MAX 14-8-11+TE (5–6M) — добриво контрольованого вивільнення ICL",
    "osmocote-landscape-16-9-12-34m": "Osmocote Landscape 16-9-12 (3–4M) — добриво контрольованого вивільнення ICL",
    "osmocote-potassium-12-8-19-34m": "Osmocote Potassium 12-8-19 (3–4M) — добриво контрольованого вивільнення ICL",
    "osmocote-quick-start-22-5-6-45m": "Osmocote Quick Start 22-5-6 (4–5M) — добриво контрольованого вивільнення ICL",
    "osmocote-start-11-11-17-1-5m": "Osmocote Start 11-11-17 (1,5M) — добриво контрольованого вивільнення ICL",
    "pekacid-npk-0-60-20": "Nova PeKacid 0-60-20 — водорозчинне PK-добриво ICL",
    "plantafol-npk-0-25-50": "PLANTAFOL 0-25-50 — водорозчинне листкове NPK-добриво Valagro",
    "plantafol-npk-10-54-10": "PLANTAFOL 10-54-10 — водорозчинне листкове NPK-добриво Valagro",
    "plantafol-npk-20-20-20": "PLANTAFOL 20-20-20 — водорозчинне листкове NPK-добриво Valagro",
    "plantafol-npk-30-10-10": "PLANTAFOL 30-10-10 — водорозчинне листкове NPK-добриво Valagro",
    "plantafol-npk-5-15-45": "PLANTAFOL 5-15-45 — водорозчинне листкове NPK-добриво Valagro",
    "radifarm": "Radifarm — кореневий біостимулятор Valagro",
    "solupotasse-sulfat-kaliyu": "SoluPotasse — водорозчинний сульфат калію Tessenderlo Kerley",
    "spidfol-amino-vehetatsiya": "Speedfol Amino Vegetative — амінокислотний коректор живлення Terral Tarsa",
    "sprei-eid": "Спрей-Ейд (Spray-Aide) — ад'ювант-підкислювач Miller",
    "sulfat-mahniyu": "Сульфат магнію — водорозчинне магнієве добриво Alventa",
    "sweet": "Sweet — біостимулятор дозрівання Valagro",
    "switch-625-wg": "Світч 62,5 WG — фунгіцид Syngenta",
    "terra-sorb": "Terra-Sorb — амінокислотний біостимулятор Bioiberica",
    "valagro-edta-5sg": "Valagro EDTA 5SG — комплексне хелатне мікродобриво Valagro",
    "valagro-edta-fe-13": "Valagro EDTA Fe 13% — хелат заліза Valagro",
    "viva": "Viva — біостимулятор ризосфери Valagro",
}
_CANONICAL_TITLE_MIGRATION_ID = "20260922_canonical_nonpot_titles_v1"


def _apply_canonical_nonpot_titles_once(con: sqlite3.Connection) -> None:
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
        (_CANONICAL_TITLE_MIGRATION_ID,),
    ).fetchone():
        return
    rows = {
        row["product_id"]: str(row["category_id"] or "").strip().lower()
        for row in con.execute(
            "SELECT product_id,category_id FROM products WHERE product_id IN (%s)"
            % ",".join("?" for _ in _CANONICAL_NONPOT_TITLES),
            tuple(_CANONICAL_NONPOT_TITLES),
        ).fetchall()
    }
    with con:
        for product_id, name in _CANONICAL_NONPOT_TITLES.items():
            category = rows.get(product_id)
            if category is None or category in {"containers", "контейнери"}:
                continue
            con.execute(
                "UPDATE products SET name=?, updated_at=CURRENT_TIMESTAMP WHERE product_id=?",
                (name, product_id),
            )
        con.execute(
            "INSERT INTO runtime_migrations(migration_id,applied_at) VALUES(?,CURRENT_TIMESTAMP)",
            (_CANONICAL_TITLE_MIGRATION_ID,),
        )


def package_group_for(value, unit) -> str | None:
    if value is None:
        return None
    unit = str(unit or "").strip().lower()
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if unit == "kg":
        amount *= Decimal("1000")
    elif unit == "g":
        pass
    elif unit == "l":
        amount *= Decimal("1000")
    elif unit == "ml":
        pass
    else:
        return None
    if amount <= Decimal("50"):
        return "small"
    if Decimal("100") <= amount <= Decimal("1000"):
        return "medium"
    if amount >= Decimal("5000"):
        return "large"
    return None


def _enforce_package_group_invariant(con: sqlite3.Connection) -> None:
    global _PACKAGE_GROUP_INVARIANT_DONE
    if _PACKAGE_GROUP_INVARIANT_DONE:
        return
    with _INVARIANT_LOCK:
        if _PACKAGE_GROUP_INVARIANT_DONE:
            return
        rows = con.execute(
            "SELECT sku_id,package_value,package_unit,package_group FROM skus"
        ).fetchall()
        updates = []
        for row in rows:
            expected = package_group_for(row["package_value"], row["package_unit"])
            if row["package_group"] != expected:
                updates.append((expected, row["sku_id"]))
        if updates:
            con.executemany(
                "UPDATE skus SET package_group=? WHERE sku_id=?",
                updates,
            )
            con.commit()
        _PACKAGE_GROUP_INVARIANT_DONE = True


def _apply_runtime_migrations_once(con: sqlite3.Connection) -> None:
    global _RUNTIME_MIGRATIONS_DONE
    if _RUNTIME_MIGRATIONS_DONE:
        return
    with _MIGRATION_LOCK:
        if _RUNTIME_MIGRATIONS_DONE:
            return
        product_master_v5_migrations.apply_runtime_migrations(con)
        _apply_canonical_nonpot_titles_once(con)
        _RUNTIME_MIGRATIONS_DONE = True


def _needs_rebuild() -> bool:
    if not DB_PATH.is_file():
        return True
    rebuild = str(os.getenv("BB610_V5_REBUILD_ON_SOURCE_CHANGE", "")).strip().lower()
    if rebuild not in {"1", "true", "yes"}:
        return False
    db_mtime = DB_PATH.stat().st_mtime
    return any(
        path.is_file() and path.stat().st_mtime > db_mtime
        for path in (STAGE, CONTENT, MEDIA, SCHEMA, BOOTSTRAP)
    )


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
                "--content",
                str(CONTENT),
                "--media",
                str(MEDIA),
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
    _enforce_package_group_invariant(con)
    _apply_runtime_migrations_once(con)
    return con


def _json(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _runtime_commerce_map() -> dict[str, dict]:
    """Read the operational sku_commerce table without creating/mutating it.

    Product Master V5 owns identity/content/media. Operational commerce remains
    the single live source for price, availability, stock and enabled state.
    When a runtime DB/table is unavailable (CI/bootstrap), V5 snapshot commerce
    remains the deterministic fallback.
    """
    if not LIVE_DB_PATH.is_file():
        return {}
    con = None
    try:
        con = sqlite3.connect(f"file:{LIVE_DB_PATH}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        table = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sku_commerce'"
        ).fetchone()
        if not table:
            return {}
        return {
            row["sku"]: dict(row)
            for row in con.execute(
                """
                SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at
                FROM sku_commerce
                """
            )
        }
    except sqlite3.Error:
        return {}
    finally:
        if con is not None:
            con.close()


def _overlay_commerce(item: dict, sku_id: str, runtime: dict[str, dict]) -> dict:
    live = runtime.get(sku_id)
    if not live:
        item["commerce_source"] = "v5_snapshot"
        return item
    for key in ("price", "sale_price", "availability", "stock_qty", "enabled", "updated_at"):
        if key in live:
            target = "commerce_enabled" if key == "enabled" and "commerce_enabled" in item else key
            item[target] = live[key]
    item["commerce_source"] = "runtime_sku_commerce"
    return item


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


def resolve_sku(value: str) -> dict | None:
    runtime = _runtime_commerce_map()
    with _connect() as con:
        row = con.execute(
            """
            SELECT s.sku_id AS canonical_sku_id,
                   c.price,c.sale_price,c.availability,c.stock_qty,
                   c.enabled,c.updated_at
            FROM skus s
            LEFT JOIN sku_commerce c ON c.sku_id=s.sku_id
            WHERE s.sku_id=?
            LIMIT 1
            """,
            (value,),
        ).fetchone()
        if row:
            data = dict(row)
            live = runtime.get(value)
            if live:
                for key in ("price","sale_price","availability","stock_qty","enabled","updated_at"):
                    data[key] = live.get(key)
            data.update({
                "requested_sku_id": value,
                "is_alias": False,
                "commerce_source": "runtime_sku_commerce" if live else "v5_snapshot",
            })
            return data

        row = con.execute(
            """
            SELECT a.alias_sku_id,a.canonical_sku_id,
                   ac.price,ac.sale_price,ac.availability,ac.stock_qty,
                   ac.enabled,ac.updated_at
            FROM sku_aliases a
            LEFT JOIN sku_alias_commerce ac ON ac.alias_sku_id=a.alias_sku_id
            WHERE a.alias_sku_id=? AND a.active=1
            LIMIT 1
            """,
            (value,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        live = runtime.get(value)
        if live:
            for key in ("price","sale_price","availability","stock_qty","enabled","updated_at"):
                data[key] = live.get(key)
        data.update({
            "requested_sku_id": value,
            "is_alias": True,
            "commerce_source": "runtime_sku_commerce" if live else "preserved_alias_snapshot",
        })
        return data

def resolve_sku_id(value: str) -> str | None:
    row = resolve_sku(value)
    return row["canonical_sku_id"] if row else None


def _media_for_sku(con: sqlite3.Connection, sku_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT m.media_id,m.path,m.kind,m.alt,m.verification_status,
               sm.is_primary,sm.sort_order,sm.binding_kind,sm.source_kind,
               sm.source_url
        FROM sku_media sm
        JOIN media m ON m.media_id=sm.media_id
        WHERE sm.sku_id=?
        ORDER BY sm.is_primary DESC, sm.sort_order ASC, m.media_id ASC
        """,
        (sku_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _media_for_product(con: sqlite3.Connection, product_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT m.media_id,m.path,m.kind,m.alt,m.verification_status,
               pm.sort_order,pm.source_kind,pm.source_url
        FROM product_media pm
        JOIN media m ON m.media_id=pm.media_id
        WHERE pm.product_id=?
        ORDER BY pm.sort_order ASC,m.media_id ASC
        """,
        (product_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _sku_rows(
    con: sqlite3.Connection,
    product_id: str,
    runtime_commerce: dict[str, dict] | None = None,
) -> list[dict]:
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
    runtime_commerce = runtime_commerce if runtime_commerce is not None else _runtime_commerce_map()
    result = []
    for row in rows:
        item = dict(row)
        item["attributes"] = _json(item.pop("attributes_json", None), {})
        item["media"] = _media_for_sku(con, item["sku_id"])
        item = _overlay_commerce(item, item["sku_id"], runtime_commerce)
        result.append(item)
    return result


def _sources_for_product(con: sqlite3.Connection, product_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT source_id,source_type,source_url,source_label,verified_at,status,notes
        FROM product_sources
        WHERE product_id=?
        ORDER BY verified_at DESC, source_id ASC
        """,
        (product_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def product(product_id_or_alias: str, *, public_only: bool = True) -> dict | None:
    canonical = resolve_product_id(product_id_or_alias)
    if not canonical:
        return None
    with _connect() as con:
        row = con.execute(
            """
            SELECT product_id,slug,name,brand,manufacturer,category_id,
                   short_description,description,application,composition,
                   benefits_json,how_it_works,characteristics_json,
                   seo_title,seo_description,public_enabled,status,created_at,updated_at
            FROM products WHERE product_id=?
            """,
            (canonical,),
        ).fetchone()
        if not row:
            return None
        if public_only and (not bool(row["public_enabled"]) or row["status"] != "active"):
            return None
        item = dict(row)
        item["benefits"] = _json(item.pop("benefits_json", None), [])
        item["characteristics"] = _json(item.pop("characteristics_json", None), [])
        item["sources"] = _sources_for_product(con, canonical)
        item["media"] = _media_for_product(con, canonical)
        runtime_commerce = _runtime_commerce_map()
        item["skus"] = _sku_rows(con, canonical, runtime_commerce)
        item["aliases"] = [
            r["alias"]
            for r in con.execute(
                "SELECT alias FROM product_aliases WHERE product_id=? AND active=1 ORDER BY alias",
                (canonical,),
            )
        ]
        return item


def resolve_order_sku(value: str) -> dict | None:
    """Resolve a sellable requested SKU against V5 identity and live commerce."""
    commerce = resolve_sku(value)
    if not commerce:
        return None
    canonical = commerce["canonical_sku_id"]
    with _connect() as con:
        row = con.execute(
            """
            SELECT s.sku_id,s.product_id,s.manufacturer_sku,
                   s.package_value,s.package_unit,s.package_label,s.package_group,
                   s.attributes_json,s.enabled AS identity_enabled,
                   p.slug,p.name,p.brand,p.manufacturer,p.category_id,
                   p.public_enabled,p.status
            FROM skus s
            JOIN products p ON p.product_id=s.product_id
            WHERE s.sku_id=?
            LIMIT 1
            """,
            (canonical,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["attributes"] = _json(item.pop("attributes_json", None), {})
        item.update(commerce)
        return item


def snapshot(*, public_only: bool = True) -> dict:
    runtime_commerce = _runtime_commerce_map()
    with _connect() as con:
        where = "WHERE public_enabled=1 AND status='active'" if public_only else ""
        products = [
            dict(row)
            for row in con.execute(
                f"""
                SELECT product_id,slug,name,brand,manufacturer,category_id,
                       short_description,description,application,composition,
                       benefits_json,how_it_works,characteristics_json,
                       seo_title,seo_description,public_enabled,status,created_at,updated_at
                FROM products
                {where}
                ORDER BY category_id,brand,name,product_id
                """
            )
        ]
        for item in products:
            item["benefits"] = _json(item.pop("benefits_json", None), [])
            item["characteristics"] = _json(item.pop("characteristics_json", None), [])
            item["sources"] = _sources_for_product(con, item["product_id"])
            item["media"] = _media_for_product(con, item["product_id"])
            item["skus"] = _sku_rows(con, item["product_id"], runtime_commerce)

        public_product_ids = {
            row["product_id"]
            for row in con.execute(
                "SELECT product_id FROM products WHERE public_enabled=1 AND status='active'"
            )
        }
        public_skus = con.execute(
            """
            SELECT COUNT(*)
            FROM skus s
            JOIN products p ON p.product_id=s.product_id
            WHERE p.public_enabled=1 AND p.status='active'
            """
        ).fetchone()[0]
        product_aliases = [
            dict(row)
            for row in con.execute(
                """
                SELECT alias,product_id,alias_kind,active
                FROM product_aliases
                WHERE active=1
                ORDER BY alias
                """
            )
        ]
        sku_aliases = [
            dict(row)
            for row in con.execute(
                """
                SELECT a.alias_sku_id,a.canonical_sku_id,a.alias_kind,a.active,
                       ac.price,ac.sale_price,ac.availability,ac.stock_qty,
                       ac.enabled,ac.updated_at
                FROM sku_aliases a
                LEFT JOIN sku_alias_commerce ac ON ac.alias_sku_id=a.alias_sku_id
                WHERE a.active=1
                ORDER BY a.alias_sku_id
                """
            )
        ]
        for item in sku_aliases:
            live = runtime_commerce.get(item["alias_sku_id"])
            if live:
                for key in ("price","sale_price","availability","stock_qty","enabled","updated_at"):
                    item[key] = live.get(key)
                item["commerce_source"] = "runtime_sku_commerce"
            else:
                item["commerce_source"] = "preserved_alias_snapshot"

        counts = {
            "products": con.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "public_products": len(public_product_ids),
            "hidden_products": con.execute(
                "SELECT COUNT(*) FROM products WHERE public_enabled=0"
            ).fetchone()[0],
            "skus": con.execute("SELECT COUNT(*) FROM skus").fetchone()[0],
            "public_skus": public_skus,
            "sku_aliases": con.execute("SELECT COUNT(*) FROM sku_aliases").fetchone()[0],
            "sku_alias_commerce": con.execute("SELECT COUNT(*) FROM sku_alias_commerce").fetchone()[0],
            "media": con.execute("SELECT COUNT(*) FROM media").fetchone()[0],
            "product_media": con.execute("SELECT COUNT(*) FROM product_media").fetchone()[0],
            "exact_sku_media": con.execute(
                "SELECT COUNT(DISTINCT sku_id) FROM sku_media"
            ).fetchone()[0],
            "product_sources": con.execute("SELECT COUNT(*) FROM product_sources").fetchone()[0],
            "request_price": con.execute(
                "SELECT COUNT(*) FROM sku_commerce WHERE availability='request_price'"
            ).fetchone()[0],
        }
        return {
            "schema_version": "5.0",
            "source": "bb610-product-master-v5",
            "counts": counts,
            "products": products,
            "product_aliases": product_aliases,
            "sku_aliases": sku_aliases,
        }
