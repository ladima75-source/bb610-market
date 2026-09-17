from __future__ import annotations

"""Activate sale state for the canonical Valagro/Syngenta SKU matrix.

Safety contract:
- source of truth is the approved 2026-09-16 price manifest;
- only the 12 approved Valagro/Syngenta slugs are in scope;
- all 49 canonical source packages must exist as enabled structural PCV3 SKUs;
- the 48 rows with positive source price must already have the exact source price
  in sku_commerce and availability=in_stock before they can be enabled;
- the single zero-price row (MASTER 15-5-30 / 20 g) is forced disabled;
- only sku_commerce.enabled is changed; price, sale_price, availability,
  stock_qty and all Product Card v3/content/media/mapping files are protected;
- SQLite backup + transaction + post-verify + automatic restore on verify failure;
- idempotent and safe to rerun.
"""

import argparse
import json
import sqlite3
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import tools_apply_valagro_prices_20260916_runtime as prices

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"
BATCH = "BB610 Valagro/Syngenta commerce activation 2026-09-17"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime():
    from backend.db import DB_PATH, connect
    from backend.services import product_cards_v3 as pcv3
    return DB_PATH, connect, pcv3


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


def expected_policy() -> dict:
    src = prices.load_source()
    rows = src["target_rows"]
    positive = [deepcopy(x) for x in rows if float(x["price"]) > 0]
    zero = [deepcopy(x) for x in rows if float(x["price"]) <= 0]
    if len(rows) != 49:
        raise RuntimeError(f"expected 49 canonical rows; got {len(rows)}")
    if len(positive) != 48:
        raise RuntimeError(f"expected 48 positive-price rows; got {len(positive)}")
    if len(zero) != 1:
        raise RuntimeError(f"expected exactly one zero-price row; got {len(zero)}")
    z = zero[0]
    if z["slug"] != "master-15-5-30" or z["pack_key"] != "20g":
        raise RuntimeError(f"unexpected zero-price row: {z['slug']}/{z['pack_key']}")
    return {"source": src, "positive": positive, "zero": zero}


def build_plan() -> dict:
    policy = expected_policy()
    DB_PATH, connect, pcv3 = _runtime()

    cards_by_slug: dict[str, dict] = {}
    for summary in pcv3.list_cards():
        pid = str(summary.get("product_id") or "").strip()
        card = pcv3.get(pid) if pid else None
        if not isinstance(card, dict):
            continue
        slug = str(card.get("slug") or "").strip().lower()
        if slug in prices.ALLOWED_SET:
            if slug in cards_by_slug:
                raise RuntimeError(f"duplicate V3 slug: {slug}")
            cards_by_slug[slug] = card

    missing = [slug for slug in prices.ALLOWED_SLUGS if slug not in cards_by_slug]
    if missing:
        raise RuntimeError("missing V3 cards: " + ", ".join(missing))

    mapping_by_pid = {
        str(row.get("product_id") or ""): row
        for row in (pcv3.commerce_map().get("products") or [])
        if isinstance(row, dict) and row.get("product_id")
    }

    structural: dict[tuple[str, str], dict] = {}
    total_active = 0
    for slug in prices.ALLOWED_SLUGS:
        card = cards_by_slug[slug]
        pid = str(card.get("product_id") or "")
        mapping = mapping_by_pid.get(pid)
        if not isinstance(mapping, dict):
            raise RuntimeError(f"{slug}: product commerce mapping missing")
        links = {
            str(x.get("sku_id") or ""): str(x.get("existing_commerce_sku_key") or "").strip()
            for x in (mapping.get("skus") or [])
            if isinstance(x, dict) and x.get("sku_id")
        }
        for sku in ((card.get("sku_media") or {}).get("skus") or []):
            if not isinstance(sku, dict) or not sku.get("enabled", True):
                continue
            sid = str(sku.get("sku_id") or "").strip()
            package = str(sku.get("package") or sku.get("label") or "").strip()
            pkey = prices.pack_key(package)
            if not sid or not pkey:
                raise RuntimeError(f"{slug}: invalid active structural SKU")
            key = (slug, pkey)
            if key in structural:
                raise RuntimeError(f"duplicate active structural package: {slug}/{pkey}")
            commerce_key = links.get(sid, "")
            if not commerce_key:
                raise RuntimeError(f"{slug}/{pkey}: commerce binding missing")
            structural[key] = {
                "slug": slug,
                "product_id": pid,
                "sku_id": sid,
                "package": package,
                "pack_key": pkey,
                "commerce_key": commerce_key,
            }
            total_active += 1

    expected_keys = {(x["slug"], x["pack_key"]) for x in policy["source"]["target_rows"]}
    actual_keys = set(structural)
    if total_active != 49 or actual_keys != expected_keys:
        missing_keys = sorted(expected_keys - actual_keys)
        extra_keys = sorted(actual_keys - expected_keys)
        raise RuntimeError(
            f"canonical structural matrix mismatch: active={total_active}; "
            f"missing={missing_keys}; extra={extra_keys}"
        )

    with connect() as con:
        db_rows = {
            str(row["sku"]): dict(row)
            for row in con.execute(
                "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce"
            ).fetchall()
        }

    actions: list[dict] = []
    protected_before: dict[str, dict] = {}
    errors: list[str] = []
    positive_keys = {(x["slug"], x["pack_key"]): x for x in policy["positive"]}
    zero_keys = {(x["slug"], x["pack_key"]): x for x in policy["zero"]}

    for identity, meta in structural.items():
        commerce_key = meta["commerce_key"]
        live = db_rows.get(commerce_key)
        if not live:
            errors.append(f"{meta['slug']}/{meta['pack_key']}: commerce row missing {commerce_key}")
            continue
        protected_before[commerce_key] = deepcopy(live)

        if identity in positive_keys:
            src = positive_keys[identity]
            current_price = live.get("price")
            if current_price is None or float(current_price) != float(src["price"]):
                errors.append(
                    f"{meta['slug']}/{meta['pack_key']}: price {current_price!r} != source {src['price']!r}"
                )
                continue
            if str(live.get("availability") or "") != "in_stock":
                errors.append(
                    f"{meta['slug']}/{meta['pack_key']}: availability {live.get('availability')!r} != in_stock"
                )
                continue
            desired = True
            source_price = float(src["price"])
        elif identity in zero_keys:
            desired = False
            source_price = float(zero_keys[identity]["price"])
        else:
            errors.append(f"unexpected canonical identity: {identity}")
            continue

        actions.append({
            **meta,
            "source_price": source_price,
            "enabled_before": bool(live.get("enabled")),
            "enabled_after": desired,
        })

    if errors:
        raise RuntimeError("VALAGRO ACTIVATION PREFLIGHT FAILED:\n- " + "\n- ".join(errors[:100]))
    if len(actions) != 49:
        raise RuntimeError(f"expected 49 activation actions; got {len(actions)}")
    if sum(1 for x in actions if x["enabled_after"]) != 48:
        raise RuntimeError("activation plan must enable exactly 48 SKU")
    if sum(1 for x in actions if not x["enabled_after"]) != 1:
        raise RuntimeError("activation plan must keep exactly one SKU disabled")

    return {
        "batch": BATCH,
        "source_file": policy["source"].get("source_file"),
        "source_date": policy["source"].get("source_date"),
        "db_path": str(DB_PATH),
        "actions": actions,
        "protected_before": protected_before,
    }


def apply_plan(plan: dict) -> dict:
    DB_PATH, connect, _pcv3 = _runtime()
    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"valagro-commerce-activate-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_file = backup_dir / Path(DB_PATH).name
    backup_db(Path(DB_PATH), backup_file)

    ts = now()
    try:
        with connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                for row in plan["actions"]:
                    con.execute(
                        "UPDATE sku_commerce SET enabled=?, updated_at=? WHERE sku=?",
                        (1 if row["enabled_after"] else 0, ts, row["commerce_key"]),
                    )
                con.commit()
            except Exception:
                con.rollback()
                raise

        with connect() as con:
            keys = [x["commerce_key"] for x in plan["actions"]]
            placeholders = ",".join("?" for _ in keys)
            after = {
                str(row["sku"]): dict(row)
                for row in con.execute(
                    f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
                    keys,
                ).fetchall()
            }

        errors: list[str] = []
        protected_fields = ("price", "sale_price", "availability", "stock_qty")
        for action in plan["actions"]:
            key = action["commerce_key"]
            before = plan["protected_before"].get(key)
            current = after.get(key)
            if not before or not current:
                errors.append(f"missing verification snapshot: {key}")
                continue
            if bool(current.get("enabled")) != bool(action["enabled_after"]):
                errors.append(f"enabled mismatch: {key}")
            for field in protected_fields:
                if current.get(field) != before.get(field):
                    errors.append(f"protected field changed: {key}.{field}")

        if errors:
            raise RuntimeError("post-verify failed:\n- " + "\n- ".join(errors[:100]))
    except Exception:
        restore_db(backup_file, Path(DB_PATH))
        raise

    return {
        "status": "PASS",
        "backup_dir": str(backup_dir),
        "enabled": sum(1 for x in plan["actions"] if x["enabled_after"]),
        "disabled": sum(1 for x in plan["actions"] if not x["enabled_after"]),
        "changed_to_enabled": sum(1 for x in plan["actions"] if x["enabled_after"] and not x["enabled_before"]),
        "changed_to_disabled": sum(1 for x in plan["actions"] if not x["enabled_after"] and x["enabled_before"]),
    }


def print_plan(plan: dict, result: dict | None = None) -> None:
    print("BB610 VALAGRO/SYNGENTA COMMERCE ACTIVATION")
    print("MODE:", "APPLY_SAFE" if result is not None else "DRY_RUN")
    print("SOURCE:", plan["source_file"])
    print("CANONICAL SKU:", len(plan["actions"]))
    print("SALE ENABLED TARGET:", sum(1 for x in plan["actions"] if x["enabled_after"]))
    print("SALE DISABLED TARGET:", sum(1 for x in plan["actions"] if not x["enabled_after"]))
    for row in plan["actions"]:
        if not row["enabled_after"]:
            print("DISABLED POLICY:", row["slug"], "|", row["package"], "| price", row["source_price"])
    if result is not None:
        for k, v in result.items():
            print(k.upper() + ":", v)


def main() -> int:
    parser = argparse.ArgumentParser(description=BATCH)
    parser.add_argument("--apply-safe", action="store_true")
    args = parser.parse_args()

    plan = build_plan()
    result = apply_plan(plan) if args.apply_safe else None
    print_plan(plan, result)

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_ROOT / f"valagro-commerce-activation-{stamp()}.json"
    report_path.write_text(
        json.dumps(
            {
                "mode": "APPLY_SAFE" if args.apply_safe else "DRY_RUN",
                "batch": BATCH,
                "source_file": plan["source_file"],
                "source_date": plan["source_date"],
                "actions": plan["actions"],
                "result": result,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("REPORT:", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
