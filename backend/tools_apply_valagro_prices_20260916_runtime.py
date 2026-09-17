from __future__ import annotations

"""Apply the 2026-09-16 price source to the current Valagro/Syngenta PCV3 runtime.

This importer intentionally reconciles against the *current* Product Card v3 SKU
structure instead of assuming the older 197-SKU catalogue shape.

Safety rules:
- the normalized source must be the approved 195-row 2026-09-16 manifest;
- only the 12 already-approved Valagro/Syngenta product slugs are in scope;
- product identity is deterministic (name/formula -> exact slug);
- package matching is exact after unit normalization;
- a current V3 SKU must already have an existing commerce binding and row;
- source rows with no current SKU are reported and never invented;
- current SKU with no source price is reported and left untouched;
- zero/non-positive prices are never activated or written;
- writes are limited to price + the existing approved availability policy
  (in_stock, stock_qty NULL); sale_price and enabled are protected;
- Product Card v3 content, SKU/media structure, mappings, and legacy catalogue
  files are never modified;
- DB backup + transactional write + post-verify + automatic DB restore on verify
  failure.
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE = ROOT / "data" / "catalog_sources" / "bb610_market_prices_2026-09-16.json"
BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

ALLOWED_SLUGS = (
    "master-13-40-13",
    "master-20-20-20",
    "master-15-5-30",
    "master-3-11-38",
    "plantafol-20-20-20",
    "plantafol-10-54-10",
    "plantafol-30-10-10",
    "plantafol-5-15-45",
    "plantafol-0-25-50",
    "megafol",
    "radifarm",
    "viva",
)
ALLOWED_SET = set(ALLOWED_SLUGS)
EXPECTED_SOURCE_ROWS = 195
EXPECTED_TARGET_SOURCE_ROWS = 49


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def formula(value: Any) -> tuple[str, str, str] | None:
    s = re.sub(r"(?<=\d),(?=\d)", ".", str(value or ""))
    m = re.search(r"(?<!\d)(\d{1,2})\s*[-+]\s*(\d{1,2})\s*[-+]\s*(\d{1,2})(?!\d)", s)
    return tuple(m.groups()) if m else None


def pack_key(value: Any) -> str:
    s = str(value or "").strip().lower().replace("*", "").replace(",", ".")
    s = re.sub(r"\s+", " ", s)
    patterns = (
        (r"(\d+(?:\.\d+)?)\s*(?:мл|ml)\b", "ml"),
        (r"(\d+(?:\.\d+)?)\s*(?:кг|kg)\b", "kg"),
        (r"(\d+(?:\.\d+)?)\s*(?:г|g)\b", "g"),
        (r"(\d+(?:\.\d+)?)\s*(?:л|l)\b", "l"),
        (r"(\d+(?:\.\d+)?)\s*(?:шт|pcs?|pieces?)\b", "pcs"),
    )
    for pattern, unit in patterns:
        m = re.search(pattern, s, re.I)
        if m:
            return f"{float(m.group(1)):g}{unit}"
    return re.sub(r"[^0-9a-zа-яіїєґ]+", "", s, flags=re.I)


def source_slug(name: Any) -> str | None:
    raw = str(name or "").strip()
    low = raw.lower()
    f = formula(raw)
    if "master" in low and f:
        slug = "master-" + "-".join(f)
        return slug if slug in ALLOWED_SET else None
    if "plantafol" in low and f:
        slug = "plantafol-" + "-".join(f)
        return slug if slug in ALLOWED_SET else None
    if re.search(r"\bmegafol\b", low):
        return "megafol"
    if re.search(r"\bradifarm\b", low):
        return "radifarm"
    if low == "viva" or re.search(r"\bviva\b", low):
        return "viva"
    return None


def load_source() -> dict:
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if doc.get("source_file") != "цены_сайт_Market_160926.xlsx":
        raise RuntimeError(f"unexpected source_file: {doc.get('source_file')!r}")
    if doc.get("source_date") != "2026-09-16":
        raise RuntimeError(f"unexpected source_date: {doc.get('source_date')!r}")
    if not isinstance(rows, list) or len(rows) != EXPECTED_SOURCE_ROWS:
        raise RuntimeError(f"price manifest must contain {EXPECTED_SOURCE_ROWS} rows; got {len(rows or [])}")

    target_rows = []
    seen: set[tuple[str, str]] = set()
    for row_no, row in enumerate(rows, start=2):
        if not isinstance(row, dict):
            raise RuntimeError(f"source row {row_no} is not an object")
        slug = source_slug(row.get("source_name"))
        if not slug:
            continue
        package = str(row.get("package") or "").strip()
        key = pack_key(package)
        price = row.get("price")
        if not key:
            raise RuntimeError(f"row {row_no}: empty package key")
        if not isinstance(price, (int, float)) or price < 0:
            raise RuntimeError(f"row {row_no}: invalid price {price!r}")
        identity = (slug, key)
        if identity in seen:
            raise RuntimeError(f"duplicate source identity {slug}/{package}")
        seen.add(identity)
        target_rows.append({
            "source_row": row_no,
            "slug": slug,
            "source_name": str(row.get("source_name") or "").strip(),
            "package": package,
            "pack_key": key,
            "price": float(price),
        })

    if len(target_rows) != EXPECTED_TARGET_SOURCE_ROWS:
        raise RuntimeError(
            f"expected {EXPECTED_TARGET_SOURCE_ROWS} Valagro/Syngenta source rows; got {len(target_rows)}"
        )
    counts = Counter(x["slug"] for x in target_rows)
    missing_slugs = [slug for slug in ALLOWED_SLUGS if counts.get(slug, 0) == 0]
    if missing_slugs:
        raise RuntimeError("source has no rows for: " + ", ".join(missing_slugs))
    return {**doc, "target_rows": target_rows}


def _runtime_services():
    from backend.db import DB_PATH, connect
    from backend.services import product_cards_v3 as pcv3
    return DB_PATH, connect, pcv3


def build_plan() -> dict:
    source = load_source()
    DB_PATH, connect, pcv3 = _runtime_services()

    cards_by_slug: dict[str, dict] = {}
    for summary in pcv3.list_cards():
        pid = str(summary.get("product_id") or "")
        card = pcv3.get(pid) if pid else None
        if not isinstance(card, dict):
            continue
        slug = str(card.get("slug") or "").strip().lower()
        if slug in ALLOWED_SET:
            if slug in cards_by_slug:
                raise RuntimeError(f"duplicate current V3 slug: {slug}")
            cards_by_slug[slug] = card
    missing_cards = [slug for slug in ALLOWED_SLUGS if slug not in cards_by_slug]
    if missing_cards:
        raise RuntimeError("current V3 cards missing: " + ", ".join(missing_cards))

    mapping_by_pid = {
        str(row.get("product_id") or ""): row
        for row in (pcv3.commerce_map().get("products") or [])
        if isinstance(row, dict) and row.get("product_id")
    }
    source_by_key = {(x["slug"], x["pack_key"]): x for x in source["target_rows"]}

    with connect() as con:
        commerce_rows = {
            str(row["sku"]): dict(row)
            for row in con.execute(
                "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce"
            ).fetchall()
        }

    actions: list[dict] = []
    current_without_price: list[dict] = []
    zero_price: list[dict] = []
    consumed_source: set[tuple[str, str]] = set()
    seen_commerce: set[str] = set()
    failures: list[str] = []

    for slug in ALLOWED_SLUGS:
        card = cards_by_slug[slug]
        pid = str(card.get("product_id") or "")
        mapping = mapping_by_pid.get(pid)
        if not mapping:
            failures.append(f"{slug}: commerce product mapping missing")
            continue
        links = {
            str(x.get("sku_id") or ""): str(x.get("existing_commerce_sku_key") or "").strip()
            for x in (mapping.get("skus") or [])
            if isinstance(x, dict) and x.get("sku_id")
        }
        live_skus = [
            x for x in ((card.get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict) and x.get("enabled", True)
        ]
        if not live_skus:
            failures.append(f"{slug}: no enabled V3 SKU")
            continue

        for sku in live_skus:
            sid = str(sku.get("sku_id") or "").strip()
            package = str(sku.get("package") or sku.get("label") or "").strip()
            pkey = pack_key(package)
            commerce_key = links.get(sid, "")
            if not sid or not commerce_key:
                failures.append(f"{slug}/{package}: current V3 SKU has no commerce binding")
                continue
            live = commerce_rows.get(commerce_key)
            if not live:
                failures.append(f"{slug}/{package}: commerce row missing {commerce_key}")
                continue

            src = source_by_key.get((slug, pkey))
            if not src:
                current_without_price.append({
                    "slug": slug,
                    "product_id": pid,
                    "sku_id": sid,
                    "commerce_key": commerce_key,
                    "package": package,
                    "current_price": live.get("price"),
                })
                continue
            consumed_source.add((slug, pkey))
            if float(src["price"]) <= 0:
                zero_price.append({**src, "sku_id": sid, "commerce_key": commerce_key})
                continue
            if commerce_key in seen_commerce:
                failures.append(f"duplicate commerce target: {commerce_key}")
                continue
            seen_commerce.add(commerce_key)
            actions.append({
                **src,
                "product_id": pid,
                "sku_id": sid,
                "commerce_key": commerce_key,
                "current_price": live.get("price"),
                "current_sale_price": live.get("sale_price"),
                "current_availability": live.get("availability"),
                "current_stock_qty": live.get("stock_qty"),
                "current_enabled": bool(live.get("enabled")),
            })

    source_without_current = [
        row for row in source["target_rows"]
        if (row["slug"], row["pack_key"]) not in consumed_source
    ]

    action_counts = Counter(x["slug"] for x in actions)
    missing_action_slugs = [slug for slug in ALLOWED_SLUGS if action_counts.get(slug, 0) == 0]
    if missing_action_slugs:
        failures.append("no positive exact price match for current SKU: " + ", ".join(missing_action_slugs))
    if failures:
        raise RuntimeError("VALAGRO PRICE PREFLIGHT FAILED:\n- " + "\n- ".join(failures[:100]))

    return {
        "source_file": source.get("source_file"),
        "source_date": source.get("source_date"),
        "currency": source.get("currency", "UAH"),
        "source_target_rows": len(source["target_rows"]),
        "actions": actions,
        "current_without_source_price": current_without_price,
        "source_without_current_sku": source_without_current,
        "zero_price_skipped": zero_price,
        "per_slug": {slug: action_counts.get(slug, 0) for slug in ALLOWED_SLUGS},
        "db_path": str(DB_PATH),
    }


def backup_db(src_path: Path, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(src_path))
    try:
        dst = sqlite3.connect(str(dest_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def apply_plan(plan: dict) -> dict:
    DB_PATH, connect, _pcv3 = _runtime_services()
    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"valagro-prices-runtime-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_file = backup_dir / Path(DB_PATH).name
    backup_db(Path(DB_PATH), backup_file)

    keys = [x["commerce_key"] for x in plan["actions"]]
    before: dict[str, dict] = {}
    with connect() as con:
        placeholders = ",".join("?" for _ in keys)
        for row in con.execute(
            f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
            keys,
        ).fetchall():
            before[str(row["sku"])] = dict(row)

        ts = now()
        con.execute("BEGIN IMMEDIATE")
        try:
            for row in plan["actions"]:
                con.execute(
                    "UPDATE sku_commerce SET price=?, availability='in_stock', stock_qty=NULL, updated_at=? WHERE sku=?",
                    (row["price"], ts, row["commerce_key"]),
                )
            con.commit()
        except Exception:
            con.rollback()
            raise

    after: dict[str, dict] = {}
    with connect() as con:
        placeholders = ",".join("?" for _ in keys)
        for row in con.execute(
            f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
            keys,
        ).fetchall():
            after[str(row["sku"])] = dict(row)

    errors: list[str] = []
    for row in plan["actions"]:
        key = row["commerce_key"]
        previous = before.get(key)
        current = after.get(key)
        if not previous or not current:
            errors.append(f"missing commerce snapshot: {key}")
            continue
        if float(current.get("price")) != float(row["price"]):
            errors.append(f"price mismatch: {key}")
        if current.get("availability") != "in_stock":
            errors.append(f"availability mismatch: {key}")
        if current.get("stock_qty") is not None:
            errors.append(f"stock_qty not NULL: {key}")
        if current.get("sale_price") != previous.get("sale_price"):
            errors.append(f"sale_price changed: {key}")
        if current.get("enabled") != previous.get("enabled"):
            errors.append(f"enabled changed: {key}")

    if errors:
        backup_db(backup_file, Path(DB_PATH))
        raise RuntimeError("post-verify failed; DB restored:\n- " + "\n- ".join(errors[:100]))

    return {
        "status": "APPLIED",
        "updated": len(plan["actions"]),
        "backup_dir": str(backup_dir),
        "availability_in_stock": len(plan["actions"]),
        "stock_qty_null": len(plan["actions"]),
        "sale_price_unchanged": True,
        "enabled_unchanged": True,
        "pcv3_content_changed": False,
        "pcv3_sku_media_changed": False,
        "commerce_mapping_changed": False,
    }


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"valagro-prices-runtime-{stamp()}.json"
    path.write_text(
        json.dumps({"mode": mode, **plan, "apply": result}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely apply approved 2026-09-16 prices to current Valagro/Syngenta PCV3 commerce bindings."
    )
    parser.add_argument("--apply-safe", action="store_true")
    args = parser.parse_args()

    plan = build_plan()
    result = apply_plan(plan) if args.apply_safe else None
    report = write_report(plan, result, "APPLY_SAFE" if args.apply_safe else "DRY_RUN")

    print("BB610 VALAGRO/SYNGENTA RUNTIME PRICE RECONCILIATION")
    print("MODE:", "APPLY_SAFE" if args.apply_safe else "DRY_RUN")
    print("SOURCE:", plan["source_file"])
    print("SOURCE VALAGRO ROWS:", plan["source_target_rows"])
    print("EXACT CURRENT SKU PRICE MATCHES:", len(plan["actions"]))
    print("PER SLUG:", json.dumps(plan["per_slug"], ensure_ascii=False, sort_keys=True))
    print("CURRENT SKU WITHOUT SOURCE PRICE:", len(plan["current_without_source_price"]))
    for row in plan["current_without_source_price"]:
        print("  NO SOURCE PRICE:", row["slug"], "|", row["package"], "|", row["commerce_key"])
    print("SOURCE PACKAGE WITHOUT CURRENT SKU:", len(plan["source_without_current_sku"]))
    for row in plan["source_without_current_sku"]:
        print("  NO CURRENT SKU:", row["slug"], "|", row["package"], "|", row["price"])
    print("ZERO PRICE SKIPPED:", len(plan["zero_price_skipped"]))
    for row in plan["zero_price_skipped"]:
        print("  ZERO SKIP:", row["slug"], "|", row["package"], "|", row["commerce_key"])
    print("PRICE POLICY: APPLY EXACT POSITIVE SOURCE PRICE")
    print("AVAILABILITY POLICY: IN_STOCK FOR UPDATED SKU")
    print("STOCK QTY POLICY: NULL")
    print("SALE PRICE: UNCHANGED")
    print("SALE ENABLED: UNCHANGED")
    if result:
        print("UPDATED:", result["updated"])
        print("BACKUP:", result["backup_dir"])
        print("RESULT: PASS")
    else:
        print("RESULT: PASS (DRY-RUN)")
    print("REPORT:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
