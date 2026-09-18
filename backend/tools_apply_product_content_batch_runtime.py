from __future__ import annotations

"""Generic content-only Product Card v3 batch updater.

This tool applies reviewed content batches to runtime Product Card v3 files while
protecting product identity, SKU/media and all commerce state. It is intended for
production-created cards that are not stored in the clean Git checkout.
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

from backend.services import product_cards_v3 as pcv3
from backend import update_stage22c_batch03_content_v3_20260918 as content_base

BACKUP_ROOT = ROOT / "var" / "content_backups"
REPORT_ROOT = ROOT / "var" / "reports"
MANAGED_FIELDS = (
    "title", "short_description", "description", "benefits", "how_it_works",
    "application", "composition", "characteristics", "seo",
)


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _norm(value: Any) -> str:
    s = str(value or "").strip().lower().replace("™", "").replace("®", "")
    s = s.replace("–", "-").replace("—", "-").replace("ё", "е")
    return re.sub(r"\s+", " ", s)


def _hash_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return s or "content-batch"


def load_batch(manifest_path: str | Path) -> dict:
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = ROOT / manifest_file
    meta = json.loads(manifest_file.read_text(encoding="utf-8"))
    if meta.get("schema_version") != "1.0":
        raise RuntimeError("unexpected manifest schema_version")

    source_file = ROOT / str(meta.get("source_batch") or "")
    source_rows = json.loads(source_file.read_text(encoding="utf-8"))
    if not isinstance(source_rows, list):
        raise RuntimeError("source batch must be a list")

    expected = [int(x) for x in (meta.get("expected_source_rows") or [])]
    if not expected or len(expected) != len(set(expected)):
        raise RuntimeError("expected_source_rows must be a non-empty unique list")

    by_row = {
        int(x.get("source_row")): x
        for x in source_rows
        if isinstance(x, dict) and x.get("source_row") is not None
    }
    missing = [x for x in expected if x not in by_row]
    if missing:
        raise RuntimeError(f"source rows missing from batch: {missing}")

    rows = [by_row[x] for x in expected]
    names = [_norm(x.get("name")) for x in rows]
    if any(not x for x in names) or len(names) != len(set(names)):
        raise RuntimeError("selected source rows contain empty/duplicate names")

    target_count = int(meta.get("expected_target_count") or len(expected))
    if target_count != len(rows):
        raise RuntimeError(
            f"expected_target_count={target_count} but selected rows={len(rows)}"
        )
    return {
        "manifest_file": manifest_file,
        "meta": meta,
        "rows": rows,
    }


def _mapping_for_legacy_id(legacy_id: str) -> list[dict]:
    return [
        x for x in (pcv3.commerce_map().get("products") or [])
        if isinstance(x, dict)
        and str(x.get("existing_product_key") or "").strip() == legacy_id
    ]


def _card_from_index_row(row: dict) -> dict | None:
    card = pcv3.get(str(row.get("product_id") or ""))
    return card if isinstance(card, dict) else None


def resolve_current_card(row: dict, meta: dict) -> dict:
    source_row = int(row["source_row"])
    source_name = str(row.get("name") or "").strip()
    managed_title = str(content_base.build_content(row).get("title") or "").strip()

    legacy_map = meta.get("legacy_id_by_source_row") or {}
    legacy_id = str(legacy_map.get(str(source_row)) or legacy_map.get(source_row) or "").strip()
    if legacy_id:
        mapped = _mapping_for_legacy_id(legacy_id)
        if len(mapped) == 1:
            card = pcv3.get(str(mapped[0].get("product_id") or ""))
            if isinstance(card, dict):
                return card
        elif len(mapped) > 1:
            raise RuntimeError(
                f"row {source_row} {source_name}: duplicate commerce mappings for {legacy_id}"
            )

    slug_map = meta.get("slug_candidates_by_source_row") or {}
    slug_candidates = slug_map.get(str(source_row)) or slug_map.get(source_row) or []
    if isinstance(slug_candidates, str):
        slug_candidates = [slug_candidates]
    wanted_slugs = {str(x).strip().lower() for x in slug_candidates if str(x).strip()}
    if wanted_slugs:
        slug_hits = [
            x for x in pcv3.list_cards()
            if str(x.get("slug") or "").strip().lower() in wanted_slugs
        ]
        if len(slug_hits) == 1:
            card = _card_from_index_row(slug_hits[0])
            if card:
                return card
        if len(slug_hits) > 1:
            raise RuntimeError(
                f"row {source_row} {source_name}: duplicate slug candidates"
            )

    alias_map = meta.get("title_aliases_by_source_row") or {}
    aliases = alias_map.get(str(source_row)) or alias_map.get(source_row) or []
    if isinstance(aliases, str):
        aliases = [aliases]
    wanted_titles = {
        _norm(source_name),
        _norm(managed_title),
        *[_norm(x) for x in aliases if str(x).strip()],
    }
    wanted_titles.discard("")

    title_hits = [
        x for x in pcv3.list_cards()
        if _norm(x.get("title")) in wanted_titles
    ]
    if len(title_hits) == 1:
        card = _card_from_index_row(title_hits[0])
        if card:
            return card
    if len(title_hits) > 1:
        raise RuntimeError(
            f"row {source_row} {source_name}: title aliases resolve to multiple cards"
        )

    raise RuntimeError(
        f"row {source_row} {source_name}: Product Card v3 not resolved uniquely; "
        f"legacy_id={legacy_id or '-'} slug_hits=0 title_hits={len(title_hits)}"
    )


def build_plan(manifest_path: str | Path) -> dict:
    source = load_batch(manifest_path)
    meta = source["meta"]
    targets: list[dict] = []
    seen_pids: set[str] = set()

    for row in source["rows"]:
        current = resolve_current_card(row, meta)
        pid = str(current.get("product_id") or "").strip()
        if not pid or pid in seen_pids:
            raise RuntimeError(
                f"row {row.get('source_row')}: invalid/duplicate product_id {pid!r}"
            )
        seen_pids.add(pid)

        before = deepcopy(current)
        after = content_base.apply_content(current, row)

        for key in ("product_id", "slug", "enabled"):
            if after.get(key) != before.get(key):
                raise RuntimeError(
                    f"row {row.get('source_row')}: protected {key} changed"
                )
        for key in ("brand", "category"):
            if (after.get("content") or {}).get(key) != (before.get("content") or {}).get(key):
                raise RuntimeError(
                    f"row {row.get('source_row')}: protected content.{key} changed"
                )
        if after.get("sku_media") != before.get("sku_media"):
            raise RuntimeError(
                f"row {row.get('source_row')}: sku_media changed during overlay"
            )

        pcv3.validate(after)
        targets.append({
            "source_row": int(row["source_row"]),
            "source_name": row["name"],
            "runtime_slug": before.get("slug"),
            "product_id": pid,
            "old_title": (before.get("content") or {}).get("title"),
            "new_title": (after.get("content") or {}).get("title"),
            "before": before,
            "after": after,
            "sku_media_hash": _hash_json(before.get("sku_media")),
        })

    expected = int(meta.get("expected_target_count") or len(source["rows"]))
    if len(targets) != expected:
        raise RuntimeError(f"expected {expected} resolved targets; got {len(targets)}")

    return {
        "batch": meta.get("batch"),
        "batch_id": _safe_id(str(meta.get("batch_id") or meta.get("batch") or "content-batch")),
        "manifest_file": str(source["manifest_file"]),
        "targets": targets,
    }


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
    backup_dir = BACKUP_ROOT / f"{plan['batch_id']}-{stamp()}"
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
                raise RuntimeError(
                    f"post-verify missing card: {target['source_name']}"
                )
            if live.get("content") != target["after"].get("content"):
                raise RuntimeError(
                    f"post-verify content mismatch: {target['source_name']}"
                )
            if live.get("sku_media") != target["before"].get("sku_media"):
                raise RuntimeError(
                    f"post-verify sku_media changed: {target['source_name']}"
                )
            if _hash_json(live.get("sku_media")) != target["sku_media_hash"]:
                raise RuntimeError(
                    f"post-verify sku_media hash changed: {target['source_name']}"
                )
            for key in ("product_id", "slug", "enabled"):
                if live.get(key) != target["before"].get(key):
                    raise RuntimeError(
                        f"post-verify protected {key} changed: {target['source_name']}"
                    )

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
    path = REPORT_ROOT / f"{plan['batch_id']}-{stamp()}.json"
    payload = {
        "mode": mode,
        "batch": plan.get("batch"),
        "manifest_file": plan.get("manifest_file"),
        "targets": [
            {
                k: x[k]
                for k in (
                    "source_row", "source_name", "runtime_slug", "product_id",
                    "old_title", "new_title", "sku_media_hash"
                )
            }
            for x in plan["targets"]
        ],
        "result": result,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def print_plan(plan: dict) -> None:
    print(f"BB610 PRODUCT CARD V3 CONTENT — {plan.get('batch')}")
    print(f"TARGET CARDS: {len(plan['targets'])}")
    for x in plan["targets"]:
        print(
            f"CONTENT row={x['source_row']} | {x['source_name']} -> "
            f"{x['runtime_slug']} | {x['product_id']} | "
            f"{x['old_title']} => {x['new_title']}"
        )
    print(
        "PROTECTED: product_id / slug / enabled / brand / category / "
        "SKU / media / commerce / prices"
    )


def self_test(manifest_path: str | Path) -> int:
    source = load_batch(manifest_path)

    class FakePCV3:
        def __init__(self, cards: list[dict]):
            self.cards = {x["product_id"]: deepcopy(x) for x in cards}

        def commerce_map(self):
            return {"products": []}

        def list_cards(self):
            return [
                {
                    "product_id": x["product_id"],
                    "slug": x["slug"],
                    "title": (x.get("content") or {}).get("title"),
                }
                for x in self.cards.values()
            ]

        def get(self, pid):
            value = self.cards.get(pid)
            return deepcopy(value) if value else None

    real_map = pcv3.commerce_map
    real_list = pcv3.list_cards
    real_get = pcv3.get
    try:
        for i, row in enumerate(source["rows"]):
            before = pcv3.empty_card(str(row["name"]), f"self-test-{i}")
            before["content"]["brand"] = str(row.get("brand") or "")
            before["content"]["category"] = str(row.get("category") or "nutrition")

            fake = FakePCV3([before])
            pcv3.commerce_map = fake.commerce_map
            pcv3.list_cards = fake.list_cards
            pcv3.get = fake.get
            resolved_before = resolve_current_card(row, {"legacy_id_by_source_row": {}})
            assert resolved_before["product_id"] == before["product_id"]

            after = content_base.apply_content(before, row)
            pcv3.validate(after)
            fake = FakePCV3([after])
            pcv3.commerce_map = fake.commerce_map
            pcv3.list_cards = fake.list_cards
            pcv3.get = fake.get
            resolved_after = resolve_current_card(row, {"legacy_id_by_source_row": {}})
            assert resolved_after["product_id"] == after["product_id"]

        print(f"CONTENT BATCH SELF-TEST: {len(source['rows'])}/{len(source['rows'])} PASS")
        return 0
    finally:
        pcv3.commerce_map = real_map
        pcv3.list_cards = real_list
        pcv3.get = real_get


def run(manifest_path: str | Path, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test(manifest_path)

    plan = build_plan(manifest_path)
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
