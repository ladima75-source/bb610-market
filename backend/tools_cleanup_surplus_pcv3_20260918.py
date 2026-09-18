from __future__ import annotations

"""Archive the 10 known surplus Product Card v3 records safely.

Targets:
- 9 legacy duplicate MASTER / PLANTAFOL cards;
- the non-catalog example-product card.

Safety rules:
- exact duplicate/canonical slugs only;
- duplicate package set must equal the canonical package set;
- any duplicate commerce mapping must be fully redundant with the canonical mapping;
- unique primary/gallery media are copied to the matching canonical SKU before archive;
- commerce DB tables are never modified;
- complete Product Card v3 backup is created before any write;
- cards are archived, not destroyed.
"""

import argparse
import hashlib
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_media import _is_resolvable
from backend.tools_complete_pcv3_media_readiness import _pack_key
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

DUPLICATES = {
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


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _full_card_by_slug(slug: str) -> dict | None:
    hits = [x for x in cards.list_cards() if str(x.get("slug") or "") == slug]
    if len(hits) != 1:
        return None
    card = cards.get(str(hits[0].get("product_id") or ""))
    return card if isinstance(card, dict) else None


def _mapping_index() -> dict[str, dict]:
    return {
        str(x.get("product_id") or ""): x
        for x in (cards.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }


def _enabled_skus(card: dict) -> list[dict]:
    return [
        x for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict) and x.get("enabled") is not False
    ]


def _sku_by_pack(card: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sku in _enabled_skus(card):
        key = _pack_key(sku.get("package") or sku.get("label") or "")
        if not key:
            raise RuntimeError(f"{card.get('slug')}: SKU without normalized package")
        if key in out:
            raise RuntimeError(f"{card.get('slug')}: duplicate package {key}")
        out[key] = sku
    return out


def _media_by_id(card: dict) -> dict[str, dict]:
    return {
        str(x.get("media_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }


def _media_path(card: dict, media_id: Any) -> str:
    row = _media_by_id(card).get(str(media_id or ""))
    if not row:
        return ""
    path = str(row.get("path") or "").strip()
    return path if path and _is_resolvable(path) else ""


def _mapping_signature(mapping: dict | None) -> tuple[str, set[str]]:
    if not isinstance(mapping, dict):
        return "", set()
    parent = str(mapping.get("existing_product_key") or "").strip()
    keys = {
        str(x.get("existing_commerce_sku_key") or "").strip()
        for x in (mapping.get("skus") or [])
        if isinstance(x, dict) and str(x.get("existing_commerce_sku_key") or "").strip()
    }
    return parent, keys


def _redundant_mapping(duplicate: dict | None, canonical: dict | None) -> tuple[bool, str]:
    if not duplicate:
        return True, "duplicate has no commerce mapping"
    if not canonical:
        return False, "duplicate has mapping but canonical mapping is missing"
    d_parent, d_keys = _mapping_signature(duplicate)
    c_parent, c_keys = _mapping_signature(canonical)
    if d_parent and c_parent and d_parent != c_parent:
        return False, f"commerce parent differs: duplicate={d_parent} canonical={c_parent}"
    if not d_keys.issubset(c_keys):
        return False, f"duplicate has unique commerce SKU keys: {sorted(d_keys-c_keys)}"
    return True, "duplicate commerce mapping is redundant"


def _copy_media_entry(canonical: dict, duplicate: dict, media_id: Any) -> str | None:
    source = _media_by_id(duplicate).get(str(media_id or ""))
    if not source:
        return None
    path = str(source.get("path") or "").strip()
    if not path or not _is_resolvable(path):
        return None

    cmedia = (canonical.get("sku_media") or {}).setdefault("media", [])
    existing = next(
        (x for x in cmedia if isinstance(x, dict) and str(x.get("path") or "") == path),
        None,
    )
    if existing:
        return str(existing.get("media_id") or "")

    used = {str(x.get("media_id") or "") for x in cmedia if isinstance(x, dict)}
    base = "med_cleanup_" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]
    mid = base
    n = 2
    while mid in used:
        mid = f"{base}_{n}"
        n += 1

    cmedia.append({
        "media_id": mid,
        "path": path,
        "alt": str(source.get("alt") or ""),
        "kind": str(source.get("kind") or "product"),
        "sort_order": len(cmedia),
    })
    return mid


def _merge_media(canonical: dict, duplicate: dict) -> dict:
    cpacks = _sku_by_pack(canonical)
    dpacks = _sku_by_pack(duplicate)
    copied_primary = copied_gallery = 0

    for pack, csku in cpacks.items():
        dsku = dpacks[pack]
        if not _media_path(canonical, csku.get("primary_media_id")):
            mid = _copy_media_entry(canonical, duplicate, dsku.get("primary_media_id"))
            if mid:
                csku["primary_media_id"] = mid
                copied_primary += 1

        gallery = csku.setdefault("gallery_media_ids", [])
        existing_paths = {
            _media_path(canonical, x)
            for x in gallery
            if _media_path(canonical, x)
        }
        for source_mid in dsku.get("gallery_media_ids") or []:
            source_path = _media_path(duplicate, source_mid)
            if not source_path or source_path in existing_paths:
                continue
            mid = _copy_media_entry(canonical, duplicate, source_mid)
            if mid and mid not in gallery:
                gallery.append(mid)
                existing_paths.add(source_path)
                copied_gallery += 1

    return {
        "copied_primary": copied_primary,
        "copied_gallery": copied_gallery,
    }


def build_plan() -> dict:
    rows = cards.list_cards()
    mappings = _mapping_index()
    blocked: list[dict] = []
    safe: list[dict] = []

    for duplicate_slug, canonical_slug in DUPLICATES.items():
        duplicate = _full_card_by_slug(duplicate_slug)
        canonical = _full_card_by_slug(canonical_slug)
        reason = ""

        if not duplicate:
            reason = "duplicate card not resolved uniquely"
        elif not canonical:
            reason = "canonical card not resolved uniquely"
        elif duplicate.get("product_id") == canonical.get("product_id"):
            reason = "duplicate and canonical product_id are identical"
        else:
            try:
                dpacks = _sku_by_pack(duplicate)
                cpacks = _sku_by_pack(canonical)
                if set(dpacks) != set(cpacks):
                    reason = (
                        f"package mismatch duplicate={sorted(dpacks)} "
                        f"canonical={sorted(cpacks)}"
                    )
            except Exception as exc:
                reason = str(exc)

        dmap = mappings.get(str((duplicate or {}).get("product_id") or ""))
        cmap = mappings.get(str((canonical or {}).get("product_id") or ""))
        mapping_ok, mapping_note = _redundant_mapping(dmap, cmap)
        if not reason and not mapping_ok:
            reason = mapping_note

        item = {
            "duplicate_slug": duplicate_slug,
            "canonical_slug": canonical_slug,
            "duplicate_product_id": str((duplicate or {}).get("product_id") or ""),
            "canonical_product_id": str((canonical or {}).get("product_id") or ""),
            "duplicate_packages": sorted(_sku_by_pack(duplicate)) if duplicate else [],
            "canonical_packages": sorted(_sku_by_pack(canonical)) if canonical else [],
            "duplicate_has_mapping": bool(dmap),
            "canonical_has_mapping": bool(cmap),
            "mapping_note": mapping_note,
        }
        if reason:
            item["reason"] = reason
            blocked.append(item)
        else:
            safe.append(item)

    example = _full_card_by_slug(EXAMPLE_SLUG)
    example_item: dict[str, Any] = {
        "slug": EXAMPLE_SLUG,
        "product_id": str((example or {}).get("product_id") or ""),
        "safe": False,
        "reason": "",
    }
    if not example:
        example_item["reason"] = "example-product not resolved uniquely"
    else:
        pid = str(example.get("product_id") or "")
        mapping = mappings.get(pid)
        sm = example.get("sku_media") or {}
        media = [x for x in (sm.get("media") or []) if isinstance(x, dict)]
        skus = [x for x in (sm.get("skus") or []) if isinstance(x, dict)]
        nonblank_skus = [
            x for x in skus
            if str(x.get("sku_code") or "").strip()
            or str(x.get("package") or "").strip()
            or x.get("primary_media_id")
            or (x.get("gallery_media_ids") or [])
        ]
        if mapping:
            example_item["reason"] = "example-product has commerce mapping"
        elif media:
            example_item["reason"] = "example-product contains media"
        elif nonblank_skus:
            example_item["reason"] = "example-product contains nonblank SKU data"
        else:
            example_item["safe"] = True

    before = len(rows)
    if before != EXPECTED_BEFORE:
        blocked.append({
            "duplicate_slug": "__runtime_count__",
            "canonical_slug": "",
            "reason": f"expected {EXPECTED_BEFORE} runtime cards before cleanup; got {before}",
        })

    return {
        "cards_before": before,
        "safe_duplicates": safe,
        "blocked": blocked,
        "example": example_item,
        "expected_after": EXPECTED_AFTER,
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
            f"cleanup blocked for {len(plan['blocked'])} condition(s); no writes performed"
        )
    if len(plan["safe_duplicates"]) != 9:
        raise RuntimeError(f"expected 9 safe duplicates; got {len(plan['safe_duplicates'])}")
    if not plan["example"].get("safe"):
        raise RuntimeError(
            "example-product is not safe to archive: " + str(plan["example"].get("reason") or "")
        )

    stamp = _stamp()
    backup = BACKUP_ROOT / f"pcv3-cleanup-10-{stamp}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cards.BASE, backup / "product_cards_v3")
    db_before = _snapshot_tables()

    archive = cards.BASE / "archive" / "surplus" / stamp
    archive.mkdir(parents=True, exist_ok=True)

    cmap = cards.commerce_map()
    map_rows = [x for x in (cmap.get("products") or []) if isinstance(x, dict)]
    duplicate_ids: set[str] = set()
    archive_manifest = []
    copied_primary = copied_gallery = removed_mapping_rows = 0

    try:
        for item in plan["safe_duplicates"]:
            duplicate = _full_card_by_slug(item["duplicate_slug"])
            canonical = _full_card_by_slug(item["canonical_slug"])
            if not isinstance(duplicate, dict) or not isinstance(canonical, dict):
                raise RuntimeError(
                    f"card disappeared before apply: {item['duplicate_slug']}"
                )

            if set(_sku_by_pack(duplicate)) != set(_sku_by_pack(canonical)):
                raise RuntimeError(
                    f"package set changed since preflight: {item['duplicate_slug']}"
                )

            merged = _merge_media(canonical, duplicate)
            copied_primary += merged["copied_primary"]
            copied_gallery += merged["copied_gallery"]
            cards.validate(canonical)
            cards.put(str(canonical["product_id"]), canonical)

            duplicate_id = str(duplicate["product_id"])
            src = cards._product_path(duplicate_id)
            dest = archive / src.name
            if not src.is_file():
                raise RuntimeError(f"duplicate file missing before archive: {duplicate_id}")
            shutil.move(str(src), str(dest))
            duplicate_ids.add(duplicate_id)
            archive_manifest.append({
                "kind": "duplicate",
                "archived_product_id": duplicate_id,
                "archived_slug": item["duplicate_slug"],
                "canonical_product_id": str(canonical["product_id"]),
                "canonical_slug": item["canonical_slug"],
                "archive_path": str(dest.relative_to(cards.BASE)),
            })

        example = _full_card_by_slug(EXAMPLE_SLUG)
        if not isinstance(example, dict):
            raise RuntimeError("example-product disappeared before apply")
        example_id = str(example["product_id"])
        src = cards._product_path(example_id)
        dest = archive / src.name
        if not src.is_file():
            raise RuntimeError("example-product file missing before archive")
        shutil.move(str(src), str(dest))
        duplicate_ids.add(example_id)
        archive_manifest.append({
            "kind": "example",
            "archived_product_id": example_id,
            "archived_slug": EXAMPLE_SLUG,
            "archive_path": str(dest.relative_to(cards.BASE)),
        })

        kept_map = []
        for row in map_rows:
            pid = str(row.get("product_id") or "")
            if pid in duplicate_ids:
                removed_mapping_rows += 1
                continue
            kept_map.append(row)
        cmap["products"] = kept_map
        cards._save(cards.COMMERCE_MAP, cmap)
        cards._rebuild_index()

        (archive / "manifest.json").write_text(
            json.dumps(archive_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if _snapshot_tables() != db_before:
            raise RuntimeError("commerce DB changed during Product Card v3 cleanup")

        after_rows = cards.list_cards()
        if len(after_rows) != EXPECTED_AFTER:
            raise RuntimeError(
                f"expected {EXPECTED_AFTER} cards after cleanup; got {len(after_rows)}"
            )

        for slug in list(DUPLICATES) + [EXAMPLE_SLUG]:
            if any(str(x.get("slug") or "") == slug for x in after_rows):
                raise RuntimeError(f"archived slug still present in runtime index: {slug}")

        for slug in DUPLICATES.values():
            if not _full_card_by_slug(slug):
                raise RuntimeError(f"canonical card missing after cleanup: {slug}")

    except Exception:
        _restore_backup(backup)
        print("AUTO ROLLBACK:", backup)
        print("AUTO ROLLBACK RESULT: PASS")
        raise

    return {
        "status": "PASS",
        "archived": 10,
        "cards_after": len(cards.list_cards()),
        "copied_primary": copied_primary,
        "copied_gallery": copied_gallery,
        "removed_mapping_rows": removed_mapping_rows,
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
    path = REPORT_ROOT / f"pcv3-cleanup-10-{_stamp()}.json"
    payload = {
        "schema_version": "1.0",
        "mode": "APPLY_SAFE" if args.apply_safe else "DRY_RUN",
        "plan": plan,
        "apply": result,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("BB610 PRODUCT CARD V3 — SURPLUS 10 CLEANUP")
    print("MODE:", payload["mode"])
    print("CARDS BEFORE:", plan["cards_before"])
    print("SAFE DUPLICATES:", len(plan["safe_duplicates"]))
    print("BLOCKED:", len(plan["blocked"]))
    for item in plan["safe_duplicates"]:
        print(
            "SAFE:",
            item["duplicate_slug"],
            "=>",
            item["canonical_slug"],
            "| mapping:",
            item["mapping_note"],
        )
    for item in plan["blocked"]:
        print("BLOCKED:", item.get("duplicate_slug"), "|", item.get("reason"))
    print(
        "EXAMPLE:",
        "SAFE" if plan["example"].get("safe") else "BLOCKED",
        "|",
        plan["example"].get("reason") or "blank non-commerce example",
    )

    if result:
        print("RESULT:", result["status"])
        print("ARCHIVED:", result["archived"])
        print("CARDS AFTER:", result["cards_after"])
        print("PRIMARY MEDIA RECOVERED:", result["copied_primary"])
        print("GALLERY MEDIA RECOVERED:", result["copied_gallery"])
        print("REDUNDANT COMMERCE MAP ROWS REMOVED:", result["removed_mapping_rows"])
        print(
            "COMMERCE DB UNCHANGED:",
            "PASS" if result["commerce_db_unchanged"] else "FAIL",
        )
        print("BACKUP:", result["backup_dir"])
        print("ARCHIVE:", result["archive_dir"])

    print("REPORT:", path)
    if plan["blocked"] or not plan["example"].get("safe"):
        raise SystemExit(2)
    print("RESULT: PASS" if not result else "FINAL CLEANUP: 10/10 PASS")


if __name__ == "__main__":
    main()
