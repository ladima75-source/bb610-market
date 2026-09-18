from __future__ import annotations

"""Bind only the two verified legacy Plantlogic commerce identities to V3 drafts.

This tool does not create commerce rows and never changes price, sale price,
stock, availability or enabled state. It writes only product_cards_v3/
commerce_map.json after proving that the exact legacy SKU already exists in
live sku_commerce. A legacy catalog parent is optional because storefront
runtime resolves commercial state directly by exact sku_commerce key.
"""

import argparse
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.catalog_provider import load_catalog
from backend.db import connect
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

TARGETS = {
    "plantlogic-25l-round-new-1308125": {
        "product_id": "prd_pl_1308125",
        "legacy_product_key": "plantlogic-25-round-1308125",
        "legacy_sku_key": "BB610-PLT-1308125-EA",
    },
    "plantlogic-40l-round-u-grooves-1308041": {
        "product_id": "prd_pl_1308041",
        "legacy_product_key": "plantlogic-40-round-ugroove-1308041",
        "legacy_sku_key": "BB610-PLT-1308041-EA",
    },
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def raw_live_commerce() -> dict[str, dict]:
    with connect() as con:
        rows = con.execute(
            "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at "
            "FROM sku_commerce"
        ).fetchall()
    out: dict[str, dict] = {}
    for row in rows:
        item = dict(row)
        item["enabled"] = bool(item.get("enabled"))
        item["effective_price"] = (
            item.get("sale_price")
            if item.get("sale_price") is not None
            else item.get("price")
        )
        out[str(item.get("sku") or "")] = item
    return out


def legacy_catalog_index() -> tuple[dict[str, dict], dict[str, list[dict]], dict[str, set[str]]]:
    catalog = load_catalog()
    products = {
        str(x.get("id") or ""): x
        for x in (catalog.get("products") or [])
        if isinstance(x, dict) and x.get("id")
    }
    skus: dict[str, list[dict]] = {}
    sku_parents: dict[str, set[str]] = {}
    for row in catalog.get("skus") or []:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("product_id") or "").strip()
        key = str(row.get("id") or row.get("sku") or "").strip()
        if pid:
            skus.setdefault(pid, []).append(row)
        if pid and key:
            sku_parents.setdefault(key, set()).add(pid)
    return products, skus, sku_parents


def mapping_index() -> dict[str, dict]:
    return {
        str(x.get("product_id") or ""): x
        for x in (pcv3.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }


def build_plan() -> dict:
    live = raw_live_commerce()
    catalog_products, catalog_skus, sku_parents = legacy_catalog_index()
    mappings = mapping_index()
    actions = []
    verified = []

    for slug, spec in TARGETS.items():
        pid = spec["product_id"]
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f"{slug}: Product Card v3 missing")
        if str(card.get("slug") or "") != slug:
            raise RuntimeError(f"{slug}: Product Card slug mismatch")
        if bool(card.get("enabled")):
            raise RuntimeError(f"{slug}: card is enabled; refusing legacy binding change")

        skus = [
            x for x in ((card.get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict) and x.get("enabled") is not False
        ]
        if len(skus) != 1:
            raise RuntimeError(f"{slug}: expected exactly one enabled V3 SKU")
        sid = str(skus[0].get("sku_id") or "").strip()
        if not sid:
            raise RuntimeError(f"{slug}: V3 sku_id missing")

        key = spec["legacy_sku_key"]
        if not isinstance(live.get(key), dict):
            raise RuntimeError(f"{slug}: live sku_commerce row missing for exact SKU {key}")

        parents = sorted(sku_parents.get(key) or [])
        if len(parents) > 1:
            raise RuntimeError(
                f"{slug}: exact legacy SKU {key} belongs to multiple catalog parents: {parents}"
            )
        actual_parent = parents[0] if parents else ""

        desired = {
            "product_id": pid,
            "existing_product_key": actual_parent,
            "skus": [
                {
                    "sku_id": sid,
                    "existing_commerce_sku_key": key,
                }
            ],
        }

        for other_pid, other in mappings.items():
            if other_pid == pid or not isinstance(other, dict):
                continue
            other_parent = str(other.get("existing_product_key") or "").strip()
            other_keys = {
                str(x.get("existing_commerce_sku_key") or "").strip()
                for x in (other.get("skus") or [])
                if isinstance(x, dict)
            }
            if key in other_keys or (actual_parent and other_parent == actual_parent):
                raise RuntimeError(
                    f"{slug}: verified legacy identity is already mapped to {other_pid}"
                )

        current = mappings.get(pid)
        if current is None:
            action = "CREATE_MAPPING"
        else:
            current_links = {
                str(x.get("sku_id") or ""): str(x.get("existing_commerce_sku_key") or "").strip()
                for x in (current.get("skus") or [])
                if isinstance(x, dict) and x.get("sku_id")
            }
            if current_links.get(sid) != key:
                raise RuntimeError(
                    f"{slug}: existing commerce mapping conflicts with exact legacy SKU {key}"
                )
            # Preserve an already-established parent identity even when the
            # current static catalog no longer contains that parent.
            desired = deepcopy(current)
            action = "UNCHANGED"

        actions.append({
            "action": action,
            "slug": slug,
            "product_id": pid,
            "desired": desired,
        })
        verified.append({
            "slug": slug,
            "legacy_product_key": actual_parent,
            "legacy_product_hint": spec["legacy_product_key"],
            "catalog_parent_found": bool(actual_parent),
            "legacy_sku_key": key,
            "price": live[key].get("price"),
            "sale_price": live[key].get("sale_price"),
            "availability": live[key].get("availability"),
            "stock_qty": live[key].get("stock_qty"),
            "enabled": bool(live[key].get("enabled")),
        })

    return {
        "actions": actions,
        "create": sum(1 for x in actions if x["action"] == "CREATE_MAPPING"),
        "unchanged": sum(1 for x in actions if x["action"] == "UNCHANGED"),
        "verified": verified,
    }


def backup_map(ts: str) -> Path:
    base = BACKUP_ROOT / f"plantlogic-legacy-commerce-{ts}"
    base.parent.mkdir(parents=True, exist_ok=True)
    dest = base
    n = 2
    while dest.exists():
        dest = Path(str(base) + f"-{n}")
        n += 1
    dest.mkdir(parents=False, exist_ok=False)
    if pcv3.COMMERCE_MAP.exists():
        shutil.copy2(pcv3.COMMERCE_MAP, dest / "commerce_map.json")
    return dest


def restore_map(backup: Path) -> None:
    saved = backup / "commerce_map.json"
    if saved.exists():
        shutil.copy2(saved, pcv3.COMMERCE_MAP)
    elif pcv3.COMMERCE_MAP.exists():
        pcv3.COMMERCE_MAP.unlink()


def apply_plan(plan: dict) -> dict:
    before_db = _snapshot_tables()
    live_before = deepcopy(raw_live_commerce())
    backup = backup_map(stamp())

    try:
        cmap = pcv3.commerce_map()
        rows = [
            deepcopy(x)
            for x in (cmap.get("products") or [])
            if isinstance(x, dict)
        ]
        by_pid = {str(x.get("product_id") or ""): i for i, x in enumerate(rows)}

        for action in plan["actions"]:
            if action["action"] != "CREATE_MAPPING":
                continue
            pid = action["product_id"]
            if pid in by_pid:
                raise RuntimeError(f"{pid}: mapping appeared concurrently")
            by_pid[pid] = len(rows)
            rows.append(deepcopy(action["desired"]))

        if plan["create"]:
            pcv3._save(
                pcv3.COMMERCE_MAP,
                {
                    "schema_version": cmap.get("schema_version") or "1.0",
                    "products": rows,
                },
            )

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce/database changed during legacy mapping bind")
        if raw_live_commerce() != live_before:
            raise RuntimeError("sku_commerce values changed during legacy mapping bind")

        after = mapping_index()
        for action in plan["actions"]:
            if after.get(action["product_id"]) != action["desired"]:
                raise RuntimeError(f"{action['slug']}: post-verify mapping mismatch")

        post = build_plan()
        if post["create"]:
            raise RuntimeError("legacy mapping bind is not idempotent")

        return {
            "status": "PASS",
            "created": plan["create"],
            "unchanged": plan["unchanged"],
            "backup": str(backup),
        }
    except Exception:
        restore_map(backup)
        if _snapshot_tables() != before_db:
            raise RuntimeError("rollback restored map but commerce DB changed externally")
        if raw_live_commerce() != live_before:
            raise RuntimeError("rollback restored map but sku_commerce changed externally")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = build_plan()
    print("BB610 PLANTLOGIC VERIFIED LEGACY COMMERCE BIND")
    print("TARGETS:", len(TARGETS))
    print("CREATE MAPPING:", plan["create"])
    print("UNCHANGED:", plan["unchanged"])
    for row in plan["verified"]:
        print(
            "VERIFIED:",
            row["slug"],
            "|", row["legacy_product_key"],
            "|", row["legacy_sku_key"],
            "| price=", row["price"],
            "| availability=", row["availability"],
            "| enabled=", row["enabled"],
        )

    if not args.apply_safe:
        print("RESULT: PASS (DRY_RUN)")
        return 0

    result = apply_plan(plan)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report = REPORT_ROOT / f"plantlogic-legacy-commerce-{stamp()}.json"
    report.write_text(
        json.dumps(
            {
                "plan": {
                    "create": plan["create"],
                    "unchanged": plan["unchanged"],
                    "verified": plan["verified"],
                },
                "result": result,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("RESULT:", result["status"])
    print("MAPPINGS CREATED:", result["created"])
    print("MAPPINGS UNCHANGED:", result["unchanged"])
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
