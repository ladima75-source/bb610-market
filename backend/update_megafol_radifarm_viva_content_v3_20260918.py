from __future__ import annotations

"""Content-only Product Card v3 update for MEGAFOL + RADIFARM + VIVA.

Protected invariants:
- product_id, slug, card enabled, brand/category;
- sku_media byte-for-structure;
- commerce_map and sku_commerce.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "data" / "product_content" / "megafol_radifarm_viva_20260918.json"
BACKUP_ROOT = ROOT / "var" / "content_backups"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PRODUCTS = 3
MANAGED_FIELDS = (
    "title", "short_description", "description", "benefits", "how_it_works",
    "application", "composition", "characteristics", "seo",
)


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower().replace("™", "").replace("®", "")
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text)


def _hash_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_manifest() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if doc.get("schema_version") != "1.0":
        raise RuntimeError("unexpected content manifest schema_version")
    products = doc.get("products")
    if not isinstance(products, list) or len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} content products; got {len(products or [])}")

    seen: set[str] = set()
    for i, row in enumerate(products):
        if not isinstance(row, dict):
            raise RuntimeError(f"products[{i}] must be an object")
        slug = str(row.get("slug") or "").strip().lower()
        if not slug or slug in seen:
            raise RuntimeError(f"invalid/duplicate slug at products[{i}]: {slug!r}")
        seen.add(slug)
        titles = row.get("match_titles")
        if not isinstance(titles, list) or not titles or any(not isinstance(x, str) or not x.strip() for x in titles):
            raise RuntimeError(f"{slug}: match_titles must be a non-empty string list")
        sources = row.get("sources")
        if not isinstance(sources, list) or not sources or any(not isinstance(x, str) or not x.startswith("https://") for x in sources):
            raise RuntimeError(f"{slug}: sources must contain https URLs")
        content = row.get("content")
        if not isinstance(content, dict) or set(content) != set(MANAGED_FIELDS):
            raise RuntimeError(f"{slug}: content must contain exactly managed fields")
        for key in ("title", "short_description", "description", "how_it_works", "application", "composition"):
            if not isinstance(content.get(key), str) or not content[key].strip():
                raise RuntimeError(f"{slug}: {key} must be non-empty")
        if not isinstance(content.get("benefits"), list) or len(content["benefits"]) < 4:
            raise RuntimeError(f"{slug}: at least four benefits are required")
        if not isinstance(content.get("characteristics"), list) or len(content["characteristics"]) < 5:
            raise RuntimeError(f"{slug}: at least five characteristics are required")
        seo = content.get("seo")
        if not isinstance(seo, dict) or set(seo) != {"title", "description"}:
            raise RuntimeError(f"{slug}: invalid seo object")
        if not str(seo.get("title") or "").strip() or not str(seo.get("description") or "").strip():
            raise RuntimeError(f"{slug}: SEO title/description must be non-empty")
    if seen != {"megafol", "radifarm", "viva"}:
        raise RuntimeError(f"unexpected target set: {sorted(seen)}")
    return doc


def _services():
    from backend.services import product_cards_v3 as pcv3
    return pcv3


def apply_content(card: dict, spec: dict) -> dict:
    out = deepcopy(card)
    content = out.get("content")
    if not isinstance(content, dict):
        raise RuntimeError("card has no content object")
    managed = spec.get("content")
    if not isinstance(managed, dict):
        raise RuntimeError("spec has no content object")
    for key in MANAGED_FIELDS:
        content[key] = deepcopy(managed[key])
    return out


def _find_current_card(pcv3, spec: dict) -> dict:
    slug = str(spec["slug"]).strip().lower()
    rows = pcv3.list_cards()
    by_slug = [x for x in rows if str(x.get("slug") or "").strip().lower() == slug]
    if len(by_slug) == 1:
        card = pcv3.get(str(by_slug[0].get("product_id") or ""))
        if isinstance(card, dict):
            return card
    if len(by_slug) > 1:
        raise RuntimeError(f"{slug}: duplicate current slug")

    wanted_titles = {_norm(x) for x in spec.get("match_titles") or []}
    wanted_titles.add(_norm((spec.get("content") or {}).get("title")))
    matches = [x for x in rows if _norm(x.get("title")) in wanted_titles]
    if len(matches) != 1:
        raise RuntimeError(f"{slug}: current card not found uniquely by slug/title; matches={len(matches)}")
    card = pcv3.get(str(matches[0].get("product_id") or ""))
    if not isinstance(card, dict):
        raise RuntimeError(f"{slug}: resolved card file is missing")
    return card


def preflight() -> dict:
    pcv3 = _services()
    manifest = load_manifest()
    targets: list[dict] = []
    seen_pids: set[str] = set()

    for spec in manifest["products"]:
        current = _find_current_card(pcv3, spec)
        pid = str(current.get("product_id") or "")
        if not pid or pid in seen_pids:
            raise RuntimeError(f"{spec['slug']}: invalid/duplicate product_id {pid!r}")
        seen_pids.add(pid)
        before = deepcopy(current)
        after = apply_content(current, spec)

        for key in ("product_id", "slug", "enabled"):
            if after.get(key) != before.get(key):
                raise RuntimeError(f"{spec['slug']}: protected {key} changed")
        for key in ("brand", "category"):
            if (after.get("content") or {}).get(key) != (before.get("content") or {}).get(key):
                raise RuntimeError(f"{spec['slug']}: protected content.{key} changed")
        if after.get("sku_media") != before.get("sku_media"):
            raise RuntimeError(f"{spec['slug']}: sku_media changed during content overlay")

        pcv3.validate(after)
        targets.append({
            "requested_slug": spec["slug"],
            "runtime_slug": before.get("slug"),
            "product_id": pid,
            "old_title": (before.get("content") or {}).get("title"),
            "new_title": (after.get("content") or {}).get("title"),
            "before": before,
            "after": after,
            "sku_media_hash": _hash_json(before.get("sku_media")),
        })

    return {"batch": manifest.get("batch"), "language": manifest.get("language"), "targets": targets}


def _backup_file(src: Path, backup_dir: Path) -> None:
    if not src.exists():
        raise RuntimeError(f"backup source missing: {src}")
    dst = backup_dir / src.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _restore_file(original: Path, backup_dir: Path) -> None:
    src = backup_dir / original.relative_to(ROOT)
    if src.exists():
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, original)


def apply_plan(plan: dict) -> dict:
    pcv3 = _services()
    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"megafol-radifarm-viva-content-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    commerce_before = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    paths = [pcv3._product_path(x["product_id"]) for x in plan["targets"]]
    for path in paths:
        _backup_file(path, backup_dir)
    if pcv3.INDEX.exists():
        _backup_file(pcv3.INDEX, backup_dir)
    if pcv3.COMMERCE_MAP.exists():
        _backup_file(pcv3.COMMERCE_MAP, backup_dir)

    changed = 0
    try:
        for target in plan["targets"]:
            if target["before"].get("content") != target["after"].get("content"):
                changed += 1
            pcv3.put(target["product_id"], target["after"])

        commerce_after = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if commerce_after != commerce_before:
            raise RuntimeError("commerce_map changed during content-only apply")

        for target in plan["targets"]:
            live = pcv3.get(target["product_id"])
            if not isinstance(live, dict):
                raise RuntimeError(f"post-verify card missing: {target['product_id']}")
            if live.get("content") != target["after"].get("content"):
                raise RuntimeError(f"post-verify content mismatch: {target['requested_slug']}")
            if live.get("sku_media") != target["before"].get("sku_media"):
                raise RuntimeError(f"post-verify sku_media changed: {target['requested_slug']}")
            if _hash_json(live.get("sku_media")) != target["sku_media_hash"]:
                raise RuntimeError(f"post-verify sku_media hash changed: {target['requested_slug']}")
            for key in ("product_id", "slug", "enabled"):
                if live.get(key) != target["before"].get(key):
                    raise RuntimeError(f"post-verify protected {key} changed: {target['requested_slug']}")

        return {
            "status": "PASS",
            "updated": len(plan["targets"]),
            "changed": changed,
            "backup_dir": str(backup_dir),
            "commerce_map_changed": False,
        }
    except Exception:
        for path in paths:
            _restore_file(path, backup_dir)
        _restore_file(pcv3.INDEX, backup_dir)
        _restore_file(pcv3.COMMERCE_MAP, backup_dir)
        raise


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"megafol-radifarm-viva-content-{stamp()}.json"
    payload = {
        "mode": mode,
        "batch": plan.get("batch"),
        "language": plan.get("language"),
        "targets": [
            {
                "requested_slug": x["requested_slug"],
                "runtime_slug": x["runtime_slug"],
                "product_id": x["product_id"],
                "old_title": x["old_title"],
                "new_title": x["new_title"],
                "sku_media_hash": x["sku_media_hash"],
            }
            for x in plan["targets"]
        ],
        "result": result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def print_plan(plan: dict) -> None:
    print("BB610 PRODUCT CARD V3 CONTENT — MEGAFOL + RADIFARM + VIVA")
    print(f"TARGET CARDS: {len(plan['targets'])}")
    for row in plan["targets"]:
        print(
            f"CONTENT {row['requested_slug']} -> {row['runtime_slug']} | {row['product_id']} | "
            f"{row['old_title']} => {row['new_title']}"
        )
    print("PROTECTED: product_id / slug / enabled / brand / category / SKU / media / commerce")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    plan = preflight()
    print_plan(plan)
    if not args.apply:
        report = write_report(plan, None, "DRY_RUN")
        print("RESULT: PASS (DRY_RUN)")
        print(f"REPORT: {report}")
        return 0

    result = apply_plan(plan)
    report = write_report(plan, result, "APPLY")
    print(f"RESULT: {result['status']}")
    print(f"UPDATED: {result['updated']}")
    print(f"CHANGED: {result['changed']}")
    print(f"COMMERCE_MAP_CHANGED: {str(result['commerce_map_changed']).lower()}")
    print(f"BACKUP_DIR: {result['backup_dir']}")
    print(f"REPORT: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
