from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "data" / "product_content" / "plantlogic_v2_final_20260928.json"
MEDIA_MANIFEST_PATH = ROOT / "data" / "product_content" / "plantlogic_v2_media_manifest_20260928.json"

OLD_SPLIT_DEFAULTS = {
    "plantlogic-micro-tube-stake": "plantlogic-micro-tube-stake-1205018",
    "plantlogic-rivus-2in1-slab-base": "plantlogic-rivus-slab-base",
}

LEGACY_SKU_ALIASES = {
    "BB610-PLT-1308125-EA": "PL-BB-1308125-BK",
}

COLOR_MAP = {
    "BK": ("black", "Чорний"),
    "WH": ("white", "Білий"),
    "TC": ("terracotta", "Теракотовий"),
}


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_spec() -> dict:
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    expected = data.get("expected") or {}
    if len(data.get("canonical_products") or []) != int(expected.get("canonical_products") or 0):
        raise RuntimeError("PlantLogic V2 canonical product count mismatch")
    if len(data.get("aliases") or []) != int(expected.get("alias_reference") or 0):
        raise RuntimeError("PlantLogic V2 alias count mismatch")
    return data


def _ensure_product_columns(con: sqlite3.Connection) -> None:
    columns = {row["name"] for row in con.execute("PRAGMA table_info(products)").fetchall()}
    if "manufacturer_title" not in columns:
        con.execute("ALTER TABLE products ADD COLUMN manufacturer_title TEXT")
    if "manufacturer_product_number" not in columns:
        con.execute("ALTER TABLE products ADD COLUMN manufacturer_product_number TEXT")


def _json(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _upsert_characteristic(rows: list, label: str, value: str | None) -> None:
    rows[:] = [
        row for row in rows
        if not (isinstance(row, dict) and str(row.get("label") or "").strip() == label)
    ]
    if value not in (None, ""):
        rows.append({"label": label, "value": str(value)})


def _application_text(spec: dict) -> str:
    primary = str(spec.get("market_category") or "").strip()
    apps = [str(x).strip() for x in (spec.get("applications") or []) if str(x).strip()]
    bits = []
    if primary:
        bits.append("Основне призначення: " + primary + ".")
    if apps:
        bits.append("Додаткові застосування: " + "; ".join(apps) + ".")
    return " ".join(bits)


def _source_template(con: sqlite3.Connection, spec: dict) -> sqlite3.Row | None:
    pid = str(spec["canonical_product_id"])
    row = con.execute("SELECT * FROM products WHERE product_id=?", (pid,)).fetchone()
    if row:
        return row
    for sku in spec.get("skus") or []:
        sid = str(sku.get("sku_id") or "")
        if not sid:
            continue
        row = con.execute(
            """
            SELECT p.* FROM products p
            JOIN skus s ON s.product_id=p.product_id
            WHERE s.sku_id=?
            LIMIT 1
            """,
            (sid,),
        ).fetchone()
        if row:
            return row
    return None


def _manufacturer_titles(spec: dict) -> list[str]:
    values = []
    for value in spec.get("manufacturer_titles") or []:
        value = str(value or "").strip()
        if value and value not in values:
            values.append(value)
    return values


def _manufacturer_numbers(spec: dict) -> list[str]:
    values = []
    for value in spec.get("manufacturer_product_numbers") or []:
        value = str(value or "").strip()
        if value and value not in values:
            values.append(value)
    return values


def _product_characteristics(base, spec: dict) -> str:
    rows = _json(base["characteristics_json"] if base else None, [])
    if not isinstance(rows, list):
        rows = []
    rows = [row for row in rows if isinstance(row, dict)]
    titles = _manufacturer_titles(spec)
    numbers = _manufacturer_numbers(spec)
    _upsert_characteristic(rows, "Оригінальна назва", " / ".join(titles))
    _upsert_characteristic(rows, "Артикул виробника", " / ".join(numbers))
    _upsert_characteristic(rows, "Призначення", _application_text(spec))
    _upsert_characteristic(rows, "__plantlogic_sections", str(spec.get("plantlogic_section") or ""))
    _upsert_characteristic(rows, "__market_category", str(spec.get("market_category") or ""))
    _upsert_characteristic(
        rows,
        "__applications",
        "|".join(str(x).strip() for x in (spec.get("applications") or []) if str(x).strip()),
    )
    _upsert_characteristic(
        rows,
        "__manufacturer_variant",
        "TO_VERIFY" if str(spec.get("status") or "") == "TO_VERIFY" else None,
    )
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def _default_description(spec: dict) -> tuple[str, str]:
    title = str(spec["title"])
    manufacturer_title = " / ".join(_manufacturer_titles(spec))
    short = title + ". Офіційна продукція PlantLogic для професійних систем вирощування."
    description = title + " — canonical-картка BB610 Market за структурою PlantLogic V2 Final."
    if manufacturer_title:
        description += " Оригінальна назва виробника: " + manufacturer_title + "."
    return short, description


def _upsert_product(con: sqlite3.Connection, spec: dict) -> None:
    pid = str(spec["canonical_product_id"])
    title = str(spec["title"])
    base = _source_template(con, spec)
    short_default, description_default = _default_description(spec)
    titles = _manufacturer_titles(spec)
    numbers = _manufacturer_numbers(spec)
    now = _now()
    public_enabled = 0 if spec.get("public_enabled") is False else 1
    public_status = "active" if public_enabled else "hidden"
    fields = {
        "slug": pid,
        "name": title,
        "brand": "Plantlogic",
        "manufacturer": "Plantlogic",
        "manufacturer_title": " / ".join(titles) or None,
        "manufacturer_product_number": " / ".join(numbers) or None,
        "category_id": str(spec.get("technical_category_id") or "accessories"),
        "short_description": (base["short_description"] if base and base["short_description"] else short_default),
        "description": (base["description"] if base and base["description"] else description_default),
        "application": _application_text(spec),
        "composition": (base["composition"] if base else None),
        "benefits_json": (base["benefits_json"] if base and base["benefits_json"] else "[]"),
        "how_it_works": (base["how_it_works"] if base else None),
        "characteristics_json": _product_characteristics(base, spec),
        "seo_title": title + " | BB610 Market",
        "seo_description": title,
        "public_enabled": public_enabled,
        "status": public_status,
        "updated_at": now,
    }
    exists = con.execute("SELECT 1 FROM products WHERE product_id=?", (pid,)).fetchone()
    if exists:
        assignments = ",".join(key + "=?" for key in fields)
        con.execute(
            "UPDATE products SET " + assignments + " WHERE product_id=?",
            [*fields.values(), pid],
        )
        return
    con.execute(
        """
        INSERT INTO products(
          product_id,slug,name,brand,manufacturer,manufacturer_title,
          manufacturer_product_number,model,category_id,short_description,
          description,application,composition,benefits_json,how_it_works,
          characteristics_json,seo_title,seo_description,public_enabled,status,
          created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            pid, fields["slug"], title, fields["brand"], fields["manufacturer"],
            fields["manufacturer_title"], fields["manufacturer_product_number"],
            base["model"] if base else None, fields["category_id"],
            fields["short_description"], fields["description"], fields["application"],
            fields["composition"], fields["benefits_json"], fields["how_it_works"],
            fields["characteristics_json"], fields["seo_title"], fields["seo_description"],
            fields["public_enabled"], fields["status"],
            (base["created_at"] if base and base["created_at"] else now), now,
        ),
    )


def _volume_from_title(title: str):
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*л\b", str(title), flags=re.I)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _sku_attributes(existing: sqlite3.Row | None, spec: dict, sku_spec: dict) -> str:
    attrs = _json(existing["attributes_json"] if existing else None, {})
    if not isinstance(attrs, dict):
        attrs = {}
    sid = str(sku_spec["sku_id"])
    suffix = sid.rsplit("-", 1)[-1]
    if suffix in COLOR_MAP:
        code, label = COLOR_MAP[suffix]
        attrs["color_code"] = code
        attrs["color_label"] = label
    attrs["manufacturer_product_no"] = str(sku_spec.get("manufacturer_product_number") or "")
    attrs["manufacturer_title"] = str(sku_spec.get("manufacturer_title") or "")
    attrs["canonical_title"] = str(spec["title"])
    attrs["market_category"] = str(spec.get("market_category") or "")
    attrs["plantlogic_sections"] = [str(spec.get("plantlogic_section") or "")]
    attrs["applications"] = list(spec.get("applications") or [])
    if str(spec.get("status") or "") == "TO_VERIFY":
        attrs["manufacturer_variant"] = "TO_VERIFY"
    else:
        attrs.pop("manufacturer_variant", None)
    return json.dumps(attrs, ensure_ascii=False, separators=(",", ":"))


def _upsert_sku(con: sqlite3.Connection, spec: dict, sku_spec: dict, sort_order: int) -> None:
    sid = str(sku_spec["sku_id"])
    pid = str(spec["canonical_product_id"])
    existing = con.execute("SELECT * FROM skus WHERE sku_id=?", (sid,)).fetchone()
    attrs = _sku_attributes(existing, spec, sku_spec)
    manufacturer_no = str(sku_spec.get("manufacturer_product_number") or "") or None
    if existing:
        con.execute(
            """
            UPDATE skus
            SET product_id=?,manufacturer_sku=?,attributes_json=?,enabled=1
            WHERE sku_id=?
            """,
            (pid, manufacturer_no, attrs, sid),
        )
        return

    volume = _volume_from_title(str(spec.get("title") or ""))
    package_value = volume
    package_unit = "l" if volume is not None else None
    package_label = (
        (str(volume).rstrip("0").rstrip(".").replace(".", ",") + " л")
        if volume is not None else "1 шт"
    )
    con.execute(
        """
        INSERT INTO skus(
          sku_id,product_id,manufacturer_sku,package_value,package_unit,
          package_label,package_group,attributes_json,sort_order,enabled
        ) VALUES(?,?,?,?,?,?,NULL,?,?,1)
        """,
        (sid, pid, manufacturer_no, package_value, package_unit, package_label, attrs, sort_order),
    )
    con.execute(
        """
        INSERT INTO sku_commerce(
          sku_id,price,sale_price,availability,stock_qty,enabled,updated_at
        ) VALUES(?,NULL,NULL,'request_price',NULL,1,?)
        """,
        (sid, _now()),
    )


def _upsert_sources(con: sqlite3.Connection, spec: dict) -> None:
    pid = str(spec["canonical_product_id"])
    for url in spec.get("source_urls") or []:
        url = str(url or "").strip()
        if not url or "..." in url:
            continue
        digest = hashlib.sha1((pid + "|" + url).encode("utf-8")).hexdigest()[:16]
        con.execute(
            """
            INSERT INTO product_sources(
              source_id,product_id,source_type,source_url,source_label,
              verified_at,status,notes
            ) VALUES(?,?, 'plantlogic_v2_final', ?, 'PlantLogic official / V2 Final',
                     '2026-09-28','verified','PlantLogic V2 Final reconciliation source')
            ON CONFLICT(source_id) DO UPDATE SET
              product_id=excluded.product_id,
              source_url=excluded.source_url,
              status='verified',
              notes=excluded.notes
            """,
            ("plv2_" + digest, pid, url),
        )


def _migrate_legacy_sku_aliases(con: sqlite3.Connection) -> None:
    """Collapse obsolete commerce SKU identities into V2 compatibility aliases."""
    for alias_sku, canonical_sku in LEGACY_SKU_ALIASES.items():
        if not con.execute("SELECT 1 FROM skus WHERE sku_id=?", (canonical_sku,)).fetchone():
            raise RuntimeError("missing canonical SKU for legacy alias: " + canonical_sku)
        con.execute("DELETE FROM skus WHERE sku_id=?", (alias_sku,))
        con.execute(
            """
            INSERT INTO sku_aliases(alias_sku_id,canonical_sku_id,alias_kind,active)
            VALUES(?,?,'plantlogic_v2_legacy',1)
            ON CONFLICT(alias_sku_id) DO UPDATE SET
              canonical_sku_id=excluded.canonical_sku_id,
              alias_kind=excluded.alias_kind,
              active=1
            """,
            (alias_sku, canonical_sku),
        )


def _rebind_legacy_product_aliases(con: sqlite3.Connection) -> None:
    for old_id, target in OLD_SPLIT_DEFAULTS.items():
        con.execute(
            "UPDATE product_aliases SET product_id=? WHERE product_id=?",
            (target, old_id),
        )
        con.execute(
            """
            INSERT INTO product_aliases(alias,product_id,alias_kind,active)
            VALUES(?,?,'plantlogic_v2_split_legacy',1)
            ON CONFLICT(alias) DO UPDATE SET
              product_id=excluded.product_id,alias_kind=excluded.alias_kind,active=1
            """,
            (old_id, target),
        )


def _install_reconciliation_aliases(con: sqlite3.Connection, data: dict) -> None:
    canonical = {str(x["canonical_product_id"]) for x in data.get("canonical_products") or []}
    seen = set()
    for row in data.get("aliases") or []:
        alias = str(row.get("alias_manufacturer_product_number") or "").strip()
        target = str(row.get("canonical_target") or "").strip()
        if not alias or target not in canonical:
            raise RuntimeError("invalid PlantLogic V2 alias target: " + alias + " -> " + target)
        if alias in seen:
            raise RuntimeError("duplicate PlantLogic V2 alias: " + alias)
        seen.add(alias)
        con.execute(
            """
            INSERT INTO product_aliases(alias,product_id,alias_kind,active)
            VALUES(?,?,'manufacturer_product_number_v2',1)
            ON CONFLICT(alias) DO UPDATE SET
              product_id=excluded.product_id,alias_kind=excluded.alias_kind,active=1
            """,
            (alias, target),
        )


def _apply_media_manifest(con: sqlite3.Connection) -> None:
    if not MEDIA_MANIFEST_PATH.is_file():
        return
    data = json.loads(MEDIA_MANIFEST_PATH.read_text(encoding="utf-8"))
    for row in data.get("media") or []:
        con.execute(
            """
            INSERT INTO media(
              media_id,path,sha256,kind,source_url,verification_status,alt,created_at
            ) VALUES(?,?,?,?,?,'verified',?,?)
            ON CONFLICT(media_id) DO UPDATE SET
              path=excluded.path,sha256=excluded.sha256,kind=excluded.kind,
              source_url=excluded.source_url,verification_status='verified',
              alt=excluded.alt
            """,
            (
                row["media_id"], row["path"], row.get("sha256"), row.get("kind") or "image",
                row.get("source_url"), row.get("alt"), _now(),
            ),
        )
    for row in data.get("product_bindings") or []:
        con.execute(
            """
            INSERT INTO product_media(product_id,media_id,sort_order,source_kind,source_url)
            VALUES(?,?,?,?,?)
            ON CONFLICT(product_id,media_id) DO UPDATE SET
              sort_order=excluded.sort_order,source_kind=excluded.source_kind,
              source_url=excluded.source_url
            """,
            (
                row["product_id"], row["media_id"], int(row.get("sort_order") or 0),
                row.get("source_kind") or "plantlogic_v2_official", row.get("source_url"),
            ),
        )
    for row in data.get("sku_bindings") or []:
        if row.get("is_primary"):
            con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (row["sku_id"],))
        con.execute(
            """
            INSERT INTO sku_media(
              sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
            ) VALUES(?,?,?,?,'exact',?,?)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET
              is_primary=excluded.is_primary,sort_order=excluded.sort_order,
              source_kind=excluded.source_kind,source_url=excluded.source_url
            """,
            (
                row["sku_id"], row["media_id"], 1 if row.get("is_primary") else 0,
                int(row.get("sort_order") or 0),
                row.get("source_kind") or "plantlogic_v2_official", row.get("source_url"),
            ),
        )


def apply(con: sqlite3.Connection) -> bool:
    data = _load_spec()
    _ensure_product_columns(con)
    products = data.get("canonical_products") or []
    canonical_ids = {str(x["canonical_product_id"]) for x in products}

    for spec in products:
        _upsert_product(con, spec)

    sort_order = 10000
    for spec in products:
        for sku in spec.get("skus") or []:
            _upsert_sku(con, spec, sku, sort_order)
            sort_order += 1
        _upsert_sources(con, spec)

    _migrate_legacy_sku_aliases(con)
    _rebind_legacy_product_aliases(con)
    for old_id in OLD_SPLIT_DEFAULTS:
        if old_id not in canonical_ids:
            con.execute("DELETE FROM products WHERE product_id=?", (old_id,))

    _install_reconciliation_aliases(con, data)
    _apply_media_manifest(con)

    bad = con.execute(
        """
        SELECT product_id,name FROM products
        WHERE lower(brand)='plantlogic'
          AND name LIKE 'Горщик%'
          AND category_id='accessories'
        """
    ).fetchall()
    if bad:
        raise RuntimeError("PlantLogic pot categorized as Accessories")
    return True
