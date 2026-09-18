from __future__ import annotations

"""Read-only Product Card v3 content coverage audit.

Resolves every card already managed by the completed content batches, compares
that set with the actual runtime Product Card v3 index, and reports only cards
that are outside the managed 77-card content scope.

No files are mutated.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend import tools_apply_product_content_batch_runtime as engine

MASTER_PLANTAFOL = ROOT / "data" / "product_content" / "master_plantafol_20260918.json"
BIOSTIM = ROOT / "data" / "product_content" / "megafol_radifarm_viva_20260918.json"
STAGE22C_BATCH03 = ROOT / "data" / "product_content" / "stage22c_batch03_20260918.json"

REMAINING_MANIFESTS = [
    ROOT / "data" / "product_content" / "stage22c_remaining_rows12_24_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch04_remaining_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch05_remaining_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch06_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch07_20260918.json",
]

EXPECTED_MANAGED = 77


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_by_slug(slug: str, rows: list[dict]) -> dict:
    hits = [x for x in rows if str(x.get("slug") or "").strip() == str(slug).strip()]
    if len(hits) != 1:
        raise RuntimeError(f"slug {slug!r}: expected one runtime card, got {len(hits)}")
    pid = str(hits[0].get("product_id") or "").strip()
    card = pcv3.get(pid)
    if not isinstance(card, dict):
        raise RuntimeError(f"slug {slug!r}: product file missing for {pid!r}")
    return card


def collect_managed_cards() -> list[dict]:
    rows = pcv3.list_cards()
    managed: list[dict] = []
    seen: set[str] = set()

    for manifest in (MASTER_PLANTAFOL, BIOSTIM):
        doc = _load_json(manifest)
        products = doc.get("products") or []
        if not isinstance(products, list):
            raise RuntimeError(f"{manifest.name}: products must be a list")
        for item in products:
            slug = str((item or {}).get("slug") or "").strip()
            if not slug:
                raise RuntimeError(f"{manifest.name}: empty slug")
            card = _resolve_by_slug(slug, rows)
            pid = str(card.get("product_id") or "").strip()
            if pid in seen:
                raise RuntimeError(f"duplicate managed product_id {pid}")
            seen.add(pid)
            managed.append(card)

    # Stage22c batch03 was already applied and is idempotently resolvable by
    # source name or the managed post-apply title.
    plan03 = engine.build_plan(STAGE22C_BATCH03)
    for target in plan03["targets"]:
        pid = str(target["product_id"])
        if pid in seen:
            raise RuntimeError(f"duplicate managed product_id {pid}")
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f"batch03 missing product {pid}")
        seen.add(pid)
        managed.append(card)

    for manifest in REMAINING_MANIFESTS:
        plan = engine.build_plan(manifest)
        for target in plan["targets"]:
            pid = str(target["product_id"])
            if pid in seen:
                raise RuntimeError(f"duplicate managed product_id {pid}")
            card = pcv3.get(pid)
            if not isinstance(card, dict):
                raise RuntimeError(f"{manifest.name}: missing product {pid}")
            seen.add(pid)
            managed.append(card)

    if len(managed) != EXPECTED_MANAGED:
        raise RuntimeError(
            f"managed content coverage expected {EXPECTED_MANAGED}; got {len(managed)}"
        )
    return managed


def main() -> int:
    runtime_rows = pcv3.list_cards()
    managed = collect_managed_cards()
    managed_ids = {str(x.get("product_id") or "") for x in managed}

    uncovered_rows = [
        x for x in runtime_rows
        if str(x.get("product_id") or "") not in managed_ids
    ]

    print("BB610 PRODUCT CARD V3 CONTENT COVERAGE AUDIT")
    print(f"RUNTIME CARDS: {len(runtime_rows)}")
    print(f"MANAGED CONTENT CARDS: {len(managed_ids)}")
    print(f"UNMANAGED CONTENT CARDS: {len(uncovered_rows)}")
    print()

    details = []
    for row in uncovered_rows:
        pid = str(row.get("product_id") or "")
        card = pcv3.get(pid) or {}
        content = card.get("content") or {}
        sku_media = card.get("sku_media") or []
        details.append({
            "product_id": pid,
            "slug": card.get("slug") or row.get("slug"),
            "title": content.get("title") or row.get("title"),
            "enabled": card.get("enabled"),
            "brand": content.get("brand"),
            "category": content.get("category"),
            "sku_count": len(sku_media) if isinstance(sku_media, list) else 0,
        })

    for i, item in enumerate(details, 1):
        print(
            f"{i:02d}. {item['slug']} | {item['product_id']} | "
            f"{item['title']} | brand={item['brand']} | "
            f"category={item['category']} | enabled={item['enabled']} | "
            f"sku={item['sku_count']}"
        )

    print()
    if len(runtime_rows) == 87 and len(managed_ids) == 77 and len(details) == 10:
        print("RESULT: PASS")
        print("CONTENT COVERAGE GAP: 10 CARDS")
        return 0

    print("RESULT: REVIEW")
    print(
        f"EXPECTED current production shape: runtime=87 managed=77 untracked=10; "
        f"got runtime={len(runtime_rows)} managed={len(managed_ids)} untracked={len(details)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
