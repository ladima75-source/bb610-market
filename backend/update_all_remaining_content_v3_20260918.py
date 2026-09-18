from __future__ import annotations

"""Apply/audit all remaining BB610 Product Card v3 content batches.

This orchestrator covers exactly the 51 stage22c rows not already completed in
previous production-verified batches:
- rows 12-24: 13 cards
- batch04 selected rows 37-48 excluding Radifarm/Viva: 10 cards
- batch05 selected rows 49-60 excluding Megafol: 11 cards
- batch06 rows 61-72: 12 cards
- batch07 rows 73-77: 5 cards

It performs a full preflight for all 51 cards before mutating anything. Every
individual batch apply uses the generic content-only engine with per-batch backup,
rollback and commerce-map protection. After apply, every batch is resolved again
to prove idempotent post-apply state.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import tools_apply_product_content_batch_runtime as engine

REPORT_ROOT = ROOT / "var" / "reports"
MANIFESTS = [
    ROOT / "data" / "product_content" / "stage22c_remaining_rows12_24_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch04_remaining_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch05_remaining_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch06_20260918.json",
    ROOT / "data" / "product_content" / "stage22c_batch07_20260918.json",
]
EXPECTED_COUNTS = [13, 10, 11, 12, 5]
EXPECTED_TOTAL = 51


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def preflight_all() -> list[dict]:
    plans: list[dict] = []
    seen_pids: set[str] = set()
    seen_rows: set[int] = set()

    for manifest, expected in zip(MANIFESTS, EXPECTED_COUNTS):
        plan = engine.build_plan(manifest)
        if len(plan["targets"]) != expected:
            raise RuntimeError(
                f"{manifest.name}: expected {expected} targets; got {len(plan['targets'])}"
            )

        for target in plan["targets"]:
            pid = str(target["product_id"])
            row = int(target["source_row"])
            if pid in seen_pids:
                raise RuntimeError(f"duplicate product_id across batches: {pid}")
            if row in seen_rows:
                raise RuntimeError(f"duplicate source_row across batches: {row}")
            seen_pids.add(pid)
            seen_rows.add(row)

        plans.append(plan)

    total = sum(len(x["targets"]) for x in plans)
    if total != EXPECTED_TOTAL:
        raise RuntimeError(f"expected total {EXPECTED_TOTAL}; got {total}")

    expected_rows = set(range(12, 25))
    expected_rows.update(x for x in range(37, 49) if x not in {42, 45})
    expected_rows.update(x for x in range(49, 61) if x != 53)
    expected_rows.update(range(61, 78))
    if seen_rows != expected_rows:
        raise RuntimeError(
            f"source-row coverage mismatch: missing={sorted(expected_rows-seen_rows)} "
            f"extra={sorted(seen_rows-expected_rows)}"
        )

    return plans


def print_summary(plans: list[dict], label: str) -> None:
    print(f"=== {label} ===")
    print(f"BATCHES: {len(plans)}")
    print(f"TARGET CARDS: {sum(len(x['targets']) for x in plans)}")
    for plan in plans:
        rows = [int(x["source_row"]) for x in plan["targets"]]
        changed = sum(
            1
            for x in plan["targets"]
            if x["before"].get("content") != x["after"].get("content")
        )
        print(
            f"{plan['batch_id']} | cards={len(rows)} | changed={changed} | "
            f"rows={rows[0]}..{rows[-1]}"
        )
    print(
        "PROTECTED: product_id / slug / enabled / brand / category / "
        "SKU / media / commerce / prices"
    )


def write_report(mode: str, before: list[dict], results: list[dict] | None, after: list[dict] | None) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"all-remaining-content-{stamp()}.json"
    payload = {
        "mode": mode,
        "expected_total": EXPECTED_TOTAL,
        "batches": [
            {
                "batch_id": plan["batch_id"],
                "count": len(plan["targets"]),
                "rows": [int(x["source_row"]) for x in plan["targets"]],
                "slugs": [x["runtime_slug"] for x in plan["targets"]],
            }
            for plan in before
        ],
        "results": results,
        "post_apply_counts": (
            [len(x["targets"]) for x in after] if after is not None else None
        ),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    # Critical rule: every one of the 51 cards must resolve before any write.
    plans = preflight_all()
    print_summary(plans, "ALL REMAINING CONTENT PREFLIGHT")

    if not args.apply:
        report = write_report("DRY_RUN", plans, None, None)
        print("RESULT: PASS (DRY_RUN)")
        print("ALL REMAINING CONTENT: 51/51 RESOLVED")
        print(f"REPORT: {report}")
        return 0

    results: list[dict] = []
    for plan in plans:
        print(f"=== APPLY {plan['batch_id']} ===")
        result = engine.apply_plan(plan)
        results.append({
            "batch_id": plan["batch_id"],
            "status": result["status"],
            "updated": result["updated"],
            "changed": result["changed"],
            "commerce_map_changed": result["commerce_map_changed"],
            "backup_dir": result["backup_dir"],
        })
        print(
            f"RESULT: {result['status']} | UPDATED: {result['updated']} | "
            f"CHANGED: {result['changed']} | "
            f"COMMERCE_MAP_CHANGED: {str(result['commerce_map_changed']).lower()}"
        )

    # Resolve all 51 again after title/content changes.
    after = preflight_all()
    print_summary(after, "POST-APPLY AUDIT")

    for result in results:
        if result["status"] != "PASS":
            raise RuntimeError(f"batch apply failed: {result['batch_id']}")
        if result["commerce_map_changed"]:
            raise RuntimeError(f"commerce map changed: {result['batch_id']}")

    report = write_report("APPLY", plans, results, after)
    print("RESULT: PASS")
    print("ALL REMAINING CONTENT: 51/51 PASS")
    print(f"REPORT: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
