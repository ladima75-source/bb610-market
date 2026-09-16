from __future__ import annotations

"""R4 price importer: apply every unambiguous 2026-09-16 price except four
Osmocote SKU rows that the owner chose to enter manually.

Manual rows intentionally excluded:
- Osmocote Potassium 12-8-19 (3-4M): 200 g, 1 kg
- Osmocote Landscape 16-9-12 (3-4M): 200 g, 1 kg

All other safeguards from the original importer remain: exact package matching,
ambiguity refusal, commerce binding checks, DB backup, transactional update and
post-verify. The two Plantlogic pot SKU remain outside this price source.
"""

import argparse
import json
from datetime import datetime, timezone

from backend.db import connect
from backend import tools_apply_pcv3_prices_20260916 as base


def _skip_manual(row: dict) -> bool:
    name = str(row.get("source_name") or "")
    n = base.norm(name)
    f = base.formula(name)
    if "osmocote" not in n:
        return False
    return f in {("12", "8", "19"), ("16", "9", "12")}


def _is_manual_target(target: dict) -> bool:
    n = base.norm(" ".join([
        str(target.get("title") or ""),
        str(target.get("package") or ""),
    ]))
    return (
        ("osmocote" in n and "potassium" in n and base.formula(n) == ("12", "8", "19"))
        or ("osmocote" in n and "landscape" in n and base.formula(n) == ("16", "9", "12"))
    )


def _is_pot_target(target: dict) -> bool:
    n = base.norm(" ".join([
        str(target.get("title") or ""),
        str(target.get("brand") or ""),
        str(target.get("category") or ""),
        str(target.get("package") or ""),
    ]))
    return any(k in n for k in ("plantlogic", "container", "pot", "gorsh", "konteiner"))


def build_plan_r4() -> dict:
    doc = base._load_json(base.PRICE_MANIFEST, {})
    source_rows = doc.get("rows") if isinstance(doc, dict) else None
    if not isinstance(source_rows, list) or len(source_rows) != 195:
        raise RuntimeError(f"price manifest must contain 195 rows; got {len(source_rows or [])}")

    skipped = []
    import_rows = []
    for row_no, row in enumerate(source_rows, start=2):
        if _skip_manual(row):
            skipped.append({"source_row": row_no, **row})
        else:
            import_rows.append((row_no, row))
    if len(skipped) != 4 or len(import_rows) != 191:
        raise RuntimeError(f"expected 4 manual rows + 191 import rows; got {len(skipped)} + {len(import_rows)}")

    targets = base.load_targets()
    if len(targets) != 197:
        raise RuntimeError(f"expected 197 active v3 SKU; got {len(targets)}")

    by_pack: dict[str, list[dict]] = {}
    for target in targets:
        by_pack.setdefault(target["pack_key"], []).append(target)

    plan: list[dict] = []
    problems: list[str] = []
    for row_no, row in import_rows:
        src_name = str(row.get("source_name") or "").strip()
        package = str(row.get("package") or "").strip()
        price = row.get("price")
        if not isinstance(price, (int, float)) or price < 0:
            problems.append(f"row {row_no}: invalid price {price!r}")
            continue
        key = base.pack_key(package)
        candidates = [(base.pair_score(src_name, target["aliases"]), target) for target in by_pack.get(key, [])]
        candidates.sort(key=lambda x: (x[0], x[1]["title"]), reverse=True)
        if not candidates:
            problems.append(f"row {row_no}: no SKU with package {package} for {src_name}")
            continue
        top_score, top = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else -1
        if top_score < 430:
            problems.append(f"row {row_no}: weak match {top_score:.1f}: {src_name} / {package} -> {top['title']}")
            continue
        if second_score >= top_score - 2.0 and candidates[1][1]["product_id"] != top["product_id"]:
            problems.append(
                f"row {row_no}: ambiguous {src_name} / {package}: {top['title']}={top_score:.1f}; "
                f"{candidates[1][1]['title']}={second_score:.1f}"
            )
            continue
        if not top["commerce_key"]:
            problems.append(f"row {row_no}: matched SKU has no commerce binding: {top['title']} / {top['package']}")
            continue
        plan.append({
            "source_row": row_no,
            "source_name": src_name,
            "source_package": package,
            "price": float(price),
            **{k: top[k] for k in ("product_id", "title", "brand", "category", "sku_id", "sku_code", "package", "commerce_key")},
            "score": round(top_score, 2),
        })

    target_counts: dict[str, int] = {}
    for row in plan:
        target_counts[row["commerce_key"]] = target_counts.get(row["commerce_key"], 0) + 1
    duplicates = [key for key, count in target_counts.items() if count != 1]
    if duplicates:
        problems.append("duplicate target commerce keys: " + ", ".join(duplicates[:20]))
    if len(plan) != 191:
        problems.append(f"matched rows {len(plan)}/191")

    unmatched_targets = [target for target in targets if target["commerce_key"] not in target_counts]
    manual_targets = [target for target in unmatched_targets if _is_manual_target(target)]
    pot_targets = [target for target in unmatched_targets if _is_pot_target(target)]
    if len(unmatched_targets) != 6:
        problems.append(f"expected 6 unmatched v3 SKU (4 manual Osmocote + 2 pots); got {len(unmatched_targets)}")
    if len(manual_targets) != 4:
        problems.append(f"expected 4 manual Osmocote SKU; got {len(manual_targets)}")
    if len(pot_targets) != 2:
        problems.append(f"expected 2 Plantlogic pot SKU; got {len(pot_targets)}")
    covered = {x["commerce_key"] for x in manual_targets + pot_targets}
    unexpected = [x for x in unmatched_targets if x["commerce_key"] not in covered]
    for target in unexpected:
        problems.append(f"unexpected unmatched SKU: {target['title']} / {target['package']} / {target['commerce_key']}")

    if problems:
        raise RuntimeError("PRICE PREFLIGHT FAILED:\n" + "\n".join(problems[:100]))

    with connect() as con:
        existing = {str(row[0]) for row in con.execute("SELECT sku FROM sku_commerce").fetchall()}
    missing = [row["commerce_key"] for row in plan if row["commerce_key"] not in existing]
    if missing:
        raise RuntimeError("missing commerce rows: " + ", ".join(missing[:30]))

    return {
        "source_file": doc.get("source_file"),
        "source_date": doc.get("source_date"),
        "currency": doc.get("currency", "UAH"),
        "rows": plan,
        "manual_source_rows": skipped,
        "manual_v3_skus": [
            {k: target[k] for k in ("title", "brand", "category", "sku_id", "sku_code", "package", "commerce_key")}
            for target in manual_targets
        ],
        "unmatched_pot_skus": [
            {k: target[k] for k in ("title", "brand", "category", "sku_id", "sku_code", "package", "commerce_key")}
            for target in pot_targets
        ],
        "zero_price_rows": [row for row in plan if row["price"] == 0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply 191 unambiguous BB610 Market prices; leave four Osmocote SKU for manual entry.")
    parser.add_argument("--apply-safe", action="store_true")
    args = parser.parse_args()

    plan = build_plan_r4()
    base.REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = base.REPORT_ROOT / f"pcv3-prices-r4-skip4-{base.stamp()}.json"
    report = {"mode": "APPLY_SAFE" if args.apply_safe else "DRY_RUN", **plan}

    print("BB610 PCV3 PRICE IMPORT R4 — SKIP 4 MANUAL OSMOCOTE SKU")
    print("SOURCE:", plan["source_file"])
    print("MATCHED PRICE ROWS:", len(plan["rows"]), "/ 191")
    print("MANUAL PRICE ROWS SKIPPED:", len(plan["manual_source_rows"]))
    for row in plan["manual_source_rows"]:
        print("  MANUAL:", row["source_name"], "|", row["package"], "|", row["price"])
    print("V3 SKU TARGETED:", len({x['commerce_key'] for x in plan['rows']}), "/ 197")
    print("MANUAL V3 SKU:", len(plan["manual_v3_skus"]))
    for row in plan["manual_v3_skus"]:
        print("  LEAVE MANUAL:", row["title"], "|", row["package"], "|", row["commerce_key"])
    print("UNMATCHED POT SKU:", len(plan["unmatched_pot_skus"]))
    print("STOCK QTY POLICY: NULL")
    print("AVAILABILITY POLICY: IN_STOCK")
    print("SALE PRICE: UNCHANGED")
    print("SALE ENABLED: UNCHANGED")

    if args.apply_safe:
        result = base.apply_plan(plan)
        report["apply"] = result
        print("UPDATED:", result["updated"])
        print("AVAILABILITY IN_STOCK:", result["availability_in_stock"])
        print("STOCK QTY NULL:", result["stock_qty_null"])
        print("BACKUP:", result["backup_dir"])
        print("RESULT: PASS")
    else:
        print("RESULT: PASS (DRY-RUN)")

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REPORT:", report_path)


if __name__ == "__main__":
    main()
