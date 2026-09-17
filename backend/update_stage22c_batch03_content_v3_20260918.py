from __future__ import annotations

"""Content-only Product Card v3 update for stage22c batch03 (rows 25-36).

The source content is the already-reviewed repository batch
`data/content_batches/stage22c_batch03_rows25_36.json`.
Only presentation content is changed. Product identity, routing, SKU/media,
commerce mapping and live commerce remain untouched.
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

MANIFEST = ROOT / "data" / "product_content" / "stage22c_batch03_20260918.json"
RUNTIME_CATALOG = ROOT / "data" / "catalog.runtime.js"
BACKUP_ROOT = ROOT / "var" / "content_backups"
REPORT_ROOT = ROOT / "var" / "reports"
PREFIX = "window.BB610_CATALOG = "
MANAGED_FIELDS = (
    "title", "short_description", "description", "benefits", "how_it_works",
    "application", "composition", "characteristics", "seo",
)
META_SPEC_LABELS = {
    "тип продукту", "форма", "препаративна форма", "бренд", "компанія",
    "виробник", "країна виробника", "бренд / торгова назва",
    "виробник у джерелі постачальника", "джерело даних",
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _norm(value: Any) -> str:
    s = str(value or "").strip().lower().replace("™", "").replace("®", "")
    s = s.replace("–", "-").replace("—", "-").replace("ё", "е")
    return re.sub(r"\s+", " ", s)


def _hash_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_manifest() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if doc.get("schema_version") != "1.0":
        raise RuntimeError("unexpected manifest schema_version")
    source = ROOT / str(doc.get("source_batch") or "")
    rows = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise RuntimeError("source batch must be a list")
    expected = [int(x) for x in (doc.get("expected_source_rows") or [])]
    actual = [int(x.get("source_row")) for x in rows if isinstance(x, dict)]
    if actual != expected or expected != list(range(25, 37)):
        raise RuntimeError(f"unexpected source rows: {actual}")
    if len(rows) != 12:
        raise RuntimeError(f"expected 12 products; got {len(rows)}")
    names = [_norm(x.get("name")) for x in rows]
    if any(not x for x in names) or len(names) != len(set(names)):
        raise RuntimeError("source batch has empty/duplicate product names")
    return {"meta": doc, "rows": rows}


def _clean_pairs(items: Any, first: str, second: str) -> list[dict]:
    out: list[dict] = []
    for row in items if isinstance(items, list) else []:
        if not isinstance(row, dict):
            continue
        a = str(row.get(first) or "").strip()
        b = str(row.get(second) or "").strip()
        if a and b:
            out.append({first: a, second: b})
    return out


def _application_text(row: dict) -> str:
    app = row.get("application") if isinstance(row.get("application"), dict) else {}
    parts: list[str] = []
    intro = str(app.get("intro") or "").strip()
    if intro:
        parts.append(intro)
    for item in app.get("rows") or []:
        if not isinstance(item, dict):
            continue
        crop = str(item.get("crop") or "").strip()
        period = str(item.get("period") or "").strip()
        dose = str(item.get("dose") or "").strip()
        left = " — ".join(x for x in (crop, period) if x)
        if left and dose:
            parts.append(f"{left}: {dose}.")
        elif left:
            parts.append(left + ".")
        elif dose:
            parts.append(dose + ".")
    note = str(app.get("note") or "").strip()
    if note:
        parts.append(note)
    return "\n\n".join(parts).strip()


def _composition_text(specs: list[dict]) -> str:
    useful: list[str] = []
    for item in specs:
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        if not label or not value:
            continue
        if _norm(label) in META_SPEC_LABELS:
            continue
        useful.append(f"{label}: {value}")
    if not useful:
        useful = [
            f"{str(x.get('label') or '').strip()}: {str(x.get('value') or '').strip()}"
            for x in specs if str(x.get("label") or "").strip() and str(x.get("value") or "").strip()
        ]
    return "\n".join(useful).strip()


def build_content(row: dict) -> dict:
    name = str(row.get("name") or "").strip()
    subtitle = str(row.get("subtitle") or "").strip()
    short = str(row.get("short_description") or row.get("lead") or "").strip()
    description = str(row.get("full_description") or short).strip()
    benefits = _clean_pairs(row.get("why"), "title", "text")
    how = row.get("how_it_works") if isinstance(row.get("how_it_works"), dict) else {}
    how_text = str(how.get("text") or "").strip()
    specs = _clean_pairs(row.get("specs"), "label", "value")
    application = _application_text(row)
    composition = _composition_text(specs)
    if not all((name, short, description, how_text, application, composition)):
        raise RuntimeError(f"source row {row.get('source_row')}: incomplete content")
    if not benefits:
        raise RuntimeError(f"source row {row.get('source_row')}: no benefits")
    if not specs:
        raise RuntimeError(f"source row {row.get('source_row')}: no characteristics")

    title = f"{name} — {subtitle}" if subtitle else name
    seo_title = f"{name} | BB610 Market"
    seo_description = short[:300]
    return {
        "title": title,
        "short_description": short,
        "description": description,
        "benefits": benefits,
        "how_it_works": how_text,
        "application": application,
        "composition": composition,
        "characteristics": specs,
        "seo": {"title": seo_title, "description": seo_description},
    }


def apply_content(card: dict, row: dict) -> dict:
    out = deepcopy(card)
    content = out.get("content")
    if not isinstance(content, dict):
        raise RuntimeError("card has no content object")
    managed = build_content(row)
    if set(managed) != set(MANAGED_FIELDS):
        raise RuntimeError("managed field contract mismatch")
    for key in MANAGED_FIELDS:
        content[key] = deepcopy(managed[key])
    return out


def _services():
    from backend.services import product_cards_v3 as pcv3
    return pcv3


def _runtime_catalog_products() -> list[dict]:
    raw = RUNTIME_CATALOG.read_text(encoding="utf-8").strip()
    if not raw.startswith(PREFIX):
        return []
    payload = raw[len(PREFIX):].strip()
    if payload.endswith(";"):
        payload = payload[:-1].rstrip()
    doc = json.loads(payload)
    return [x for x in (doc.get("products") or []) if isinstance(x, dict)] if isinstance(doc, dict) else []


def _find_current_card(pcv3, row: dict, runtime_products: list[dict]) -> dict:
    wanted = _norm(row.get("name"))

    # First resolve through the authoritative commerce mapping when possible.
    legacy_matches = [
        x for x in runtime_products
        if _norm(x.get("name") or x.get("official_name")) == wanted
    ]
    if len(legacy_matches) == 1:
        legacy_id = str(legacy_matches[0].get("id") or "").strip()
        mapped = [
            x for x in (pcv3.commerce_map().get("products") or [])
            if isinstance(x, dict) and str(x.get("existing_product_key") or "").strip() == legacy_id
        ]
        if len(mapped) == 1:
            card = pcv3.get(str(mapped[0].get("product_id") or ""))
            if isinstance(card, dict):
                return card
        elif len(mapped) > 1:
            raise RuntimeError(f"{row.get('name')}: duplicate commerce mappings")

    # Safe fallback: exact normalized current title only.
    rows = pcv3.list_cards()
    matches = [x for x in rows if _norm(x.get("title")) == wanted]
    if len(matches) != 1:
        raise RuntimeError(
            f"{row.get('name')}: current Product Card v3 not resolved uniquely; "
            f"legacy_matches={len(legacy_matches)} title_matches={len(matches)}"
        )
    card = pcv3.get(str(matches[0].get("product_id") or ""))
    if not isinstance(card, dict):
        raise RuntimeError(f"{row.get('name')}: resolved card missing")
    return card


def preflight() -> dict:
    pcv3 = _services()
    source = load_manifest()
    runtime_products = _runtime_catalog_products()
    targets: list[dict] = []
    seen_pids: set[str] = set()

    for row in source["rows"]:
        current = _find_current_card(pcv3, row, runtime_products)
        pid = str(current.get("product_id") or "").strip()
        if not pid or pid in seen_pids:
            raise RuntimeError(f"{row.get('name')}: invalid/duplicate product_id {pid!r}")
        seen_pids.add(pid)
        before = deepcopy(current)
        after = apply_content(current, row)

        for key in ("product_id", "slug", "enabled"):
            if after.get(key) != before.get(key):
                raise RuntimeError(f"{row.get('name')}: protected {key} changed")
        for key in ("brand", "category"):
            if (after.get("content") or {}).get(key) != (before.get("content") or {}).get(key):
                raise RuntimeError(f"{row.get('name')}: protected content.{key} changed")
        if after.get("sku_media") != before.get("sku_media"):
            raise RuntimeError(f"{row.get('name')}: sku_media changed")

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

    if len(targets) != 12:
        raise RuntimeError(f"expected 12 resolved targets; got {len(targets)}")
    return {"batch": source["meta"].get("batch"), "targets": targets}


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
    backup_dir = BACKUP_ROOT / f"stage22c-batch03-content-{stamp()}"
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
                raise RuntimeError(f"post-verify missing card: {target['source_name']}")
            if live.get("content") != target["after"].get("content"):
                raise RuntimeError(f"post-verify content mismatch: {target['source_name']}")
            if live.get("sku_media") != target["before"].get("sku_media"):
                raise RuntimeError(f"post-verify sku_media changed: {target['source_name']}")
            if _hash_json(live.get("sku_media")) != target["sku_media_hash"]:
                raise RuntimeError(f"post-verify sku_media hash changed: {target['source_name']}")
            for key in ("product_id", "slug", "enabled"):
                if live.get(key) != target["before"].get(key):
                    raise RuntimeError(f"post-verify protected {key} changed: {target['source_name']}")

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
    path = REPORT_ROOT / f"stage22c-batch03-content-{stamp()}.json"
    payload = {
        "mode": mode,
        "batch": plan.get("batch"),
        "targets": [
            {k: x[k] for k in ("source_row", "source_name", "runtime_slug", "product_id", "old_title", "new_title", "sku_media_hash")}
            for x in plan["targets"]
        ],
        "result": result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def print_plan(plan: dict) -> None:
    print("BB610 PRODUCT CARD V3 CONTENT — STAGE22C BATCH03 ROWS25-36")
    print(f"TARGET CARDS: {len(plan['targets'])}")
    for x in plan["targets"]:
        print(
            f"CONTENT row={x['source_row']} | {x['source_name']} -> {x['runtime_slug']} | "
            f"{x['product_id']} | {x['old_title']} => {x['new_title']}"
        )
    print("PROTECTED: product_id / slug / enabled / brand / category / SKU / media / commerce / prices")


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
