from __future__ import annotations

"""Safe R2 cleanup for the 10 known surplus Product Card v3 records.

Production evidence showed that the 9 duplicate MASTER/PLANTAFOL cards use
different commerce parents/keys but mirror the canonical card package-by-package.
This updater therefore treats a duplicate mapping as redundant only if every
package has matching live commerce state (effective/base/sale price, availability,
stock_qty and enabled) on duplicate and canonical sides.

The commerce database is never changed. Redundant Product Card v3 mapping rows
are removed, duplicate card files are archived, and unique resolvable media are
copied into the matching canonical SKU before archive.

example-product is archived only when:
- its catalog parent is explicitly unpublished;
- every mapped live commerce SKU exists and is disabled;
- it has no resolvable media.

Any failed precondition means zero writes.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_media import _is_resolvable
from backend.services.product_commerce import commerce_map as live_commerce_map
from backend.services.catalog_cms import admin_detail
from backend.tools_complete_pcv3_media_readiness import _pack_key
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

PAIRS = {
    "master-npk-13-40-13": "master-13-40-13",
    "master-npk-15-5-30": "master-15-5-30",
    "master-npk-20-20-20": "master-20-20-20",
    "master-npk-3-11-38": "master-3-11-38",
    "plantafol-npk-0-25-50": "plantafol-0-25-50",
    "plantafol-npk-10-54-10": "plantafol-10-54-10",
    "plantafol-npk-20-20-20": "plantafol-20-20-20",
    "plantafol-npk-30-10-10": "plantafol-30-10-10",
    "plantafol-npk-5-15-45": "plantafol-5-15-45",
}
EXAMPLE_SLUG = "example-product"
EXPECTED_BEFORE = 119
EXPECTED_AFTER = 109


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _card_by_slug(slug: str) -> dict:
    hits = [x for x in cards.list_cards() if str(x.get("slug") or "") == slug]
    if len(hits) != 1:
        raise RuntimeError(f"{slug}: expected exactly one runtime card; got {len(hits)}")
    card = cards.get(str(hits[0].get("product_id") or ""))
    if not isinstance(card, dict):
        raise RuntimeError(f"{slug}: product file missing")
    return card


def _mapping_index() -> dict[str, dict]:
    return {
        str(x.get("product_id") or ""): x
        for x in (cards.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }


def _sku_by_pack(card: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sku in ((card.get("sku_media") or {}).get("skus") or []):
        if not isinstance(sku, dict) or sku.get("enabled") is False:
            continue
        key = _pack_key(sku.get("package") or sku.get("label") or "")
        if not key:
            raise RuntimeError(f"{card.get('slug')}: SKU without normalized package")
        if key in out:
            raise RuntimeError(f"{card.get('slug')}: duplicate package {key}")
        out[key] = sku
    return out


def _bound_by_pack(card: dict, mapping: dict, live: dict[str, dict]) -> dict[str, dict]:
    skus = {
        str(x.get("sku_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict) and x.get("sku_id") and x.get("enabled") is not False
    }
    out: dict[str, dict] = {}
    for row in (mapping.get("skus") or []):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("sku_id") or "").strip()
        key = str(row.get("existing_commerce_sku_key") or "").strip()
        sku = skus.get(sid)
        if not sku:
            continue
        pack = _pack_key(sku.get("package") or sku.get("label") or "")
        if not pack:
            raise RuntimeError(f"{card.get('slug')}: mapped SKU without package")
        if pack in out:
            raise RuntimeError(f"{card.get('slug')}: duplicate mapped package {pack}")
        out[pack] = {
            "sku_id": sid,
            "commerce_key": key,
            "commerce": live.get(key) if key else None,
        }
    return out


def _commerce_state(row: dict | None) -> tuple[Any, ...] | None:
    if not isinstance(row, dict):
        return None
    return (
        row.get("price"),
        row.get("sale_price"),
        row.get("effective_price"),
        row.get("availability"),
        row.get("stock_qty"),
        bool(row.get("enabled")),
    )


def compare_pair(
    duplicate_card: dict,
    duplicate_mapping: dict,
    canonical_card: dict,
    canonical_mapping: dict,
    live: dict[str, dict],
) -> dict:
    dpacks = _sku_by_pack(duplicate_card)
    cpacks = _sku_by_pack(canonical_card)
    if set(dpacks) != set(cpacks):
        return {
            "safe": False,
            "reason": f"package mismatch duplicate={sorted(dpacks)} canonical={sorted(cpacks)}",
            "rows": [],
        }

    dbound = _bound_by_pack(duplicate_card, duplicate_mapping, live)
    cbound = _bound_by_pack(canonical_card, canonical_mapping, live)
    if set(dbound) != set(dpacks):
        return {
            "safe": False,
            "reason": f"duplicate binding coverage mismatch mapped={sorted(dbound)} packages={sorted(dpacks)}",
            "rows": [],
        }
    if set(cbound) != set(cpacks):
        return {
            "safe": False,
            "reason": f"canonical binding coverage mismatch mapped={sorted(cbound)} packages={sorted(cpacks)}",
            "rows": [],
        }

    rows = []
    for pack in sorted(dpacks):
        d = dbound[pack]
        c = cbound[pack]
        ds = _commerce_state(d["commerce"])
        cs = _commerce_state(c["commerce"])
        if ds is None:
            return {"safe": False, "reason": f"{pack}: duplicate live commerce row missing", "rows": rows}
        if cs is None:
            return {"safe": False, "reason": f"{pack}: canonical live commerce row missing", "rows": rows}
        same = ds == cs
        rows.append({
            "package": pack,
            "duplicate_commerce_key": d["commerce_key"],
            "canonical_commerce_key": c["commerce_key"],
            "duplicate_state": list(ds),
            "canonical_state": list(cs),
            "same_state": same,
        })
        if not same:
            return {
                "safe": False,
                "reason": f"{pack}: commerce state differs duplicate={ds} canonical={cs}",
                "rows": rows,
            }

    return {
        "safe": True,
        "reason": "package set and live commerce state are identical",
        "rows": rows,
    }


def _media_by_id(card: dict) -> dict[str, dict]:
    return {
        str(x.get("media_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }


def _resolvable_media(card: dict, media_id: Any) -> dict | None:
    row = _media_by_id(card).get(str(media_id or ""))
    if not row:
        return None
    path = str(row.get("path") or "").strip()
    return row if path and _is_resolvable(path) else None


def _copy_media(canonical: dict, duplicate: dict, media_id: Any) -> str | None:
    source = _resolvable_media(duplicate, media_id)
    if not source:
        return None
    path = str(source.get("path") or "")

    media = (canonical.get("sku_media") or {}).setdefault("media", [])
    existing = next(
        (x for x in media if isinstance(x, dict) and str(x.get("path") or "") == path),
        None,
    )
    if existing:
        return str(existing.get("media_id") or "")

    used = {str(x.get("media_id") or "") for x in media if isinstance(x, dict)}
    base = "med_merge_" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]
    mid = base
    n = 2
    while mid in used:
        mid = f"{base}_{n}"
        n += 1

    media.append({
        "media_id": mid,
        "path": path,
        "alt": str(source.get("alt") or ""),
        "kind": str(source.get("kind") or "product"),
        "sort_order": len(media),
    })
    return mid


def _merge_media(canonical: dict, duplicate: dict) -> dict:
    cpacks = _sku_by_pack(canonical)
    dpacks = _sku_by_pack(duplicate)
    primary = gallery = 0

    for pack, csku in cpacks.items():
        dsku = dpacks[pack]
        if _resolvable_media(canonical, csku.get("primary_media_id")) is None:
            mid = _copy_media(canonical, duplicate, dsku.get("primary_media_id"))
            if mid:
                csku["primary_media_id"] = mid
                primary += 1

        cg = csku.setdefault("gallery_media_ids", [])
        paths = {
            str((_resolvable_media(canonical, x) or {}).get("path") or "")
            for x in cg
        }
        paths.discard("")
        for gid in dsku.get("gallery_media_ids") or []:
            src = _resolvable_media(duplicate, gid)
            if not src:
                continue
            path = str(src.get("path") or "")
            if path in paths:
                continue
            mid = _copy_media(canonical, duplicate, gid)
            if mid and mid not in cg:
                cg.append(mid)
                paths.add(path)
                gallery += 1

    return {"primary": primary, "gallery": gallery}


def _example_preflight(card: dict, mapping: dict, live: dict[str, dict]) -> dict:
    parent = str(mapping.get("existing_product_key") or "").strip()
    detail = admin_detail(parent) if parent else None
    if not isinstance(detail, dict):
        return {"safe": False, "reason": "example commerce parent detail is missing"}
    if detail.get("published") is not False:
        return {"safe": False, "reason": f"example commerce parent published={detail.get('published')}"}

    media = [
        x for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict)
        and str(x.get("path") or "").strip()
        and _is_resolvable(str(x.get("path") or "").strip())
    ]
    if media:
        return {"safe": False, "reason": f"example has {len(media)} resolvable media item(s)"}

    keys = [
        str(x.get("existing_commerce_sku_key") or "").strip()
        for x in (mapping.get("skus") or [])
        if isinstance(x, dict) and str(x.get("existing_commerce_sku_key") or "").strip()
    ]
    if not keys:
        return {"safe": False, "reason": "example has no mapped commerce SKU keys"}

    states = []
    for key in keys:
        row = live.get(key)
        if not isinstance(row, dict):
            return {"safe": False, "reason": f"example live commerce row missing: {key}"}
        states.append({
            "commerce_key": key,
            "price": row.get("price"),
            "sale_price": row.get("sale_price"),
            "availability": row.get("availability"),
            "stock_qty": row.get("stock_qty"),
            "enabled": bool(row.get("enabled")),
        })
        if bool(row.get("enabled")):
            return {"safe": False, "reason": f"example commerce SKU enabled: {key}"}

    return {
        "safe": True,
        "reason": "parent unpublished, all commerce SKU disabled, no resolvable media",
        "parent": parent,
        "states": states,
    }


def build_plan() -> dict:
    count = len(cards.list_cards())
    mappings = _mapping_index()
    live = live_commerce_map()
    safe_pairs = []
    blocked = []

    if count != EXPECTED_BEFORE:
        blocked.append({
            "slug": "__runtime_count__",
            "reason": f"expected {EXPECTED_BEFORE} cards before cleanup; got {count}",
        })

    for duplicate_slug, canonical_slug in PAIRS.items():
        try:
            duplicate = _card_by_slug(duplicate_slug)
            canonical = _card_by_slug(canonical_slug)
        except Exception as exc:
            blocked.append({
                "slug": duplicate_slug,
                "canonical_slug": canonical_slug,
                "reason": str(exc),
            })
            continue

        dmap = mappings.get(str(duplicate.get("product_id") or ""))
        cmap = mappings.get(str(canonical.get("product_id") or ""))
        if not isinstance(dmap, dict):
            blocked.append({
                "slug": duplicate_slug,
                "canonical_slug": canonical_slug,
                "reason": "duplicate commerce mapping missing",
            })
            continue
        if not isinstance(cmap, dict):
            blocked.append({
                "slug": duplicate_slug,
                "canonical_slug": canonical_slug,
                "reason": "canonical commerce mapping missing",
            })
            continue

        comparison = compare_pair(duplicate, dmap, canonical, cmap, live)
        item = {
            "duplicate_slug": duplicate_slug,
            "canonical_slug": canonical_slug,
            "duplicate_product_id": str(duplicate.get("product_id") or ""),
            "canonical_product_id": str(canonical.get("product_id") or ""),
            "duplicate_parent": str(dmap.get("existing_product_key") or ""),
            "canonical_parent": str(cmap.get("existing_product_key") or ""),
            "comparison": comparison,
        }
        if comparison["safe"]:
            safe_pairs.append(item)
        else:
            blocked.append({
                "slug": duplicate_slug,
                "canonical_slug": canonical_slug,
                "reason": comparison["reason"],
            })

    example = None
    try:
        example_card = _card_by_slug(EXAMPLE_SLUG)
        example_mapping = mappings.get(str(example_card.get("product_id") or ""))
        if not isinstance(example_mapping, dict):
            example = {"safe": False, "reason": "example commerce mapping missing"}
        else:
            example = _example_preflight(example_card, example_mapping, live)
            example["product_id"] = str(example_card.get("product_id") or "")
    except Exception as exc:
        example = {"safe": False, "reason": str(exc)}

    return {
        "cards_before": count,
        "safe_pairs": safe_pairs,
        "blocked": blocked,
        "example": example,
    }


def _restore_backup(backup: Path) -> None:
    saved = backup / "product_cards_v3"
    if not saved.is_dir():
        raise RuntimeError(f"backup missing: {saved}")
    if cards.BASE.exists():
        shutil.rmtree(cards.BASE)
    shutil.copytree(saved, cards.BASE)


def apply_plan(plan: dict) -> dict:
    if plan["blocked"]:
        raise RuntimeError(
            f"R2 cleanup blocked for {len(plan['blocked'])} condition(s); no writes performed"
        )
    if len(plan["safe_pairs"]) != 9:
        raise RuntimeError(f"expected 9 safe pairs; got {len(plan['safe_pairs'])}")
    if not plan["example"].get("safe"):
        raise RuntimeError("example-product blocked: " + str(plan["example"].get("reason") or ""))

    stamp_value = stamp()
    backup = BACKUP_ROOT / f"pcv3-surplus-r2-{stamp_value}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cards.BASE, backup / "product_cards_v3")
    db_before = _snapshot_tables()

    archive = cards.BASE / "archive" / "surplus" / stamp_value
    archive.mkdir(parents=True, exist_ok=True)

    cmap = cards.commerce_map()
    rows = [x for x in (cmap.get("products") or []) if isinstance(x, dict)]
    remove_ids: set[str] = set()
    manifest = []
    copied_primary = copied_gallery = 0

    try:
        # Re-run full preflight immediately before the first write.
        current = build_plan()
        if current["blocked"] or len(current["safe_pairs"]) != 9 or not current["example"].get("safe"):
            raise RuntimeError("production state changed between dry-run and apply preflight")

        for item in current["safe_pairs"]:
            duplicate = _card_by_slug(item["duplicate_slug"])
            canonical = _card_by_slug(item["canonical_slug"])

            merged = _merge_media(canonical, duplicate)
            copied_primary += merged["primary"]
            copied_gallery += merged["gallery"]
            cards.validate(canonical)
            cards.put(str(canonical["product_id"]), canonical)

            duplicate_id = str(duplicate["product_id"])
            src = cards._product_path(duplicate_id)
            dest = archive / src.name
            if not src.is_file():
                raise RuntimeError(f"duplicate source file missing: {duplicate_id}")
            shutil.move(str(src), str(dest))
            remove_ids.add(duplicate_id)
            manifest.append({
                "kind": "duplicate",
                "archived_product_id": duplicate_id,
                "archived_slug": item["duplicate_slug"],
                "canonical_product_id": str(canonical["product_id"]),
                "canonical_slug": item["canonical_slug"],
                "duplicate_parent": item["duplicate_parent"],
                "canonical_parent": item["canonical_parent"],
                "archive_path": str(dest.relative_to(cards.BASE)),
            })

        example = _card_by_slug(EXAMPLE_SLUG)
        example_id = str(example["product_id"])
        src = cards._product_path(example_id)
        dest = archive / src.name
        if not src.is_file():
            raise RuntimeError("example-product file missing")
        shutil.move(str(src), str(dest))
        remove_ids.add(example_id)
        manifest.append({
            "kind": "example",
            "archived_product_id": example_id,
            "archived_slug": EXAMPLE_SLUG,
            "commerce_parent": current["example"].get("parent"),
            "archive_path": str(dest.relative_to(cards.BASE)),
        })

        cmap["products"] = [
            row for row in rows
            if str(row.get("product_id") or "") not in remove_ids
        ]
        cards._save(cards.COMMERCE_MAP, cmap)
        cards._rebuild_index()
        (archive / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if _snapshot_tables() != db_before:
            raise RuntimeError("commerce DB changed during R2 cleanup")

        after = cards.list_cards()
        if len(after) != EXPECTED_AFTER:
            raise RuntimeError(
                f"expected {EXPECTED_AFTER} cards after cleanup; got {len(after)}"
            )

        for slug in list(PAIRS) + [EXAMPLE_SLUG]:
            if any(str(x.get("slug") or "") == slug for x in after):
                raise RuntimeError(f"surplus slug still present: {slug}")

        for slug in PAIRS.values():
            canonical = _card_by_slug(slug)
            if not canonical.get("enabled"):
                raise RuntimeError(f"canonical card unexpectedly disabled: {slug}")

    except Exception:
        _restore_backup(backup)
        print("AUTO ROLLBACK:", backup)
        print("AUTO ROLLBACK RESULT: PASS")
        raise

    return {
        "status": "PASS",
        "archived": 10,
        "cards_after": len(cards.list_cards()),
        "mapping_rows_removed": len(remove_ids),
        "primary_media_recovered": copied_primary,
        "gallery_media_recovered": copied_gallery,
        "commerce_db_unchanged": True,
        "backup_dir": str(backup),
        "archive_dir": str(archive),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = build_plan()
    result = apply_plan(plan) if args.apply_safe else None

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_ROOT / f"pcv3-surplus-r2-{stamp()}.json"
    report = {
        "schema_version": "2.0",
        "mode": "APPLY_SAFE" if args.apply_safe else "DRY_RUN",
        "plan": plan,
        "apply": result,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("BB610 PRODUCT CARD V3 — SURPLUS R2 CLEANUP")
    print("MODE:", report["mode"])
    print("CARDS BEFORE:", plan["cards_before"])
    print("SAFE PAIRS:", len(plan["safe_pairs"]))
    print("BLOCKED:", len(plan["blocked"]))
    for item in plan["safe_pairs"]:
        print(
            "SAFE:",
            item["duplicate_slug"],
            "=>",
            item["canonical_slug"],
            "| duplicate_parent=", item["duplicate_parent"],
            "| canonical_parent=", item["canonical_parent"],
            "|", item["comparison"]["reason"],
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
        print("MAPPING ROWS REMOVED:", result["mapping_rows_removed"])
        print("PRIMARY MEDIA RECOVERED:", result["primary_media_recovered"])
        print("GALLERY MEDIA RECOVERED:", result["gallery_media_recovered"])
        print(
            "COMMERCE DB UNCHANGED:",
            "PASS" if result["commerce_db_unchanged"] else "FAIL",
        )
        print("BACKUP:", result["backup_dir"])
        print("ARCHIVE:", result["archive_dir"])

    print("REPORT:", report_path)
    if plan["blocked"] or not plan["example"].get("safe"):
        raise SystemExit(2)
    print("RESULT: PASS" if not result else "FINAL SURPLUS CLEANUP: 10/10 PASS")


if __name__ == "__main__":
    main()
