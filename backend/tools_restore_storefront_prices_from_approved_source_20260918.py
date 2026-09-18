from __future__ import annotations

"""Audit/restore storefront prices strictly from the approved 2026-09-16 source.

This tool works against the actual browser base snapshot (data/catalog.runtime.js)
and live sku_commerce. It never invents a price.

DRY-RUN (default):
- finds runtime products/SKU whose effective price is missing;
- classifies each missing SKU as:
  * APPROVED_PRICE: exact product identity + exact package in approved source;
  * ZERO_SOURCE_PRICE: source explicitly has 0 (do not publish a price);
  * SOURCE_PACKAGE_MISSING: product exists in source, this package does not;
  * PRODUCT_NOT_IN_SOURCE: product is absent from the approved price source;
- Switch/Світч and Aktara/Актара therefore remain unpriced unless a future
  approved source adds them.

APPLY-SAFE:
- updates ONLY APPROVED_PRICE rows whose live effective price is still NULL;
- price comes only from data/catalog_sources/bb610_market_prices_2026-09-16.json;
- sets availability=in_stock, stock_qty=NULL, enabled=1 for those exact rows;
- preserves sale_price;
- never changes any already-priced SKU;
- DB backup + full non-target row verification + automatic rollback.
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import DB_PATH, connect
from backend.services.product_commerce import commerce_map

RUNTIME = ROOT / "data" / "catalog.runtime.js"
SOURCE = ROOT / "data" / "catalog_sources" / "bb610_market_prices_2026-09-16.json"
BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

EXPECTED_SOURCE_ROWS = 195
EXPECTED_RUNTIME_PRODUCTS = 41
EXPECTED_RUNTIME_SKUS = 55


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.replace("ё", "е").replace("ґ", "г")
    s = re.sub(r"\s+", " ", s)
    return s


def formula(value: Any) -> tuple[str, str, str] | None:
    s = str(value or "").replace("–", "-").replace("—", "-").replace("+", "-")
    m = re.search(r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})(?!\d)", s)
    return tuple(m.groups()) if m else None


def pack_key(value: Any) -> str:
    s = norm(value).replace("*", "").replace(",", ".")
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


def load_runtime() -> dict:
    raw = RUNTIME.read_text(encoding="utf-8").strip()
    prefix = "window.BB610_CATALOG = "
    if not raw.startswith(prefix):
        raise RuntimeError("catalog.runtime.js wrapper changed")
    payload = raw[len(prefix):]
    if payload.endswith(";"):
        payload = payload[:-1]
    doc = json.loads(payload)
    products = doc.get("products") or []
    skus = doc.get("skus") or []
    if len(products) != EXPECTED_RUNTIME_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_RUNTIME_PRODUCTS} runtime products; got {len(products)}")
    if len(skus) != EXPECTED_RUNTIME_SKUS:
        raise RuntimeError(f"expected {EXPECTED_RUNTIME_SKUS} runtime SKU; got {len(skus)}")
    return doc


def load_source() -> dict:
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if not isinstance(rows, list) or len(rows) != EXPECTED_SOURCE_ROWS:
        raise RuntimeError(f"expected {EXPECTED_SOURCE_ROWS} approved source rows; got {len(rows or [])}")
    if doc.get("source_date") != "2026-09-16":
        raise RuntimeError(f"unexpected source date: {doc.get('source_date')}")
    return doc


def _formula_family(name: str) -> str:
    n = norm(name)
    if "master" in n or "мастер" in n:
        return "master"
    if "plantafol" in n or "плантафол" in n:
        return "plantafol"
    if "pekacid" in n or "пекацид" in n:
        return "pekacid"
    if "osmocote" in n or "осмокот" in n:
        return "osmocote"
    if "haifa" in n or "хайфа" in n:
        return "haifa"
    return ""


def _contains_all(name: str, *parts: str) -> bool:
    n = norm(name)
    return all(norm(x) in n for x in parts)


def _explicit_matcher(product_id: str) -> Callable[[str], bool] | None:
    rules: dict[str, Callable[[str], bool]] = {
        "megafol": lambda n: "megafol" in norm(n) or "мегафол" in norm(n),
        "radifarm": lambda n: "radifarm" in norm(n) or "радіфарм" in norm(n),
        "brexil-mix": lambda n: _contains_all(n, "brexil", "mix"),
        "kendal-root": lambda n: ("kendal root" in norm(n) or "kendal root" in norm(n).replace("рут", "root")),
        "control-dmp": lambda n: "control dmp" in norm(n) or "контроль дмп" in norm(n),
        "kendal": lambda n: (
            ("kendal" in norm(n) or "кендал" in norm(n))
            and "root" not in norm(n) and "рут" not in norm(n) and " te" not in (" "+norm(n))
        ),
        "viva": lambda n: re.search(r"\bviva\b", norm(n)) is not None or "віва" in norm(n),
        "solupotasse": lambda n: "solupotasse" in norm(n) or "солюпотасс" in norm(n),
        "magnesium-sulfate": lambda n: "сульфат магнію" in norm(n),
        "boroplus": lambda n: "boroplus" in norm(n) or "бороплюс" in norm(n),
        "brexil-combi": lambda n: _contains_all(n, "brexil", "combi"),
        "brexil-fe": lambda n: (
            _contains_all(n, "brexil", "fe") or _contains_all(n, "брексіл", "залізо")
        ),
        "ferrilene": lambda n: (
            ("ferrilene" in norm(n) or "ferrilen" in norm(n) or "феррілен" in norm(n))
            and ("4,8" in norm(n) or "4.8" in norm(n) or "orto-orto" in norm(n))
        ),
        "kemira-rooter": lambda n: (
            ("кеміра" in norm(n) or "kemira" in norm(n))
            and ("укорін" in norm(n) or "root" in norm(n))
        ),
        "benefit-pz": lambda n: ("benefit pz" in norm(n) or "benefit pz" in norm(n).replace("pz", "pz")),
        "blackjak": lambda n: "blackjak" in norm(n) or "блекджек" in norm(n),
        "maxicrop-cream": lambda n: _contains_all(n, "maxicrop", "cream"),
        "neocore": lambda n: "neocore" in norm(n) or "неокор" in norm(n),
        "sweet": lambda n: (
            re.search(r"\bsweet\b", norm(n)) is not None
            or re.search(r"\bsvit\b", norm(n)) is not None
        ),
        "brexil-ca": lambda n: (
            _contains_all(n, "brexil", "ca") or _contains_all(n, "брексіл", "кальцій")
        ),
        "brexil-zn": lambda n: (
            _contains_all(n, "brexil", "zn") or _contains_all(n, "брексіл", "цинк")
        ),
    }
    return rules.get(product_id)


def source_rows_for_product(product: dict, source_rows: list[dict]) -> list[dict]:
    pid = str(product.get("id") or "")
    name = str(product.get("name") or "")
    fam = _formula_family(name)
    f = formula(name)

    if fam and f:
        out = []
        for row in source_rows:
            sname = str(row.get("source_name") or "")
            if _formula_family(sname) != fam:
                continue
            if formula(sname) != f:
                continue
            out.append(row)
        return out

    matcher = _explicit_matcher(pid)
    if matcher:
        return [row for row in source_rows if matcher(str(row.get("source_name") or ""))]

    return []


def collapse_source(rows: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        key = pack_key(row.get("package"))
        if key:
            grouped[key].append(row)

    resolved: dict[str, dict] = {}
    conflicts: list[dict] = []
    for key, items in grouped.items():
        prices = {float(x.get("price")) for x in items if isinstance(x.get("price"), (int, float))}
        if len(prices) != 1:
            conflicts.append({
                "pack_key": key,
                "rows": items,
                "prices": sorted(prices),
            })
            continue
        chosen = dict(items[0])
        chosen["pack_key"] = key
        chosen["price"] = float(next(iter(prices)))
        chosen["duplicate_source_rows"] = len(items)
        resolved[key] = chosen
    return resolved, conflicts


def db_snapshot() -> dict[str, dict]:
    with connect() as con:
        return {
            str(r["sku"]): dict(r)
            for r in con.execute(
                "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at "
                "FROM sku_commerce"
            ).fetchall()
        }


def effective_price(row: dict | None) -> Any:
    if not isinstance(row, dict):
        return None
    return row.get("sale_price") if row.get("sale_price") is not None else row.get("price")


def build_plan() -> dict:
    runtime = load_runtime()
    source = load_source()
    live = commerce_map()

    skus_by_product: dict[str, list[dict]] = defaultdict(list)
    for sku in runtime.get("skus") or []:
        if isinstance(sku, dict) and sku.get("product_id"):
            skus_by_product[str(sku["product_id"])].append(sku)

    actions = []
    zero_rows = []
    no_source_products = []
    source_package_missing = []
    existing_priced = []
    conflicts = []
    product_summaries = []

    for product in runtime.get("products") or []:
        pid = str(product.get("id") or "")
        pskus = skus_by_product.get(pid, [])
        source_rows = source_rows_for_product(product, source["rows"])
        source_by_pack, source_conflicts = collapse_source(source_rows)
        if source_conflicts:
            conflicts.append({
                "product_id": pid,
                "name": product.get("name"),
                "conflicts": source_conflicts,
            })

        product_missing = 0
        product_actions = 0
        for sku in pskus:
            sid = str(sku.get("id") or "")
            package = str(sku.get("variant") or "")
            pkey = pack_key(package)
            current = live.get(sid)
            current_effective = effective_price(current)

            if current_effective is not None:
                existing_priced.append({
                    "product_id": pid,
                    "sku": sid,
                    "package": package,
                    "price": current_effective,
                })
                continue

            product_missing += 1
            src = source_by_pack.get(pkey)
            if src is not None:
                if float(src["price"]) <= 0:
                    zero_rows.append({
                        "product_id": pid,
                        "name": product.get("name"),
                        "sku": sid,
                        "package": package,
                        "pack_key": pkey,
                        "source_name": src.get("source_name"),
                        "source_price": src["price"],
                    })
                    continue

                if not isinstance(current, dict):
                    # commerce_map() should seed catalog SKU, but refuse apply if it did not.
                    conflicts.append({
                        "product_id": pid,
                        "name": product.get("name"),
                        "sku": sid,
                        "reason": "live commerce row missing",
                    })
                    continue

                actions.append({
                    "product_id": pid,
                    "name": product.get("name"),
                    "sku": sid,
                    "package": package,
                    "pack_key": pkey,
                    "source_name": src.get("source_name"),
                    "source_package": src.get("package"),
                    "source_price": float(src["price"]),
                    "current_price": current.get("price"),
                    "current_sale_price": current.get("sale_price"),
                    "current_availability": current.get("availability"),
                    "current_stock_qty": current.get("stock_qty"),
                    "current_enabled": bool(current.get("enabled")),
                })
                product_actions += 1
                continue

            if source_rows:
                source_package_missing.append({
                    "product_id": pid,
                    "name": product.get("name"),
                    "sku": sid,
                    "package": package,
                    "pack_key": pkey,
                    "available_source_packages": [
                        {
                            "package": x.get("package"),
                            "price": x.get("price"),
                            "source_name": x.get("source_name"),
                        }
                        for x in source_rows
                    ],
                })
            else:
                no_source_products.append({
                    "product_id": pid,
                    "name": product.get("name"),
                    "sku": sid,
                    "package": package,
                })

        product_summaries.append({
            "product_id": pid,
            "name": product.get("name"),
            "sku_count": len(pskus),
            "missing_price_sku": product_missing,
            "approved_restore_sku": product_actions,
            "source_rows": len(source_rows),
        })

    no_source_product_ids = sorted({x["product_id"] for x in no_source_products})
    source_package_missing_ids = sorted({x["product_id"] for x in source_package_missing})
    restore_product_ids = sorted({x["product_id"] for x in actions})

    return {
        "source_file": source.get("source_file"),
        "source_date": source.get("source_date"),
        "runtime_products": len(runtime.get("products") or []),
        "runtime_skus": len(runtime.get("skus") or []),
        "restore_actions": actions,
        "restore_product_ids": restore_product_ids,
        "zero_source_price": zero_rows,
        "product_not_in_source": no_source_products,
        "product_not_in_source_ids": no_source_product_ids,
        "source_package_missing": source_package_missing,
        "source_package_missing_ids": source_package_missing_ids,
        "existing_priced": existing_priced,
        "conflicts": conflicts,
        "product_summaries": product_summaries,
    }


def backup_db(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(src))
    try:
        target = sqlite3.connect(str(dst))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def apply_plan(plan: dict) -> dict:
    if plan["conflicts"]:
        raise RuntimeError(
            f"restore blocked: {len(plan['conflicts'])} conflict(s); no writes"
        )

    # Full second preflight immediately before write.
    current_plan = build_plan()
    if current_plan["conflicts"]:
        raise RuntimeError("production state changed; conflicts appeared")
    expected = {
        (x["sku"], float(x["source_price"]))
        for x in plan["restore_actions"]
    }
    current = {
        (x["sku"], float(x["source_price"]))
        for x in current_plan["restore_actions"]
    }
    if expected != current:
        raise RuntimeError("production state changed between dry-run and apply")

    actions = current_plan["restore_actions"]
    if not actions:
        return {
            "status": "NOOP",
            "updated": 0,
            "backup_dir": None,
        }

    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"storefront-approved-price-restore-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_file = backup_dir / Path(DB_PATH).name
    backup_db(Path(DB_PATH), backup_file)

    before = db_snapshot()
    target_keys = {x["sku"] for x in actions}

    try:
        with connect() as con:
            ts = now()
            con.execute("BEGIN IMMEDIATE")
            try:
                for row in actions:
                    live = con.execute(
                        "SELECT sku,price,sale_price,availability,stock_qty,enabled "
                        "FROM sku_commerce WHERE sku=?",
                        (row["sku"],),
                    ).fetchone()
                    if not live:
                        raise RuntimeError(f"missing live commerce row: {row['sku']}")
                    live = dict(live)
                    if effective_price(live) is not None:
                        raise RuntimeError(
                            f"refuse overwrite already-priced SKU: {row['sku']}"
                        )
                    con.execute(
                        "UPDATE sku_commerce "
                        "SET price=?,availability='in_stock',stock_qty=NULL,enabled=1,updated_at=? "
                        "WHERE sku=?",
                        (row["source_price"], ts, row["sku"]),
                    )
                con.commit()
            except Exception:
                con.rollback()
                raise

        after = db_snapshot()
        if set(before) != set(after):
            raise RuntimeError("sku_commerce key set changed")

        errors = []
        for key, prev in before.items():
            cur = after[key]
            if key not in target_keys:
                if cur != prev:
                    errors.append(f"non-target commerce row changed: {key}")
                continue

            action = next(x for x in actions if x["sku"] == key)
            if float(cur.get("price")) != float(action["source_price"]):
                errors.append(f"price mismatch: {key}")
            if cur.get("sale_price") != prev.get("sale_price"):
                errors.append(f"sale_price changed: {key}")
            if cur.get("availability") != "in_stock":
                errors.append(f"availability not in_stock: {key}")
            if cur.get("stock_qty") is not None:
                errors.append(f"stock_qty not NULL: {key}")
            if not bool(cur.get("enabled")):
                errors.append(f"SKU not enabled: {key}")

        if errors:
            raise RuntimeError("\n".join(errors[:100]))

    except Exception:
        backup_db(backup_file, Path(DB_PATH))
        print("AUTO ROLLBACK:", backup_dir)
        print("AUTO ROLLBACK RESULT: PASS")
        raise

    return {
        "status": "PASS",
        "updated": len(actions),
        "updated_products": len({x["product_id"] for x in actions}),
        "backup_dir": str(backup_dir),
        "already_priced_untouched": len(before) - len(actions),
    }


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"storefront-approved-price-restore-{stamp()}.json"
    path.write_text(
        json.dumps(
            {"mode": mode, "plan": plan, "apply": result},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = build_plan()
    result = apply_plan(plan) if args.apply_safe else None
    report = write_report(plan, result, "APPLY_SAFE" if args.apply_safe else "DRY_RUN")

    print("BB610 STOREFRONT APPROVED PRICE RESTORE")
    print("MODE:", "APPLY_SAFE" if args.apply_safe else "DRY_RUN")
    print("SOURCE:", plan["source_file"], "|", plan["source_date"])
    print("RUNTIME PRODUCTS:", plan["runtime_products"])
    print("RUNTIME SKU:", plan["runtime_skus"])
    print("APPROVED RESTORE SKU:", len(plan["restore_actions"]))
    print("APPROVED RESTORE PRODUCTS:", len(plan["restore_product_ids"]))
    print("ZERO SOURCE PRICE:", len(plan["zero_source_price"]))
    print("SOURCE PACKAGE MISSING:", len(plan["source_package_missing"]))
    print("PRODUCT NOT IN SOURCE:", len(plan["product_not_in_source"]))
    print("CONFLICTS:", len(plan["conflicts"]))
    print()

    if plan["restore_actions"]:
        print("=== A: PRICE EXISTS IN APPROVED SOURCE ===")
        for row in plan["restore_actions"]:
            print(
                "RESTORE:",
                row["product_id"],
                "|", row["package"],
                "|", row["sku"],
                "|", row["source_price"],
                "| source:", row["source_name"],
            )
        print()

    if plan["zero_source_price"]:
        print("=== ZERO PRICE: KEEP UNPRICED ===")
        for row in plan["zero_source_price"]:
            print(
                "ZERO:",
                row["product_id"],
                "|", row["package"],
                "|", row["sku"],
                "| source price=", row["source_price"],
            )
        print()

    if plan["source_package_missing"]:
        print("=== SOURCE PRODUCT EXISTS, PACKAGE ABSENT ===")
        for row in plan["source_package_missing"]:
            print(
                "NO PACKAGE:",
                row["product_id"],
                "|", row["package"],
                "|", row["sku"],
            )
        print()

    if plan["product_not_in_source"]:
        print("=== B: PRODUCT/PACKAGE NOT IN APPROVED SOURCE ===")
        for row in plan["product_not_in_source"]:
            print(
                "NO SOURCE:",
                row["product_id"],
                "|", row["package"],
                "|", row["sku"],
            )
        print()

    if plan["conflicts"]:
        print("=== BLOCKING CONFLICTS ===")
        for row in plan["conflicts"]:
            print("BLOCKED:", row)
        print()

    if result:
        print("RESULT:", result["status"])
        print("UPDATED SKU:", result["updated"])
        print("UPDATED PRODUCTS:", result.get("updated_products", 0))
        print("BACKUP:", result.get("backup_dir"))
    else:
        print("RESULT:", "PASS (DRY_RUN)" if not plan["conflicts"] else "BLOCKED")

    print("REPORT:", report)
    return 2 if plan["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
