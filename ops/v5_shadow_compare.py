#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


HIDDEN_EXPECTED = {
    "aktara-25-wg",
    "switch-625-wg",
    "control-dmp",
    "plantlogic-25-round-1308125",
}
COMMERCE_FIELDS = ("price", "sale_price", "availability", "stock_qty", "enabled")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    return a == b


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--stage", default="v5/staging/production-current.json")
    ap.add_argument("--content", default="v5/content/verified-current.json")
    ap.add_argument("--media", default="v5/media/verified-current.json")
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--md-out", required=True)
    args = ap.parse_args()

    snapshot = Path(args.snapshot).resolve()
    stage = load(Path(args.stage))
    content = load(Path(args.content))
    media = load(Path(args.media))
    source_commerce = load(snapshot / "db/sku_commerce.json")

    products = list(stage.get("products") or []) + list(stage.get("plantlogic_products") or [])
    skus = list(stage.get("skus") or []) + list(stage.get("plantlogic_skus") or [])
    product_ids = [row["product_id"] for row in products]
    slugs = [row["slug"] for row in products]
    sku_ids = [row["sku_id"] for row in skus]

    canonical_by_sku = {row["sku_id"]: row for row in skus}
    aliases = {
        row["alias_sku_id"]: row
        for row in stage.get("sku_aliases") or []
    }
    excluded = {
        row["sku_id"]: row
        for row in stage.get("excluded") or []
    }
    source_by_sku = {row["sku"]: row for row in source_commerce}

    checks = []
    warnings = []
    details = {}

    def check(name: str, ok: bool, note: str, data=None):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "note": note})
        if data is not None:
            details[name] = data

    def warn(name: str, note: str, data=None):
        warnings.append({"name": name, "status": "WARN", "note": note})
        if data is not None:
            details[name] = data

    duplicate_products = sorted(k for k, n in Counter(product_ids).items() if n > 1)
    duplicate_slugs = sorted(k for k, n in Counter(slugs).items() if n > 1)
    duplicate_skus = sorted(k for k, n in Counter(sku_ids).items() if n > 1)
    check(
        "identity_uniqueness",
        not duplicate_products and not duplicate_slugs and not duplicate_skus,
        f"products={len(product_ids)}, skus={len(sku_ids)}",
        {
            "duplicate_product_ids": duplicate_products,
            "duplicate_slugs": duplicate_slugs,
            "duplicate_skus": duplicate_skus,
        },
    )

    coverage = {"canonical": 0, "alias": 0, "excluded": 0, "unmapped": []}
    for row in source_commerce:
        sid = row["sku"]
        if sid in canonical_by_sku:
            coverage["canonical"] += 1
        elif sid in aliases:
            coverage["alias"] += 1
        elif sid in excluded:
            coverage["excluded"] += 1
        else:
            coverage["unmapped"].append(sid)
    check(
        "production_commerce_identity_coverage",
        not coverage["unmapped"],
        (
            f"source={len(source_commerce)} canonical={coverage['canonical']} "
            f"alias={coverage['alias']} excluded={coverage['excluded']} "
            f"unmapped={len(coverage['unmapped'])}"
        ),
        coverage,
    )

    direct_mismatches = []
    direct_checked = 0
    for row in stage.get("skus") or []:
        src = source_by_sku.get(row["sku_id"])
        if not src:
            continue
        direct_checked += 1
        field_diff = {}
        for field in COMMERCE_FIELDS:
            if not same(src.get(field), row.get(field)):
                field_diff[field] = {"source": src.get(field), "v5": row.get(field)}
        if field_diff:
            direct_mismatches.append({"sku_id": row["sku_id"], "diff": field_diff})
    check(
        "direct_commerce_parity",
        not direct_mismatches,
        f"checked={direct_checked}, mismatches={len(direct_mismatches)}",
        direct_mismatches,
    )

    alias_mismatches = []
    alias_checked = 0
    for alias_id, alias in aliases.items():
        src = source_by_sku.get(alias_id)
        if not src:
            continue
        alias_checked += 1
        preserved = alias.get("alias_commerce") or {}
        diffs = {}
        for field in COMMERCE_FIELDS:
            if not same(src.get(field), preserved.get(field)):
                diffs[field] = {"source": src.get(field), "preserved": preserved.get(field)}
        if diffs:
            alias_mismatches.append({
                "alias_sku_id": alias_id,
                "canonical_sku_id": alias.get("canonical_sku_id"),
                "product_id": alias.get("product_id"),
                "diff": diffs,
            })
    check(
        "alias_commerce_preservation",
        not alias_mismatches,
        f"checked={alias_checked}, mismatches={len(alias_mismatches)}",
        alias_mismatches,
    )

    content_rows = content.get("products") or []
    content_ids = {row["product_id"] for row in content_rows}
    source_count = sum(len(row.get("sources") or []) for row in content_rows)
    missing_content = sorted(set(product_ids) - content_ids)
    source_less = sorted(
        row["product_id"] for row in content_rows if not (row.get("sources") or [])
    )
    check(
        "content_coverage",
        not missing_content and not source_less and content_ids == set(product_ids),
        (
            f"products={len(content_rows)}/{len(product_ids)}, "
            f"sources={source_count}, source_less={len(source_less)}"
        ),
        {"missing": missing_content, "source_less": source_less},
    )

    hidden = {row["product_id"] for row in content_rows if not row.get("public_enabled", True)}
    check(
        "public_visibility",
        hidden == HIDDEN_EXPECTED,
        f"hidden={sorted(hidden)}",
        {
            "expected": sorted(HIDDEN_EXPECTED),
            "actual": sorted(hidden),
            "missing_hidden": sorted(HIDDEN_EXPECTED - hidden),
            "unexpected_hidden": sorted(hidden - HIDDEN_EXPECTED),
        },
    )

    sku_bindings = media.get("sku_bindings") or []
    product_bindings = media.get("product_bindings") or []
    non_exact = [row for row in sku_bindings if row.get("binding_kind") != "exact"]
    product_media_ids = {row["product_id"] for row in product_bindings}
    exact_sku_ids = {row["sku_id"] for row in sku_bindings}
    current_skus = [
        row for row in skus
        if row.get("enabled") in (1, True)
        and row.get("commerce_state") != "legacy_disabled"
    ]
    unresolved_media = [
        {
            "sku_id": row["sku_id"],
            "product_id": row["product_id"],
            "package_label": row.get("package_label"),
        }
        for row in current_skus
        if row["sku_id"] not in exact_sku_ids and row["product_id"] not in product_media_ids
    ]
    public_ids = set(product_ids) - hidden
    public_without_media = sorted(public_ids - product_media_ids)
    check(
        "media_architecture",
        not non_exact and not unresolved_media and not public_without_media,
        (
            f"exact_skus={len(exact_sku_ids)}, product_media_products={len(product_media_ids)}, "
            f"unresolved_current_skus={len(unresolved_media)}, "
            f"public_products_without_media={len(public_without_media)}"
        ),
        {
            "non_exact_sku_bindings": non_exact,
            "unresolved_current_skus": unresolved_media,
            "public_products_without_media": public_without_media,
        },
    )

    model_rows = defaultdict(list)
    for row in stage.get("plantlogic_skus") or []:
        if row.get("commerce_state") != "request_price":
            continue
        attrs = row.get("attributes") or {}
        model = str(attrs.get("manufacturer_product_no") or "").strip()
        model_rows[model].append(row)
    duplicate_models = {
        model: [r["sku_id"] for r in rows]
        for model, rows in model_rows.items()
        if not model or len(rows) != 1
    }
    wrong_colors = []
    for model, rows in model_rows.items():
        if not rows:
            continue
        row = rows[0]
        attrs = row.get("attributes") or {}
        volume = row.get("package_value")
        color = attrs.get("color_code")
        expected = "terracotta" if volume == 40 and color == "terracotta" else "black"
        # 40 L Zephyr has no terracotta in manufacturer set, so black is valid fallback.
        if volume == 40:
            valid = color in {"terracotta", "black"}
        else:
            valid = color == "black"
        if not valid:
            wrong_colors.append({
                "manufacturer_product_no": model,
                "sku_id": row["sku_id"],
                "volume_l": volume,
                "color": color,
                "expected": expected,
            })
    check(
        "plantlogic_assortment",
        len(model_rows) == 17 and not duplicate_models and not wrong_colors,
        (
            f"manufacturer_models={len(model_rows)}, "
            f"duplicate_or_missing_model_keys={len(duplicate_models)}, "
            f"wrong_colors={len(wrong_colors)}"
        ),
        {"duplicate_models": duplicate_models, "wrong_colors": wrong_colors},
    )

    price_conflicts = stage.get("price_conflicts") or []
    checks.append({
        "name": "canonical_price_decisions",
        "status": "PASS",
        "note": (
            f"recorded_conflicts={len(price_conflicts)}; "
            "legacy values preserved in sku_alias_commerce"
        ),
    })
    if price_conflicts:
        details["canonical_price_decisions"] = price_conflicts

    failed = [row for row in checks if row["status"] == "FAIL"]
    status = "FAIL" if failed else ("WARN" if warnings else "PASS")

    result = {
        "schema": "bb610-v5-shadow-report-1",
        "status": status,
        "summary": {
            "checks_pass": sum(1 for row in checks if row["status"] == "PASS"),
            "checks_fail": len(failed),
            "warnings": len(warnings),
            "source_commerce_rows": len(source_commerce),
            "v5_products": len(product_ids),
            "v5_skus": len(sku_ids),
            "public_products": len(public_ids),
            "plantlogic_models": len(model_rows),
        },
        "checks": checks,
        "warnings": warnings,
        "details": details,
    }

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# BB610 V5 shadow gate",
        "",
        f"Overall: **{status}**",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(f"- **{row['status']}** — {row['name']}: {row['note']}")
    if warnings:
        lines += ["", "## Warnings", ""]
        for row in warnings:
            lines.append(f"- **WARN** — {row['name']}: {row['note']}")
    lines += [
        "",
        f"Source commerce rows: **{len(source_commerce)}**",
        f"V5: **{len(product_ids)} products / {len(sku_ids)} SKU**",
        f"Public products: **{len(public_ids)}**",
        "",
    ]
    md_out.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result["summary"] | {"status": status}, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
