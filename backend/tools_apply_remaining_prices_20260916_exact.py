from __future__ import annotations

"""Apply the non-Valagro rows from the approved 2026-09-16 price source.

This importer is deliberately conservative. It NEVER auto-applies a fuzzy match.
It reuses the existing Product Card v3 alias model, but only accepts pair_score
>= 900. In tools_apply_pcv3_prices_20260916.py, scores >= 900 can only come
from exact alias equality or deterministic alias containment; SequenceMatcher /
Jaccard / formula similarity cannot reach 900.

Safety:
- approved source must contain exactly 195 rows;
- the 49 Valagro/Syngenta rows are excluded (already completed separately);
- remaining source scope must be exactly 146 rows;
- package identity must match exactly after unit normalization;
- one source row must resolve to one unique current active V3 SKU;
- ambiguous/unmatched/missing-commerce rows are reported and NOT written;
- writes are limited to sku_commerce: price, availability=in_stock,
  stock_qty=NULL and enabled=1 for positive-price exact matches;
- sale_price is protected;
- Product Card v3 content/SKU/media/mapping are never modified;
- SQLite backup + transaction + post-verify + automatic restore on failure;
- rerunnable/idempotent.
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import tools_apply_pcv3_prices_20260916 as base
from backend import tools_apply_valagro_prices_20260916_runtime as valagro

SOURCE = ROOT / "data" / "catalog_sources" / "bb610_market_prices_2026-09-16.json"
BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_ALL_ROWS = 195
EXPECTED_VALAGRO_ROWS = 49
EXPECTED_REMAINING_ROWS = 146
MIN_EXACT_SCORE = 900.0


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_source_rows() -> list[dict]:
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if doc.get("source_file") != "цены_сайт_Market_160926.xlsx":
        raise RuntimeError(f"unexpected source_file: {doc.get('source_file')!r}")
    if doc.get("source_date") != "2026-09-16":
        raise RuntimeError(f"unexpected source_date: {doc.get('source_date')!r}")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ALL_ROWS:
        raise RuntimeError(f"price manifest must contain {EXPECTED_ALL_ROWS} rows; got {len(rows or [])}")

    remaining: list[dict] = []
    excluded = 0
    for row_no, row in enumerate(rows, start=2):
        if not isinstance(row, dict):
            raise RuntimeError(f"source row {row_no} is not an object")
        if valagro.source_slug(row.get("source_name")):
            excluded += 1
            continue
        price = row.get("price")
        if not isinstance(price, (int, float)) or price < 0:
            raise RuntimeError(f"row {row_no}: invalid price {price!r}")
        package = str(row.get("package") or "").strip()
        pkey = base.pack_key(package)
        if not pkey:
            raise RuntimeError(f"row {row_no}: empty package")
        remaining.append({
            "source_row": row_no,
            "source_name": str(row.get("source_name") or "").strip(),
            "package": package,
            "pack_key": pkey,
            "price": float(price),
        })

    if excluded != EXPECTED_VALAGRO_ROWS:
        raise RuntimeError(f"expected {EXPECTED_VALAGRO_ROWS} excluded Valagro rows; got {excluded}")
    if len(remaining) != EXPECTED_REMAINING_ROWS:
        raise RuntimeError(f"expected {EXPECTED_REMAINING_ROWS} remaining rows; got {len(remaining)}")
    return remaining


def classify() -> dict:
    from backend.db import DB_PATH, connect

    source_rows = load_source_rows()
    targets = base.load_targets()
    by_pack: dict[str, list[dict]] = {}
    for target in targets:
        by_pack.setdefault(str(target.get("pack_key") or ""), []).append(target)

    with connect() as con:
        commerce = {
            str(row["sku"]): dict(row)
            for row in con.execute(
                "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce"
            ).fetchall()
        }

    actions: list[dict] = []
    unmatched: list[dict] = []
    ambiguous: list[dict] = []
    missing_commerce: list[dict] = []
    zero_price: list[dict] = []
    seen_keys: set[str] = set()

    for src in source_rows:
        candidates: list[tuple[float, dict]] = []
        for target in by_pack.get(src["pack_key"], []):
            score = base.pair_score(src["source_name"], target.get("aliases") or set())
            if score >= MIN_EXACT_SCORE:
                candidates.append((score, target))
        candidates.sort(key=lambda x: (x[0], x[1].get("title") or ""), reverse=True)

        if not candidates:
            unmatched.append(deepcopy(src))
            continue

        top_score = candidates[0][0]
        top = [x for x in candidates if abs(x[0] - top_score) < 0.0001]
        unique_products = {str(x[1].get("product_id") or "") for x in top}
        unique_commerce = {str(x[1].get("commerce_key") or "") for x in top}
        if len(top) != 1 or len(unique_products) != 1 or len(unique_commerce) != 1:
            ambiguous.append({
                **deepcopy(src),
                "candidates": [
                    {
                        "score": score,
                        "product_id": t.get("product_id"),
                        "title": t.get("title"),
                        "package": t.get("package"),
                        "commerce_key": t.get("commerce_key"),
                    }
                    for score, t in candidates[:8]
                ],
            })
            continue

        score, target = top[0]
        commerce_key = str(target.get("commerce_key") or "").strip()
        if not commerce_key or commerce_key not in commerce:
            missing_commerce.append({
                **deepcopy(src),
                "score": score,
                "product_id": target.get("product_id"),
                "title": target.get("title"),
                "sku_id": target.get("sku_id"),
                "commerce_key": commerce_key,
            })
            continue
        if commerce_key in seen_keys:
            raise RuntimeError(f"duplicate exact target commerce key: {commerce_key}")
        seen_keys.add(commerce_key)

        row = {
            **deepcopy(src),
            "score": round(score, 2),
            "product_id": target.get("product_id"),
            "title": target.get("title"),
            "sku_id": target.get("sku_id"),
            "sku_code": target.get("sku_code"),
            "commerce_key": commerce_key,
            "before": deepcopy(commerce[commerce_key]),
        }
        if src["price"] <= 0:
            zero_price.append(row)
        else:
            actions.append(row)

    return {
        "db_path": str(DB_PATH),
        "source_rows": len(source_rows),
        "active_v3_targets": len(targets),
        "actions": actions,
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        "missing_commerce": missing_commerce,
        "zero_price": zero_price,
        "matched_by_product": dict(Counter(x["title"] for x in actions)),
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
    from backend.db import DB_PATH, connect

    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"remaining-prices-exact-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_file = backup_dir / Path(DB_PATH).name
    backup_db(Path(DB_PATH), backup_file)

    keys = [x["commerce_key"] for x in plan["actions"]]
    before = {x["commerce_key"]: deepcopy(x["before"]) for x in plan["actions"]}
    try:
        with connect() as con:
            ts = now()
            con.execute("BEGIN IMMEDIATE")
            try:
                for row in plan["actions"]:
                    con.execute(
                        "UPDATE sku_commerce SET price=?, availability='in_stock', stock_qty=NULL, enabled=1, updated_at=? WHERE sku=?",
                        (row["price"], ts, row["commerce_key"]),
                    )
                con.commit()
            except Exception:
                con.rollback()
                raise

        with connect() as con:
            placeholders = ",".join("?" for _ in keys)
            after = {
                str(row["sku"]): dict(row)
                for row in con.execute(
                    f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
                    keys,
                ).fetchall()
            } if keys else {}

        errors: list[str] = []
        for row in plan["actions"]:
            key = row["commerce_key"]
            old = before.get(key)
            cur = after.get(key)
            if not old or not cur:
                errors.append(f"missing commerce snapshot: {key}")
                continue
            if float(cur.get("price")) != float(row["price"]):
                errors.append(f"price mismatch: {key}")
            if cur.get("availability") != "in_stock":
                errors.append(f"availability mismatch: {key}")
            if cur.get("stock_qty") is not None:
                errors.append(f"stock_qty not NULL: {key}")
            if not bool(cur.get("enabled")):
                errors.append(f"enabled not active: {key}")
            if cur.get("sale_price") != old.get("sale_price"):
                errors.append(f"sale_price changed: {key}")
        if errors:
            raise RuntimeError("post-verify failed:\n" + "\n".join(errors[:100]))
    except Exception:
        src = sqlite3.connect(str(backup_file))
        try:
            dst = sqlite3.connect(str(DB_PATH))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        raise

    return {
        "status": "PASS",
        "backup_dir": str(backup_dir),
        "updated": len(plan["actions"]),
        "sale_price_unchanged": True,
        "content_changed": False,
        "mapping_changed": False,
    }


def print_plan(plan: dict, *, mode: str) -> None:
    print("BB610 REMAINING CATALOGUE EXACT PRICE IMPORT")
    print("MODE:", mode)
    print("SOURCE REMAINING ROWS:", plan["source_rows"])
    print("ACTIVE V3 TARGETS:", plan["active_v3_targets"])
    print("EXACT POSITIVE MATCHES:", len(plan["actions"]))
    print("UNMATCHED SOURCE:", len(plan["unmatched"]))
    print("AMBIGUOUS SOURCE:", len(plan["ambiguous"]))
    print("MISSING COMMERCE:", len(plan["missing_commerce"]))
    print("ZERO PRICE SKIPPED:", len(plan["zero_price"]))
    print("AUTO MATCH POLICY: pair_score >= 900 only (exact equality/containment; no fuzzy auto-apply)")
    print("WRITE POLICY: price + in_stock + stock_qty NULL + enabled=1; sale_price unchanged")

    for label, rows in (
        ("UNMATCHED", plan["unmatched"]),
        ("AMBIGUOUS", plan["ambiguous"]),
        ("MISSING_COMMERCE", plan["missing_commerce"]),
        ("ZERO", plan["zero_price"]),
    ):
        for row in rows:
            print(f"{label}: row={row.get('source_row')} | {row.get('source_name')} | {row.get('package')} | price={row.get('price')}")
            if label == "AMBIGUOUS":
                for c in row.get("candidates") or []:
                    print("   CANDIDATE:", c)


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely apply exact non-Valagro prices from the approved 2026-09-16 source")
    parser.add_argument("--apply-safe", action="store_true")
    args = parser.parse_args()

    plan = classify()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_ROOT / f"remaining-prices-exact-{stamp()}.json"
    print_plan(plan, mode="APPLY_SAFE" if args.apply_safe else "DRY_RUN")

    result = None
    if args.apply_safe:
        result = apply_plan(plan)
        print("RESULT:", result["status"])
        print("UPDATED:", result["updated"])
        print("BACKUP:", result["backup_dir"])

    report = {
        "mode": "APPLY_SAFE" if args.apply_safe else "DRY_RUN",
        **plan,
        "result": result,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("REPORT:", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
