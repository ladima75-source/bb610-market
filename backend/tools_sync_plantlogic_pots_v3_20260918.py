from __future__ import annotations

"""Safely synchronize managed Plantlogic Product Card v3 drafts to the current master.

Rules:
- managed scope comes only from plantlogic_pots_v1_20260918.json;
- creates missing draft cards;
- updates existing Plantlogic cards only while the card is disabled;
- preserves existing media rows and per-SKU primary/gallery links for unchanged sku_id;
- never changes commerce_map, sku_commerce, price, stock, availability or publication;
- blocks on SKU identity conflicts instead of guessing;
- backs up Product Card v3 and rolls back on any post-check failure.
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

from backend import update_plantlogic_pots_v3_20260918 as master
from backend.services import product_cards_v3 as pcv3
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _media_index(card: dict) -> dict[str, dict]:
    return {
        str(x.get("media_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }


def merge_existing(desired: dict, existing: dict) -> dict:
    if str(existing.get("product_id") or "") != str(desired.get("product_id") or ""):
        raise RuntimeError("product_id conflict")
    if str(existing.get("slug") or "") != str(desired.get("slug") or ""):
        raise RuntimeError("slug conflict")
    if bool(existing.get("enabled")):
        raise RuntimeError("existing Plantlogic card is enabled; refusing draft sync")

    content = existing.get("content") or {}
    if str(content.get("brand") or "").strip().lower() != "plantlogic":
        raise RuntimeError("existing card is not a Plantlogic-managed card")

    old_skus = {
        str(x.get("sku_id") or ""): x
        for x in ((existing.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict) and x.get("sku_id")
    }
    old_media = [
        deepcopy(x)
        for x in ((existing.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict)
    ]
    media_ids = {
        str(x.get("media_id") or "")
        for x in old_media
        if x.get("media_id")
    }

    merged = deepcopy(desired)
    merged["sku_media"]["media"] = old_media

    for sku in merged["sku_media"]["skus"]:
        sid = str(sku.get("sku_id") or "")
        old = old_skus.get(sid)
        if not old:
            continue

        old_code = str(old.get("sku_code") or "").strip()
        new_code = str(sku.get("sku_code") or "").strip()
        if old_code and new_code and old_code != new_code:
            raise RuntimeError(f"{sid}: sku_code conflict {old_code} != {new_code}")

        primary = str(old.get("primary_media_id") or "").strip()
        if primary:
            if primary not in media_ids:
                raise RuntimeError(f"{sid}: primary_media_id points to missing media row")
            sku["primary_media_id"] = primary

        gallery = []
        for mid in old.get("gallery_media_ids") or []:
            value = str(mid or "").strip()
            if not value:
                continue
            if value not in media_ids:
                raise RuntimeError(f"{sid}: gallery media points to missing media row {value}")
            if value not in gallery:
                gallery.append(value)
        sku["gallery_media_ids"] = gallery

        # Preserve a deliberate per-SKU disabled state; never auto-enable a SKU
        # merely because the refreshed master contains it.
        if old.get("enabled") is False:
            sku["enabled"] = False

    pcv3.validate(merged)
    return merged


def build_plan() -> dict:
    doc = master.load_manifest()
    if len(doc["products"]) != EXPECTED_PRODUCTS:
        raise RuntimeError("Plantlogic master product count changed")
    if sum(len(x.get("skus") or []) for x in doc["products"]) != EXPECTED_SKUS:
        raise RuntimeError("Plantlogic master SKU count changed")

    index = pcv3.list_cards()
    by_pid = {str(x.get("product_id") or ""): x for x in index}
    by_slug = {str(x.get("slug") or ""): x for x in index}
    managed_ids = {str(x.get("product_id") or "") for x in doc["products"]}
    unmanaged_plantlogic = [
        x for x in index
        if str(x.get("brand") or "").strip().lower() == "plantlogic"
        and str(x.get("product_id") or "") not in managed_ids
    ]
    if unmanaged_plantlogic:
        raise RuntimeError(
            "unmanaged Plantlogic v3 cards exist: "
            + ", ".join(
                f"{x.get('slug')}({x.get('product_id')})"
                for x in unmanaged_plantlogic
            )
        )

    actions = []
    conflicts = []
    for row in doc["products"]:
        desired = master.build_card(row)
        pid = desired["product_id"]
        slug = desired["slug"]

        other = by_slug.get(slug)
        if other and str(other.get("product_id") or "") != pid:
            conflicts.append(f"{slug}: slug belongs to {other.get('product_id')}")
            continue

        summary = by_pid.get(pid)
        if not summary:
            actions.append({
                "action": "CREATE",
                "product_id": pid,
                "slug": slug,
                "card": desired,
            })
            continue

        existing = pcv3.get(pid)
        if not isinstance(existing, dict):
            conflicts.append(f"{pid}: index entry exists but card file is missing")
            continue
        try:
            merged = merge_existing(desired, existing)
        except Exception as exc:
            conflicts.append(f"{slug}: {exc}")
            continue

        if merged == existing:
            action = "UNCHANGED"
        else:
            action = "UPDATE"
        actions.append({
            "action": action,
            "product_id": pid,
            "slug": slug,
            "card": merged,
        })

    if conflicts:
        raise RuntimeError("Plantlogic sync conflicts: " + " | ".join(conflicts))
    if len(actions) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} actions; got {len(actions)}")

    return {
        "actions": actions,
        "create": sum(1 for x in actions if x["action"] == "CREATE"),
        "update": sum(1 for x in actions if x["action"] == "UPDATE"),
        "unchanged": sum(1 for x in actions if x["action"] == "UNCHANGED"),
        "deferred": doc.get("deferred") or [],
    }


def backup_cards(ts: str) -> Path:
    dest = BACKUP_ROOT / f"plantlogic-v3-sync-{ts}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 2
    base = dest
    while dest.exists():
        dest = Path(str(base) + f"-{n}")
        n += 1
    shutil.copytree(pcv3.BASE, dest / "product_cards_v3")
    return dest


def restore_cards(backup: Path) -> None:
    src = backup / "product_cards_v3"
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(src, pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply_plan(plan: dict) -> dict:
    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    all_before = {
        str(x.get("product_id") or ""): pcv3.get(str(x.get("product_id") or ""))
        for x in pcv3.list_cards()
    }

    backup = backup_cards(stamp())
    try:
        for row in plan["actions"]:
            if row["action"] == "CREATE":
                pcv3.create(deepcopy(row["card"]))
            elif row["action"] == "UPDATE":
                pcv3.put(row["product_id"], deepcopy(row["card"]))

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce/database changed during Plantlogic sync")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed during Plantlogic sync")

        targets = {x["product_id"] for x in plan["actions"]}
        for row in plan["actions"]:
            live = pcv3.get(row["product_id"])
            if live != row["card"]:
                raise RuntimeError(f"post-verify mismatch: {row['slug']}")
            if bool(live.get("enabled")):
                raise RuntimeError(f"Plantlogic draft unexpectedly enabled: {row['slug']}")

        for pid, before in all_before.items():
            if pid in targets:
                continue
            if pcv3.get(pid) != before:
                raise RuntimeError(f"non-target card changed: {pid}")

        post = build_plan()
        if post["create"] or post["update"]:
            raise RuntimeError(
                f"sync not idempotent: create={post['create']} update={post['update']}"
            )

        return {
            "status": "PASS",
            "created": plan["create"],
            "updated": plan["update"],
            "unchanged": plan["unchanged"],
            "backup": str(backup),
        }
    except Exception:
        restore_cards(backup)
        if _snapshot_tables() != before_db:
            raise RuntimeError("rollback restored cards but commerce DB changed externally")
        if (pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b"") != before_map:
            raise RuntimeError("rollback restored cards but commerce_map changed externally")
        raise


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"plantlogic-v3-sync-{stamp()}.json"
    payload = {
        "mode": mode,
        "summary": {
            "products": EXPECTED_PRODUCTS,
            "skus": EXPECTED_SKUS,
            "create": plan["create"],
            "update": plan["update"],
            "unchanged": plan["unchanged"],
        },
        "actions": [
            {
                "action": x["action"],
                "product_id": x["product_id"],
                "slug": x["slug"],
            }
            for x in plan["actions"]
        ],
        "deferred": plan["deferred"],
        "result": result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = build_plan()
    print("BB610 PLANTLOGIC V3 MASTER SYNC")
    print("PRODUCTS:", EXPECTED_PRODUCTS)
    print("SKU:", EXPECTED_SKUS)
    print("CREATE:", plan["create"])
    print("UPDATE:", plan["update"])
    print("UNCHANGED:", plan["unchanged"])
    for row in plan["actions"]:
        if row["action"] != "UNCHANGED":
            print(row["action"] + ":", row["slug"])

    if not args.apply_safe:
        report = write_report(plan, None, "DRY_RUN")
        print("RESULT: PASS (DRY_RUN)")
        print("REPORT:", report)
        return 0

    result = apply_plan(plan)
    report = write_report(plan, result, "APPLY_SAFE")
    print("RESULT:", result["status"])
    print("CREATED:", result["created"])
    print("UPDATED:", result["updated"])
    print("UNCHANGED:", result["unchanged"])
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
