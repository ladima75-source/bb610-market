from __future__ import annotations

"""R5 price importer for BB610 Market.

Business decision for this run:
- import every unambiguous source price except four Osmocote rows that the owner
  will enter manually;
- do not block the whole import merely because the live v3 catalogue contains
  additional untargeted SKU;
- never invent prices for untargeted SKU.

Safety retained from R1:
- source must contain exactly 195 rows;
- exactly four known Osmocote source rows are skipped;
- every remaining 191 source row must resolve to exactly one active v3 SKU by
  package + product identity;
- ambiguous/weak matches, duplicate commerce targets and missing commerce rows
  abort before writes;
- DB backup, transactional update and post-verify are delegated to R1.
"""

import argparse
import json

from backend.db import connect
from backend import tools_apply_pcv3_prices_20260916 as base


def _skip_manual_osmocote(row: dict) -> bool:
    name = str(row.get("source_name") or "")
    n = base.norm(name)
    f = base.formula(name)
    return "osmocote" in n and f in {("12", "8", "19"), ("16", "9", "12")}


def build_plan_r5() -> dict:
    doc = base._load_json(base.PRICE_MANIFEST, {})
    source_rows = doc.get("rows") if isinstance(doc, dict) else None
    if not isinstance(source_rows, list) or len(source_rows) != 195:
        raise RuntimeError(f"price manifest must contain 195 rows; got {len(source_rows or [])}")

    skipped: list[dict] = []
    import_rows: list[tuple[int, dict]] = []
    for row_no, row in enumerate(source_rows, start=2):
        if _skip_manual_osmocote(row):
            skipped.append({"source_row": row_no, **row})
        else:
            import_rows.append((row_no, row))

    if len(skipped) != 4 or len(import_rows) != 191:
        raise RuntimeError(
            f"expected exactly 4 manual Osmocote rows + 191 import rows; got {len(skipped)} + {len(import_rows)}"
        )

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
        candidates = [
            (base.pair_score(src_name, target["aliases"]), target)
            for target in by_pack.get(key, [])
        ]
        candidates.sort(key=lambda x: (x[0], x[1]["title"]), reverse=True)
        if not candidates:
            problems.append(f"row {row_no}: no SKU with package {package} for {src_name}")
            continue

        top_score, top = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else -1
        if top_score < 430:
            problems.append(
                f"row {row_no}: weak match {top_score:.1f}: {src_name} / {package} -> {top['title']}"
            )
            continue
        if second_score >= top_score - 2.0 and candidates[1][1]["product_id"] != top["product_id"]:
            problems.append(
                f"row {row_no}: ambiguous {src_name} / {package}: {top['title']}={top_score:.1f}; "
                f"{candidates[1][1]['title']}={second_score:.1f}"
            )
            continue
        if not top["commerce_key"]:
            problems.append(
                f"row {row_no}: matched SKU has no commerce binding: {top['title']} / {top['package']}"
            )
            continue

        plan.append({
            "source_row": row_no,
            "source_name": src_name,
            "source_package": package,
            "price": float(price),
            **{
                k: top[k]
                for k in (
                    "product_id",
                    "title",
                    "brand",
                    "category",
                    "sku_id",
                    "sku_code",
                    "package",
                    "commerce_key",
                )
            },
            "score": round(top_score, 2),
        })

    target_counts: dict[str, int] = {}
    for row in plan:
        target_counts[row["commerce_key"]] = target_counts.get(row["commerce_key"], 0) + 1
    duplicate_targets = [key for key, count in target_counts.items() if count != 1]
    if duplicate_targets:
        problems.append("duplicate target commerce keys: " + ", ".join(duplicate_targets[:30]))
    if len(plan) != 191:
        problems.append(f"matched source rows {len(plan)}/191")

    if problems:
        raise RuntimeError("PRICE PREFLIGHT FAILED:\n" + "\n".join(problems[:100]))

    with connect() as con:
        existing = {str(row[0]) for row in con.execute("SELECT sku FROM sku_commerce").fetchall()}
    missing_commerce = [row["commerce_key"] for row in plan if row["commerce_key"] not in existing]
    if missing_commerce:
        raise RuntimeError("missing commerce rows: " + ", ".join(missing_commerce[:30]))

    untargeted = [target for target in targets if target["commerce_key"] not in target_counts]

    return {
        "source_file": doc.get("source_file"),
        "source_date": doc.get("source_date"),
        "currency": doc.get("currency", "UAH"),
        "rows": plan,
        "manual_source_rows": skipped,
        "untargeted_v3_skus": [
            {
                k: target[k]
                for k in (
                    "title",
                    "brand",
                    "category",
                    "sku_id",
                    "sku_code",
                    "package",
                    "commerce_key",
                )
            }
            for target in untargeted
        ],
        "zero_price_rows": [row for row in plan if row["price"] == 0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply 191 verified BB610 Market price rows; leave four Osmocote rows manual and report any untargeted live SKU."
    )
    parser.add_argument("--apply-safe", action="store_true")
    args = parser.parse_args()

    plan = build_plan_r5()
    base.REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = base.REPORT_ROOT / f"pcv3-prices-r5-apply191-{base.stamp()}.json"
    report = {"mode": "APPLY_SAFE" if args.apply_safe else "DRY_RUN", **plan}

    print("BB610 PCV3 PRICE IMPORT R5 — APPLY 191 VERIFIED ROWS")
    print("SOURCE:", plan["source_file"])
    print("MATCHED PRICE ROWS:", len(plan["rows"]), "/ 191")
    print("MANUAL OSMOCOTE SOURCE ROWS:", len(plan["manual_source_rows"]))
    for row in plan["manual_source_rows"]:
        print("  MANUAL:", row["source_name"], "|", row["package"], "|", row["price"])
    print("V3 SKU TARGETED:", len({x['commerce_key'] for x in plan['rows']}), "/ 197")
    print("UNTARGETED V3 SKU (NO PRICE INVENTED):", len(plan["untargeted_v3_skus"]))
    for row in plan["untargeted_v3_skus"]:
        print("  UNTARGETED:", row["title"], "|", row["package"], "|", row["commerce_key"])
    print("STOCK QTY POLICY: NULL")
    print("AVAILABILITY POLICY: IN_STOCK FOR THE 191 TARGETED SKU")
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
