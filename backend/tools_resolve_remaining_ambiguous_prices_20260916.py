from __future__ import annotations

"""Resolve the eight remaining ambiguous 2026-09-16 price rows explicitly.

The broad importer intentionally refuses fuzzy/tied matches. This follow-up keeps
that safety rule and resolves only eight reviewed source rows by stable product
title identity + exact package identity. Runtime product IDs are deliberately
not hard-coded because migrated cards can be deployment-specific.

Writes are limited to sku_commerce price, availability=in_stock, stock_qty=NULL
and enabled=1. sale_price, Product Card v3 content/SKU/media and mappings are
protected. SQLite is backed up before apply and restored if post-verify fails.
"""

import argparse
import json
import sqlite3
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import tools_apply_pcv3_prices_20260916 as base
from backend import tools_apply_remaining_prices_20260916_exact as remaining

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

RESOLUTIONS: dict[int, dict[str, Any]] = {
    14: {"target_title": "MASTER 18-18-18", "name_fragment": "18-18-18", "package": "250 г", "price": 177.0},
    15: {"target_title": "MASTER 18-18-18", "name_fragment": "18-18-18", "package": "1 кг", "price": 399.0},
    16: {"target_title": "MASTER 17-6-18", "name_fragment": "17-6-18", "package": "250 г", "price": 154.0},
    17: {"target_title": "MASTER 17-6-18", "name_fragment": "17-6-18", "package": "1 кг", "price": 364.0},
    73: {"target_title": "Osmocote Potassium 12-8-19 (3-4M)", "name_fragment": "12-8-19", "package": "200 г", "price": 154.0},
    74: {"target_title": "Osmocote Potassium 12-8-19 (3-4M)", "name_fragment": "12-8-19", "package": "1 кг", "price": 637.0},
    77: {"target_title": "Osmocote Landscape 16-9-12 (3-4M)", "name_fragment": "16-9-12", "package": "200 г", "price": 149.0},
    78: {"target_title": "Osmocote Landscape 16-9-12 (3-4M)", "name_fragment": "16-9-12", "package": "1 кг", "price": 611.0},
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_contract() -> list[dict]:
    """Validate only the approved price source; safe for clean CI checkout."""
    src_by_row = {int(x["source_row"]): x for x in remaining.load_source_rows()}
    if set(RESOLUTIONS) != {14, 15, 16, 17, 73, 74, 77, 78}:
        raise RuntimeError("manual resolution registry must contain exactly the eight reviewed rows")

    out: list[dict] = []
    for row_no, spec in sorted(RESOLUTIONS.items()):
        src = src_by_row.get(row_no)
        if not src:
            raise RuntimeError(f"source row {row_no} is not in remaining scope")
        if spec["name_fragment"] not in str(src.get("source_name") or ""):
            raise RuntimeError(f"row {row_no}: source identity drift: {src.get('source_name')!r}")
        if base.pack_key(src.get("package")) != base.pack_key(spec["package"]):
            raise RuntimeError(f"row {row_no}: package drift: {src.get('package')!r}")
        if float(src.get("price")) != float(spec["price"]):
            raise RuntimeError(f"row {row_no}: price drift: {src.get('price')!r}")
        out.append({**deepcopy(src), "target_title": spec["target_title"]})
    return out


def resolve_targets(contract_rows: list[dict], targets: list[dict] | None = None, *, require_ambiguity: bool = True) -> list[dict]:
    """Resolve reviewed rows against current runtime PCV3 targets.

    In production `require_ambiguity=True` proves that the broad importer still
    sees multiple >=900 candidates and that the reviewed target remains among
    them. CI can unit-test the deterministic title+package resolver with a small
    fixture without requiring runtime-generated cards to exist in Git.
    """
    targets = base.load_targets() if targets is None else targets
    out: list[dict] = []

    for src in contract_rows:
        wanted_title = base.norm(src["target_title"])
        matches = [
            t for t in targets
            if base.norm(t.get("title")) == wanted_title
            and str(t.get("pack_key") or "") == str(src.get("pack_key") or "")
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"row {src['source_row']}: expected one runtime target for {src['target_title']}/{src.get('pack_key')}; got {len(matches)}"
            )
        target = matches[0]
        commerce_key = str(target.get("commerce_key") or "").strip()
        if not commerce_key:
            raise RuntimeError(f"row {src['source_row']}: reviewed target has no commerce binding")

        candidate_product_count = None
        if require_ambiguity:
            candidates: list[tuple[float, dict]] = []
            for t in targets:
                if str(t.get("pack_key") or "") != str(src.get("pack_key") or ""):
                    continue
                score = base.pair_score(src.get("source_name"), t.get("aliases") or set())
                if score >= remaining.MIN_EXACT_SCORE:
                    candidates.append((score, t))
            identities = {
                (str(t.get("product_id") or ""), str(t.get("sku_id") or ""))
                for _score, t in candidates
            }
            target_identity = (str(target.get("product_id") or ""), str(target.get("sku_id") or ""))
            if target_identity not in identities:
                raise RuntimeError(f"row {src['source_row']}: reviewed target no longer appears in exact-candidate set")
            candidate_product_count = len({pid for pid, _sid in identities})
            if candidate_product_count < 2:
                raise RuntimeError(f"row {src['source_row']}: row is no longer ambiguous; review registry before applying")

        out.append({
            **deepcopy(src),
            "product_id": target.get("product_id"),
            "title": target.get("title"),
            "sku_id": target.get("sku_id"),
            "sku_code": target.get("sku_code"),
            "commerce_key": commerce_key,
            "candidate_product_count": candidate_product_count,
        })

    keys = [x["commerce_key"] for x in out]
    if len(keys) != len(set(keys)):
        raise RuntimeError("resolved commerce keys must be unique")
    return out


def build_plan() -> dict:
    from backend.db import DB_PATH, connect

    actions = resolve_targets(source_contract())
    keys = [x["commerce_key"] for x in actions]
    with connect() as con:
        placeholders = ",".join("?" for _ in keys)
        live = {
            str(row["sku"]): dict(row)
            for row in con.execute(
                f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
                keys,
            ).fetchall()
        }
    missing = [key for key in keys if key not in live]
    if missing:
        raise RuntimeError("resolved commerce rows missing: " + ", ".join(missing))
    for row in actions:
        row["before"] = deepcopy(live[row["commerce_key"]])
    return {"db_path": str(DB_PATH), "actions": actions}


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


def restore_db(src_path: Path, dest_path: Path) -> None:
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
    backup_dir = BACKUP_ROOT / f"remaining-prices-manual-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_file = backup_dir / Path(DB_PATH).name
    backup_db(Path(DB_PATH), backup_file)

    try:
        ts = now()
        with connect() as con:
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

        keys = [x["commerce_key"] for x in plan["actions"]]
        with connect() as con:
            placeholders = ",".join("?" for _ in keys)
            after = {
                str(row["sku"]): dict(row)
                for row in con.execute(
                    f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
                    keys,
                ).fetchall()
            }

        errors: list[str] = []
        changed = 0
        for row in plan["actions"]:
            key = row["commerce_key"]
            old = row["before"]
            cur = after.get(key)
            if not cur:
                errors.append(f"missing after snapshot: {key}")
                continue
            if float(cur.get("price")) != float(row["price"]):
                errors.append(f"price mismatch: {key}")
            if cur.get("availability") != "in_stock":
                errors.append(f"availability mismatch: {key}")
            if cur.get("stock_qty") is not None:
                errors.append(f"stock_qty must stay NULL: {key}")
            if not bool(cur.get("enabled")):
                errors.append(f"enabled mismatch: {key}")
            if cur.get("sale_price") != old.get("sale_price"):
                errors.append(f"sale_price changed unexpectedly: {key}")
            if (
                old.get("price") != cur.get("price")
                or old.get("availability") != cur.get("availability")
                or old.get("stock_qty") != cur.get("stock_qty")
                or bool(old.get("enabled")) != bool(cur.get("enabled"))
            ):
                changed += 1

        if errors:
            raise RuntimeError("post-verify failed:\n- " + "\n- ".join(errors))
        return {"status": "PASS", "updated": len(plan["actions"]), "changed": changed, "backup_dir": str(backup_dir)}
    except Exception:
        restore_db(backup_file, Path(DB_PATH))
        raise


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"remaining-prices-manual-{stamp()}.json"
    payload = {
        "mode": mode,
        "source_file": "цены_сайт_Market_160926.xlsx",
        "resolved_rows": len(plan["actions"]),
        "actions": plan["actions"],
        "result": result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def print_plan(plan: dict) -> None:
    print("BB610 REMAINING AMBIGUOUS PRICE RESOLUTION")
    print("SOURCE: цены_сайт_Market_160926.xlsx")
    print(f"RESOLVED ROWS: {len(plan['actions'])}")
    for row in plan["actions"]:
        print(
            f"RESOLVE row={row['source_row']} | {row['source_name']} | {row['package']} | price={row['price']} "
            f"=> {row['title']} | {row['commerce_key']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-safe", action="store_true")
    args = parser.parse_args()

    plan = build_plan()
    print_plan(plan)
    if not args.apply_safe:
        report = write_report(plan, None, "DRY_RUN")
        print("RESULT: PASS (DRY_RUN)")
        print(f"REPORT: {report}")
        return 0

    result = apply_plan(plan)
    report = write_report(plan, result, "APPLY_SAFE")
    print(f"RESULT: {result['status']}")
    print(f"UPDATED: {result['updated']}")
    print(f"CHANGED: {result['changed']}")
    print(f"BACKUP_DIR: {result['backup_dir']}")
    print(f"REPORT: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
