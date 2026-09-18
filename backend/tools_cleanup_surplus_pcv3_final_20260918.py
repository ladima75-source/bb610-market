from __future__ import annotations

"""Final safe cleanup of the 10 surplus Product Card v3 records.

The 2026-09-18 production audit established:
- 8 duplicate MASTER/PLANTAFOL pairs are exact commerce mirrors;
- MASTER 15-5-30 differs only for 20 g, where the duplicate branch has a stale
  active 25 UAH offer while the approved source row is zero and the canonical
  branch is intentionally price=None / enabled=False;
- example-product is unpublished and all of its commerce SKU are disabled.

Policy:
1) Canonical Product Card + canonical commerce state is authoritative.
2) Never copy a stale duplicate price into canonical commerce.
3) Retire duplicate legacy commerce parents by unpublishing them and disabling
   only their mapped duplicate SKU rows; price/sale_price/availability/stock are
   preserved.
4) Copy resolvable media into canonical matching packages when useful.
5) Archive the 9 duplicate cards + example-product and remove only their V3
   commerce_map rows.
6) Full DB + Product Card backup and automatic rollback on any failed verify.
"""

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import DB_PATH, connect
from backend.services import product_cards_v3 as cards
from backend.services.catalog_cms import admin_detail, save_product
from backend.tools_apply_valagro_prices_20260916_runtime import load_source, pack_key
from backend import tools_cleanup_surplus_pcv3_r2_20260918 as r2

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

PAIRS = dict(r2.PAIRS)
EXAMPLE_SLUG = r2.EXAMPLE_SLUG
SPECIAL_DUPLICATE = "master-npk-15-5-30"
SPECIAL_CANONICAL = "master-15-5-30"
SPECIAL_PACKAGE_KEY = "20g"
EXPECTED_BEFORE = 119
EXPECTED_AFTER = 109


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def backup_db(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(src))
    try:
        target = sqlite3.connect(str(dest))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def restore_db(src: Path, dest: Path) -> None:
    backup_db(src, dest)


def mapping_index() -> dict[str, dict]:
    return {
        str(x.get("product_id") or ""): x
        for x in (cards.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }


def live_commerce_rows() -> dict[str, dict]:
    with connect() as con:
        return {
            str(row["sku"]): dict(row)
            for row in con.execute(
                "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at "
                "FROM sku_commerce"
            ).fetchall()
        }


def content_rows() -> dict[str, dict]:
    with connect() as con:
        rows = con.execute(
            "SELECT product_id,slug,content_json,published,created_at,updated_at "
            "FROM product_content"
        ).fetchall()
    return {str(x["product_id"]): dict(x) for x in rows}


def commerce_state(row: dict | None) -> tuple[Any, ...] | None:
    if not isinstance(row, dict):
        return None
    effective = row.get("sale_price") if row.get("sale_price") is not None else row.get("price")
    return (
        row.get("price"),
        row.get("sale_price"),
        effective,
        row.get("availability"),
        row.get("stock_qty"),
        bool(row.get("enabled")),
    )


def source_zero_policy() -> dict:
    source = load_source()
    hits = [
        x for x in source["target_rows"]
        if x.get("slug") == SPECIAL_CANONICAL
        and pack_key(x.get("package")) == SPECIAL_PACKAGE_KEY
    ]
    if len(hits) != 1:
        raise RuntimeError(
            f"expected exactly one approved source row for {SPECIAL_CANONICAL}/{SPECIAL_PACKAGE_KEY}; got {len(hits)}"
        )
    row = hits[0]
    if float(row.get("price") or 0) != 0.0:
        raise RuntimeError(
            f"approved source row for {SPECIAL_CANONICAL}/{SPECIAL_PACKAGE_KEY} is not zero: {row.get('price')}"
        )
    return row


def side(card: dict, mapping: dict, live: dict[str, dict]) -> dict[str, dict]:
    return r2._bound_by_pack(card, mapping, live)


def build_plan() -> dict:
    count = len(cards.list_cards())
    mappings = mapping_index()
    live = live_commerce_rows()
    zero_source = source_zero_policy()

    safe_pairs = []
    blocked = []

    if count != EXPECTED_BEFORE:
        blocked.append({
            "slug": "__runtime_count__",
            "reason": f"expected {EXPECTED_BEFORE} runtime cards; got {count}",
        })

    duplicate_product_ids: set[str] = set()
    duplicate_parents: set[str] = set()
    duplicate_keys: set[str] = set()
    canonical_keys: set[str] = set()

    for duplicate_slug, canonical_slug in PAIRS.items():
        try:
            duplicate = r2._card_by_slug(duplicate_slug)
            canonical = r2._card_by_slug(canonical_slug)
        except Exception as exc:
            blocked.append({"slug": duplicate_slug, "reason": str(exc)})
            continue

        dpid = str(duplicate.get("product_id") or "")
        cpid = str(canonical.get("product_id") or "")
        dmap = mappings.get(dpid)
        cmap = mappings.get(cpid)
        if not isinstance(dmap, dict) or not isinstance(cmap, dict):
            blocked.append({
                "slug": duplicate_slug,
                "reason": "duplicate or canonical commerce mapping missing",
            })
            continue

        try:
            dpacks = r2._sku_by_pack(duplicate)
            cpacks = r2._sku_by_pack(canonical)
        except Exception as exc:
            blocked.append({"slug": duplicate_slug, "reason": str(exc)})
            continue
        if set(dpacks) != set(cpacks):
            blocked.append({
                "slug": duplicate_slug,
                "reason": f"package mismatch duplicate={sorted(dpacks)} canonical={sorted(cpacks)}",
            })
            continue

        dbound = side(duplicate, dmap, live)
        cbound = side(canonical, cmap, live)
        if set(dbound) != set(dpacks) or set(cbound) != set(cpacks):
            blocked.append({
                "slug": duplicate_slug,
                "reason": (
                    f"binding coverage mismatch dup={sorted(dbound)} can={sorted(cbound)} "
                    f"packs={sorted(dpacks)}"
                ),
            })
            continue

        rows = []
        reason = ""
        for pkey in sorted(dpacks):
            drow = dbound[pkey]
            crow = cbound[pkey]
            ds = commerce_state(drow.get("commerce"))
            cs = commerce_state(crow.get("commerce"))
            if ds is None or cs is None:
                reason = f"{pkey}: live commerce row missing"
                break

            if duplicate_slug == SPECIAL_DUPLICATE and pkey == SPECIAL_PACKAGE_KEY:
                if float(zero_source.get("price") or 0) != 0.0:
                    reason = "approved zero-source policy disappeared"
                    break
                if cs[0] not in (None, 0, 0.0) or cs[5] is not False:
                    reason = f"{pkey}: canonical no-price policy changed: {cs}"
                    break
                if ds[0] is None or float(ds[0]) <= 0 or ds[5] is not True:
                    reason = f"{pkey}: stale duplicate state is not the expected active positive-price branch: {ds}"
                    break
                policy = "retire-stale-duplicate; preserve canonical zero-price disabled policy"
            else:
                if ds != cs:
                    reason = f"{pkey}: commerce state differs duplicate={ds} canonical={cs}"
                    break
                policy = "exact-mirror"

            rows.append({
                "package_key": pkey,
                "duplicate_commerce_key": drow["commerce_key"],
                "canonical_commerce_key": crow["commerce_key"],
                "duplicate_state": list(ds),
                "canonical_state": list(cs),
                "policy": policy,
            })

        if reason:
            blocked.append({
                "slug": duplicate_slug,
                "canonical_slug": canonical_slug,
                "reason": reason,
            })
            continue

        dparent = str(dmap.get("existing_product_key") or "").strip()
        cparent = str(cmap.get("existing_product_key") or "").strip()
        if not dparent or not cparent:
            blocked.append({
                "slug": duplicate_slug,
                "reason": "commerce parent missing",
            })
            continue

        duplicate_product_ids.add(dpid)
        duplicate_parents.add(dparent)
        for x in rows:
            duplicate_keys.add(str(x["duplicate_commerce_key"]))
            canonical_keys.add(str(x["canonical_commerce_key"]))

        safe_pairs.append({
            "duplicate_slug": duplicate_slug,
            "canonical_slug": canonical_slug,
            "duplicate_product_id": dpid,
            "canonical_product_id": cpid,
            "duplicate_parent": dparent,
            "canonical_parent": cparent,
            "rows": rows,
        })

    # example-product must already be non-public and its mapped commerce SKU disabled.
    example = {"safe": False, "reason": ""}
    try:
        ecard = r2._card_by_slug(EXAMPLE_SLUG)
        epid = str(ecard.get("product_id") or "")
        emap = mappings.get(epid)
        if not isinstance(emap, dict):
            example["reason"] = "example commerce mapping missing"
        else:
            eparent = str(emap.get("existing_product_key") or "").strip()
            detail = admin_detail(eparent) if eparent else None
            keys = [
                str(x.get("existing_commerce_sku_key") or "").strip()
                for x in (emap.get("skus") or [])
                if isinstance(x, dict) and str(x.get("existing_commerce_sku_key") or "").strip()
            ]
            if not isinstance(detail, dict):
                example["reason"] = "example parent detail missing"
            elif detail.get("published") is not False:
                example["reason"] = f"example parent is published={detail.get('published')}"
            elif not keys:
                example["reason"] = "example has no mapped commerce SKU"
            elif any(not isinstance(live.get(k), dict) for k in keys):
                example["reason"] = "example mapped commerce row missing"
            elif any(bool(live[k].get("enabled")) for k in keys):
                example["reason"] = "example has enabled commerce SKU"
            else:
                example = {
                    "safe": True,
                    "reason": "parent unpublished and all mapped commerce SKU disabled",
                    "product_id": epid,
                    "parent": eparent,
                    "commerce_keys": keys,
                }
    except Exception as exc:
        example["reason"] = str(exc)

    if len(safe_pairs) != 9:
        blocked.append({
            "slug": "__pair_count__",
            "reason": f"expected 9 safe duplicate pairs; got {len(safe_pairs)}",
        })
    if not example.get("safe"):
        blocked.append({"slug": EXAMPLE_SLUG, "reason": example.get("reason")})

    return {
        "cards_before": count,
        "safe_pairs": safe_pairs,
        "blocked": blocked,
        "example": example,
        "duplicate_product_ids": sorted(duplicate_product_ids),
        "duplicate_parents": sorted(duplicate_parents),
        "duplicate_commerce_keys": sorted(duplicate_keys),
        "canonical_commerce_keys": sorted(canonical_keys),
        "zero_source_row": zero_source,
    }


def _verify_only_expected_db_changes(
    before_commerce: dict[str, dict],
    after_commerce: dict[str, dict],
    duplicate_keys: set[str],
    before_content: dict[str, dict],
    after_content: dict[str, dict],
    duplicate_parents: set[str],
) -> None:
    if set(before_commerce) != set(after_commerce):
        raise RuntimeError("sku_commerce key set changed during cleanup")

    for key in before_commerce:
        b = before_commerce[key]
        a = after_commerce[key]
        if key in duplicate_keys:
            for field in ("sku", "price", "sale_price", "availability", "stock_qty"):
                if a.get(field) != b.get(field):
                    raise RuntimeError(f"{key}: protected commerce field changed: {field}")
            if bool(a.get("enabled")) is not False:
                raise RuntimeError(f"{key}: duplicate commerce SKU not disabled")
        else:
            if a != b:
                raise RuntimeError(f"{key}: non-target commerce row changed")

    changed_content = {
        pid
        for pid in set(before_content) | set(after_content)
        if before_content.get(pid) != after_content.get(pid)
    }
    if not changed_content.issubset(duplicate_parents):
        raise RuntimeError(
            "unexpected product_content changes: " + ", ".join(sorted(changed_content - duplicate_parents))
        )
    for pid in duplicate_parents:
        row = after_content.get(pid)
        if not isinstance(row, dict):
            raise RuntimeError(f"{pid}: unpublished override missing after cleanup")
        if bool(row.get("published")):
            raise RuntimeError(f"{pid}: duplicate commerce parent still published")


def apply_plan(plan: dict) -> dict:
    if plan["blocked"]:
        raise RuntimeError(
            f"final cleanup blocked for {len(plan['blocked'])} condition(s); no writes performed"
        )

    # Full second preflight immediately before any write.
    current = build_plan()
    if current["blocked"]:
        raise RuntimeError("production state changed between dry-run and apply")

    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"pcv3-final-cleanup-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    db_backup = backup_dir / Path(DB_PATH).name
    backup_db(Path(DB_PATH), db_backup)
    shutil.copytree(cards.BASE, backup_dir / "product_cards_v3")

    before_commerce = live_commerce_rows()
    before_content = content_rows()
    canonical_snapshot = {
        key: before_commerce.get(key)
        for key in current["canonical_commerce_keys"]
    }

    duplicate_keys = set(current["duplicate_commerce_keys"])
    duplicate_parents = set(current["duplicate_parents"])
    remove_ids = set(current["duplicate_product_ids"])
    remove_ids.add(str(current["example"]["product_id"]))

    archive = cards.BASE / "archive" / "surplus" / run_stamp
    archive.mkdir(parents=True, exist_ok=True)
    copied_primary = copied_gallery = 0
    archive_manifest = []

    try:
        # Retire duplicate legacy branches without touching price or canonical rows.
        ts = now()
        with connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                for key in sorted(duplicate_keys):
                    con.execute(
                        "UPDATE sku_commerce SET enabled=0, updated_at=? WHERE sku=?",
                        (ts, key),
                    )
                con.commit()
            except Exception:
                con.rollback()
                raise

        for parent in sorted(duplicate_parents):
            detail = admin_detail(parent)
            if not isinstance(detail, dict):
                raise RuntimeError(f"{parent}: duplicate parent disappeared")
            save_product(parent, {"published": False}, create=False)

        after_commerce = live_commerce_rows()
        after_content = content_rows()
        _verify_only_expected_db_changes(
            before_commerce,
            after_commerce,
            duplicate_keys,
            before_content,
            after_content,
            duplicate_parents,
        )

        # Canonical commerce state must stay byte-for-field identical.
        for key, snapshot in canonical_snapshot.items():
            if after_commerce.get(key) != snapshot:
                raise RuntimeError(f"{key}: canonical commerce row changed")

        # Merge media and archive the 9 duplicate cards.
        for item in current["safe_pairs"]:
            duplicate = r2._card_by_slug(item["duplicate_slug"])
            canonical = r2._card_by_slug(item["canonical_slug"])
            merged = r2._merge_media(canonical, duplicate)
            copied_primary += merged["primary"]
            copied_gallery += merged["gallery"]
            cards.validate(canonical)
            cards.put(str(canonical["product_id"]), canonical)

            duplicate_id = str(duplicate["product_id"])
            src = cards._product_path(duplicate_id)
            dest = archive / src.name
            if not src.is_file():
                raise RuntimeError(f"duplicate card file missing: {duplicate_id}")
            shutil.move(str(src), str(dest))
            archive_manifest.append({
                "kind": "duplicate",
                "archived_product_id": duplicate_id,
                "archived_slug": item["duplicate_slug"],
                "canonical_product_id": str(canonical["product_id"]),
                "canonical_slug": item["canonical_slug"],
                "retired_parent": item["duplicate_parent"],
                "archive_path": str(dest.relative_to(cards.BASE)),
            })

        # Archive example-product V3 card.
        example = r2._card_by_slug(EXAMPLE_SLUG)
        example_id = str(example["product_id"])
        src = cards._product_path(example_id)
        dest = archive / src.name
        if not src.is_file():
            raise RuntimeError("example-product file missing")
        shutil.move(str(src), str(dest))
        archive_manifest.append({
            "kind": "example",
            "archived_product_id": example_id,
            "archived_slug": EXAMPLE_SLUG,
            "commerce_parent": current["example"]["parent"],
            "archive_path": str(dest.relative_to(cards.BASE)),
        })

        # Remove only archived V3 mapping rows. Legacy DB rows stay for audit/history.
        cmap = cards.commerce_map()
        cmap["products"] = [
            x for x in (cmap.get("products") or [])
            if not (isinstance(x, dict) and str(x.get("product_id") or "") in remove_ids)
        ]
        cards._save(cards.COMMERCE_MAP, cmap)
        cards._rebuild_index()

        (archive / "manifest.json").write_text(
            json.dumps(archive_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        after_cards = cards.list_cards()
        if len(after_cards) != EXPECTED_AFTER:
            raise RuntimeError(
                f"expected {EXPECTED_AFTER} cards after cleanup; got {len(after_cards)}"
            )

        for slug in list(PAIRS) + [EXAMPLE_SLUG]:
            if any(str(x.get("slug") or "") == slug for x in after_cards):
                raise RuntimeError(f"archived surplus slug still present: {slug}")
        for slug in PAIRS.values():
            card = r2._card_by_slug(slug)
            if not card.get("enabled"):
                raise RuntimeError(f"canonical card unexpectedly disabled: {slug}")

        final_commerce = live_commerce_rows()
        for key, snapshot in canonical_snapshot.items():
            if final_commerce.get(key) != snapshot:
                raise RuntimeError(f"{key}: canonical commerce changed after card archive")
        for key in duplicate_keys:
            if bool((final_commerce.get(key) or {}).get("enabled")):
                raise RuntimeError(f"{key}: retired duplicate SKU became enabled")

    except Exception:
        # Restore both DB and Product Card v3 atomically enough for this maintenance path.
        restore_db(db_backup, Path(DB_PATH))
        saved_cards = backup_dir / "product_cards_v3"
        if cards.BASE.exists():
            shutil.rmtree(cards.BASE)
        shutil.copytree(saved_cards, cards.BASE)
        print("AUTO ROLLBACK:", backup_dir)
        print("AUTO ROLLBACK RESULT: PASS")
        raise

    return {
        "status": "PASS",
        "archived": 10,
        "cards_after": len(cards.list_cards()),
        "retired_parents": len(duplicate_parents),
        "disabled_duplicate_skus": len(duplicate_keys),
        "primary_media_recovered": copied_primary,
        "gallery_media_recovered": copied_gallery,
        "canonical_commerce_unchanged": True,
        "special_zero_policy_preserved": True,
        "backup_dir": str(backup_dir),
        "archive_dir": str(archive),
    }


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"pcv3-final-cleanup-{stamp()}.json"
    path.write_text(
        json.dumps(
            {"schema_version": "3.0", "mode": mode, "plan": plan, "apply": result},
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

    print("BB610 PRODUCT CARD V3 — FINAL SURPLUS CLEANUP")
    print("MODE:", "APPLY_SAFE" if args.apply_safe else "DRY_RUN")
    print("CARDS BEFORE:", plan["cards_before"])
    print("SAFE PAIRS:", len(plan["safe_pairs"]))
    print("BLOCKED:", len(plan["blocked"]))
    print(
        "SPECIAL POLICY:",
        "MASTER 15-5-30 / 20 g source price=0; canonical stays price=None + disabled; duplicate branch is retired",
    )
    for item in plan["safe_pairs"]:
        policy = (
            "SPECIAL_ZERO_SOURCE_RETIRE_DUPLICATE"
            if item["duplicate_slug"] == SPECIAL_DUPLICATE
            else "EXACT_MIRROR"
        )
        print(
            "SAFE:",
            item["duplicate_slug"],
            "=>",
            item["canonical_slug"],
            "|", policy,
        )
    for item in plan["blocked"]:
        print("BLOCKED:", item.get("slug"), "|", item.get("reason"))
    print(
        "EXAMPLE:",
        "SAFE" if plan["example"].get("safe") else "BLOCKED",
        "|", plan["example"].get("reason"),
    )

    if result:
        print("RESULT:", result["status"])
        print("ARCHIVED:", result["archived"])
        print("CARDS AFTER:", result["cards_after"])
        print("RETIRED DUPLICATE PARENTS:", result["retired_parents"])
        print("DISABLED DUPLICATE SKU:", result["disabled_duplicate_skus"])
        print("PRIMARY MEDIA RECOVERED:", result["primary_media_recovered"])
        print("GALLERY MEDIA RECOVERED:", result["gallery_media_recovered"])
        print(
            "CANONICAL COMMERCE UNCHANGED:",
            "PASS" if result["canonical_commerce_unchanged"] else "FAIL",
        )
        print(
            "MASTER 15-5-30 / 20g ZERO POLICY:",
            "PASS" if result["special_zero_policy_preserved"] else "FAIL",
        )
        print("BACKUP:", result["backup_dir"])
        print("ARCHIVE:", result["archive_dir"])
        print("FINAL CLEANUP: 10/10 PASS")
    else:
        print("RESULT:", "PASS (DRY_RUN)" if not plan["blocked"] else "BLOCKED")

    print("REPORT:", report)
    if plan["blocked"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
