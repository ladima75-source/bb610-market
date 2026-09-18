from __future__ import annotations

"""Complete exact primary media only for the current visible PCV3 scope.

Scope is identical to tools_repair_visible_pcv3_structural_20260918.py:
- enabled Product Card v3;
- excludes Plantlogic;
- excludes temporarily hidden "Захист рослин".

The tool reuses the audited pcv3_preprice_media_manifest_v1 + R3 exact-product
resolver. It never changes commerce, price, stock, availability, publication,
mapping, content, SKU identity, or galleries.

Default mode is network preflight only. --apply-safe writes only local media
files and primary_media_id assignments after ALL current scoped missing-photo
products have resolved successfully in memory.
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
from backend.tools_complete_pcv3_preprice_web_media import (
    MANIFEST,
    RUNTIME_MEDIA,
    _load_json,
    _media_id,
    _safe_slug,
    _sha256,
)
from backend.tools_complete_pcv3_preprice_web_media_r3 import _resolve_r3
from backend.tools_prepare_pcv3_release import _snapshot_tables
from backend.tools_repair_visible_pcv3_structural_20260918 import (
    card_exclusion,
    catalog_indexes,
    load_authoritative_catalog,
    mapping_index,
)

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def scoped_cards() -> tuple[list[dict], list[dict]]:
    catalog = load_authoritative_catalog()
    by_id, _by_slug, _sku_by_product = catalog_indexes(catalog)
    mappings = mapping_index()

    scope: list[dict] = []
    excluded: list[dict] = []
    for summary in cards.list_cards():
        pid = str(summary.get("product_id") or "")
        card = cards.get(pid)
        if not isinstance(card, dict):
            excluded.append({"product_id": pid, "reason": "card_file_missing"})
            continue
        mapping = mappings.get(pid)
        reason = card_exclusion(card, mapping, by_id)
        if reason:
            excluded.append({"product_id": pid, "slug": card.get("slug"), "reason": reason})
            continue
        if not card.get("enabled", False):
            excluded.append({"product_id": pid, "slug": card.get("slug"), "reason": "card_disabled"})
            continue
        scope.append(card)
    return scope, excluded


def enabled_skus(card: dict) -> list[dict]:
    return [
        x for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict) and x.get("enabled") is not False
    ]


def valid_primary(card: dict, sku: dict) -> bool:
    media = {
        str(x.get("media_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }
    row = media.get(str(sku.get("primary_media_id") or ""))
    path = str((row or {}).get("path") or "").strip()
    return bool(isinstance(row, dict) and path and _is_resolvable(path))


def missing_photo_products(scope: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for card in scope:
        missing = [
            str(sku.get("sku_id") or "")
            for sku in enabled_skus(card)
            if not valid_primary(card, sku)
        ]
        if missing:
            out[str(card.get("product_id") or "")] = {
                "card": card,
                "missing_sku_ids": missing,
            }
    return out


def load_manifest_rows() -> dict[str, dict]:
    manifest = _load_json(MANIFEST)
    rows = [x for x in (manifest.get("products") or []) if isinstance(x, dict)]
    by_pid = {str(x.get("product_id") or ""): x for x in rows}
    if len(by_pid) != len(rows):
        raise RuntimeError("duplicate product_id in exact-media manifest")
    return by_pid


def preflight() -> dict:
    scope, excluded = scoped_cards()
    missing = missing_photo_products(scope)
    manifest = load_manifest_rows()

    uncovered = sorted(set(missing) - set(manifest))
    if uncovered:
        raise RuntimeError(
            "exact-media manifest does not cover scoped missing products: "
            + ", ".join(uncovered)
        )

    resolved: dict[str, tuple[bytes, str, str, str]] = {}
    failures: dict[str, str] = {}
    for pid in sorted(missing):
        row = manifest[pid]
        try:
            resolved[pid] = _resolve_r3(row)
            print("RESOLVED:", pid, "|", str(row.get("title") or ""))
        except Exception as exc:
            failures[pid] = str(exc)
            print("UNRESOLVED:", pid, "|", str(row.get("title") or ""), "|", exc)

    result = {
        "scope_cards": len(scope),
        "excluded": len(excluded),
        "products_with_gaps": len(missing),
        "sku_gaps": sum(len(x["missing_sku_ids"]) for x in missing.values()),
        "manifest_products": len(manifest),
        "resolved_products": len(resolved),
        "failures": failures,
        "missing": missing,
        "resolved": resolved,
    }

    print("VISIBLE PCV3 EXACT MEDIA PREFLIGHT")
    print("SCOPE CARDS:", result["scope_cards"])
    print("EXCLUDED:", result["excluded"])
    print("PRODUCTS WITH MEDIA GAPS:", result["products_with_gaps"])
    print("SKU MEDIA GAPS:", result["sku_gaps"])
    print("MANIFEST PRODUCTS:", result["manifest_products"])
    print("PREFLIGHT RESOLVED:", result["resolved_products"], "/", result["products_with_gaps"])
    print("PREFLIGHT UNRESOLVED:", len(failures))
    if failures:
        print("RESULT: FAIL")
    else:
        print("RESULT: PASS")
    return result


def _backup_cards(ts: str) -> Path:
    dest = BACKUP_ROOT / f"visible-pcv3-exact-media-{ts}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        # Same-second retry or interrupted previous attempt: never overwrite a
        # backup. Allocate a deterministic unique suffix instead.
        n = 2
        while True:
            candidate = BACKUP_ROOT / f"visible-pcv3-exact-media-{ts}-{n}"
            if not candidate.exists():
                dest = candidate
                break
            n += 1
    dest.mkdir(parents=False, exist_ok=False)
    shutil.copytree(cards.BASE, dest / "product_cards_v3")
    return dest


def _restore_cards(backup: Path) -> None:
    src = backup / "product_cards_v3"
    if not src.is_dir():
        raise RuntimeError(f"backup missing: {src}")
    if cards.BASE.exists():
        shutil.rmtree(cards.BASE)
    shutil.copytree(src, cards.BASE)
    cards.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply_safe(plan: dict) -> dict:
    if plan["failures"]:
        raise RuntimeError("preflight has unresolved exact-media sources")
    if plan["resolved_products"] != plan["products_with_gaps"]:
        raise RuntimeError("preflight is incomplete")

    before_db = _snapshot_tables()
    cmap_before = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b""
    ts = stamp()
    backup = _backup_cards(ts)
    created_files: list[Path] = []
    changed_cards = 0
    assigned_skus = 0
    provenance: list[dict[str, Any]] = []

    try:
        RUNTIME_MEDIA.mkdir(parents=True, exist_ok=True)

        for pid in sorted(plan["missing"]):
            card = cards.get(pid)
            if not isinstance(card, dict):
                raise RuntimeError(f"{pid}: card disappeared after preflight")

            before_missing = [
                sku for sku in enabled_skus(card)
                if not valid_primary(card, sku)
            ]
            if not before_missing:
                continue

            data, resolved_url, source_page, kind = plan["resolved"][pid]
            digest = _sha256(data)
            filename = (
                f"pcv3-source-{_safe_slug(str(card.get('slug') or pid))}-"
                f"{digest[:10]}.{kind}"
            )
            physical = RUNTIME_MEDIA / filename
            local_path = f"media/products/{filename}"

            if not physical.exists():
                physical.write_bytes(data)
                created_files.append(physical)
            elif _sha256(physical.read_bytes()) != digest:
                raise RuntimeError(f"{pid}: local media hash collision")

            if not _is_resolvable(local_path):
                raise RuntimeError(f"{pid}: local media not resolvable: {local_path}")

            work = deepcopy(card)
            sm = work.get("sku_media") or {}
            media = sm.setdefault("media", [])
            title = str((work.get("content") or {}).get("title") or pid)

            entry = next(
                (
                    x for x in media
                    if isinstance(x, dict)
                    and str(x.get("path") or "") == local_path
                ),
                None,
            )
            if not entry:
                entry = {
                    "media_id": _media_id(local_path),
                    "path": local_path,
                    "alt": title,
                    "kind": "product",
                    "sort_order": len(media),
                }
                media.append(entry)
            elif not str(entry.get("alt") or "").strip():
                entry["alt"] = title

            assigned: list[str] = []
            for sku in enabled_skus(work):
                if valid_primary(work, sku):
                    continue
                sku["primary_media_id"] = entry["media_id"]
                assigned.append(str(sku.get("sku_id") or ""))
                assigned_skus += 1

            if not assigned:
                raise RuntimeError(f"{pid}: no missing SKU primary media remained")

            cards.validate(work)
            cards.put(pid, work)
            changed_cards += 1
            row = load_manifest_rows()[pid]
            provenance.append({
                "product_id": pid,
                "title": title,
                "quality": row.get("quality"),
                "source_page": source_page or ((row.get("source_pages") or [""])[0]),
                "resolved_image_url": resolved_url,
                "local_path": local_path,
                "sha256": digest,
                "bytes": len(data),
                "assigned_sku_ids": assigned,
            })

        after_db = _snapshot_tables()
        cmap_after = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b""
        if before_db != after_db:
            raise RuntimeError("commerce/database changed during exact-media apply")
        if cmap_before != cmap_after:
            raise RuntimeError("commerce_map changed during exact-media apply")

        scope_after, _excluded_after = scoped_cards()
        remaining = missing_photo_products(scope_after)
        if remaining:
            raise RuntimeError(
                "scoped media gaps remain after apply: "
                + ", ".join(sorted(remaining))
            )

        result = {
            "status": "PASS",
            "changed_cards": changed_cards,
            "assigned_skus": assigned_skus,
            "backup_dir": str(backup),
            "remaining_products": 0,
            "commerce_unchanged": True,
            "provenance": provenance,
        }

        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        report = REPORT_ROOT / f"visible-pcv3-exact-media-{ts}.json"
        report.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result["report"] = str(report)
        return result

    except Exception:
        _restore_cards(backup)
        for path in created_files:
            try:
                path.unlink()
            except Exception:
                pass
        if _snapshot_tables() != before_db:
            raise RuntimeError("rollback restored cards but commerce DB changed externally")
        if (cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b"") != cmap_before:
            raise RuntimeError("rollback restored cards but commerce_map changed externally")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = preflight()
    if plan["failures"]:
        return 2

    if not args.apply_safe:
        return 0

    result = apply_safe(plan)
    print("VISIBLE PCV3 EXACT MEDIA APPLY")
    print("CHANGED CARDS:", result["changed_cards"])
    print("ASSIGNED SKU PRIMARY MEDIA:", result["assigned_skus"])
    print("REMAINING PRODUCTS:", result["remaining_products"])
    print("COMMERCE/PRICES UNCHANGED:", "PASS" if result["commerce_unchanged"] else "FAIL")
    print("BACKUP:", result["backup_dir"])
    print("REPORT:", result["report"])
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
