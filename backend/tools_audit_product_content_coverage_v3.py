from __future__ import annotations

"""Read-only Product Card v3 content coverage audit.

Resolves every card already managed by the completed content batches, compares
that set with the actual runtime Product Card v3 index, and reports only cards
that are outside the managed 77-card content scope.

Important: dedicated MASTER/PLANTAFOL and MEGAFOL/RADIFARM/VIVA batches can
have production slugs that differ from the Git manifest slug. This audit therefore
reuses their exact production preflight resolvers instead of assuming slug identity.

No files are mutated.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend import tools_apply_product_content_batch_runtime as engine
from backend import update_master_plantafol_content_v3_20260918 as master_plantafol
from backend import update_megafol_radifarm_viva_content_v3_20260918 as biostim

STAGE22C_BATCH03 = ROOT / "data" / "product_content" / "stage22c_batch03_20260918.json"

REMAINING_MANIFESTS = [
    ROOT / "data" / "product_content" / "stage22c_remaining_rows12_24_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch04_remaining_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch05_remaining_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch06_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch07_20260918.json",
]

EXPECTED_MANAGED = 77


def _append_plan_targets(
    managed: list[dict],
    seen: set[str],
    targets: list[dict],
    label: str,
) -> None:
    for target in targets:
        pid = str(target.get("product_id") or "").strip()
        if not pid:
            raise RuntimeError(f"{label}: empty product_id")
        if pid in seen:
            raise RuntimeError(f"{label}: duplicate managed product_id {pid}")
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f"{label}: missing product file {pid}")
        seen.add(pid)
        managed.append(card)


def collect_managed_cards() -> list[dict]:
    managed: list[dict] = []
    seen: set[str] = set()

    # Reuse the exact production resolvers that successfully applied and
    # post-verified these dedicated content batches. Do not assume manifest slug
    # equals production runtime slug.
    mp_plan = master_plantafol.preflight()
    if len(mp_plan.get("targets") or []) != 11:
        raise RuntimeError(
            f"MASTER/PLANTAFOL expected 11 targets; got {len(mp_plan.get('targets') or [])}"
        )
    _append_plan_targets(managed, seen, mp_plan["targets"], "MASTER/PLANTAFOL")

    bio_plan = biostim.preflight()
    if len(bio_plan.get("targets") or []) != 3:
        raise RuntimeError(
            f"MEGAFOL/RADIFARM/VIVA expected 3 targets; got {len(bio_plan.get('targets') or [])}"
        )
    _append_plan_targets(managed, seen, bio_plan["targets"], "MEGAFOL/RADIFARM/VIVA")

    plan03 = engine.build_plan(STAGE22C_BATCH03)
    if len(plan03.get("targets") or []) != 12:
        raise RuntimeError(
            f"stage22c batch03 expected 12 targets; got {len(plan03.get('targets') or [])}"
        )
    _append_plan_targets(managed, seen, plan03["targets"], "stage22c batch03")

    expected_counts = [13, 10, 11, 12, 5]
    for manifest, expected in zip(REMAINING_MANIFESTS, expected_counts):
        plan = engine.build_plan(manifest)
        if len(plan.get("targets") or []) != expected:
            raise RuntimeError(
                f"{manifest.name}: expected {expected} targets; "
                f"got {len(plan.get('targets') or [])}"
            )
        _append_plan_targets(managed, seen, plan["targets"], manifest.name)

    if len(managed) != EXPECTED_MANAGED:
        raise RuntimeError(
            f"managed content coverage expected {EXPECTED_MANAGED}; got {len(managed)}"
        )
    if len(seen) != EXPECTED_MANAGED:
        raise RuntimeError(
            f"managed unique product coverage expected {EXPECTED_MANAGED}; got {len(seen)}"
        )
    return managed


def _sku_count(card: dict) -> int:
    sku_media = card.get("sku_media") or {}
    if isinstance(sku_media, dict):
        skus = sku_media.get("skus") or []
        return len(skus) if isinstance(skus, list) else 0
    if isinstance(sku_media, list):
        return len(sku_media)
    return 0


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
        details.append({
            "product_id": pid,
            "slug": card.get("slug") or row.get("slug"),
            "title": content.get("title") or row.get("title"),
            "enabled": card.get("enabled"),
            "brand": content.get("brand"),
            "category": content.get("category"),
            "sku_count": _sku_count(card),
        })

    details.sort(key=lambda x: (str(x.get("title") or "").lower(), str(x.get("slug") or "")))

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
        f"got runtime={len(runtime_rows)} managed={len(managed_ids)} "
        f"untracked={len(details)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
