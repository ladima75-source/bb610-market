from __future__ import annotations

"""Runtime audit for BB610 catalog filter combinations.

Checks the canonical Product Master snapshot against the storefront filter
semantics. The audit is read-only and is intended to run on production after
catalog/filter changes.
"""

from collections import Counter, defaultdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.product_master_runtime import CULTURE_FACETS, snapshot


PACKAGE_GROUPS = ("small", "medium", "large")
METHOD_GROUPS = ("fertigation", "foliar", "root")
CULTURES = tuple(sorted(x for x in CULTURE_FACETS if x != "all"))


def _facets(row: dict) -> dict:
    value = row.get("facets")
    return value if isinstance(value, dict) else {}


def _culture_match(product: dict, culture: str) -> bool:
    values = set(str(x) for x in (_facets(product).get("cultures") or []) if x)
    return "all" in values or culture in values


def _method_match(product: dict, method: str) -> bool:
    return method in {
        str(x)
        for x in (_facets(product).get("application_methods") or [])
        if x
    }


def _package_match(product: dict, package_group: str) -> bool:
    return package_group in {
        str(x)
        for x in (_facets(product).get("package_groups") or [])
        if x
    }


def main() -> int:
    master = snapshot()
    products = [x for x in (master.get("products") or []) if isinstance(x, dict)]
    skus = [x for x in (master.get("skus") or []) if isinstance(x, dict)]

    by_product: dict[str, list[dict]] = defaultdict(list)
    for sku in skus:
        by_product[str(sku.get("product_id") or "")].append(sku)

    nonpot = [
        p for p in products
        if str(_facets(p).get("category") or "") != "containers"
    ]
    containers = [
        p for p in products
        if str(_facets(p).get("category") or "") == "containers"
    ]

    missing_brand: list[str] = []
    package_stock_mismatches: list[str] = []
    culture_wildcard_errors: list[str] = []
    container_facet_leaks: list[str] = []
    combination_counts: Counter[str] = Counter()

    for p in products:
        pid = str(p.get("id") or "?")
        if not str(_facets(p).get("brand") or "").strip():
            missing_brand.append(pid)

    # Stock + package must be satisfied by the same physical SKU.
    for p in nonpot:
        pid = str(p.get("id") or "?")
        rows = by_product.get(pid, [])
        for package_group in PACKAGE_GROUPS:
            product_has_package = _package_match(p, package_group)
            matching_rows = [
                sku for sku in rows
                if str(_facets(sku).get("package_group") or "") == package_group
            ]
            if product_has_package != bool(matching_rows):
                package_stock_mismatches.append(
                    f"{pid}:{package_group}:product={int(product_has_package)}:sku={len(matching_rows)}"
                )
                continue

            expected_in_stock = any(bool(_facets(sku).get("in_stock")) for sku in matching_rows)
            if product_has_package and bool(_facets(p).get("in_stock")):
                # Product-level stock can be true because another package is in stock.
                # The package+stock combination is valid only when this package has
                # at least one in-stock SKU.
                combination_counts[f"package:{package_group}:stock"] += int(expected_in_stock)

    # "all" is a wildcard and must satisfy every visible culture filter.
    for p in nonpot:
        cultures = set(str(x) for x in (_facets(p).get("cultures") or []) if x)
        if "all" not in cultures:
            continue
        pid = str(p.get("id") or "?")
        for culture in CULTURES:
            if not _culture_match(p, culture):
                culture_wildcard_errors.append(f"{pid}:{culture}")

    # Containers must never satisfy agronomic filter dimensions.
    for p in containers:
        pid = str(p.get("id") or "?")
        for package_group in PACKAGE_GROUPS:
            if _package_match(p, package_group):
                container_facet_leaks.append(f"{pid}:package:{package_group}")
        for method in METHOD_GROUPS:
            if _method_match(p, method):
                container_facet_leaks.append(f"{pid}:method:{method}")
        for culture in CULTURES:
            if _culture_match(p, culture):
                container_facet_leaks.append(f"{pid}:culture:{culture}")

    # Exercise the real intersection space. Zero-result combinations are valid;
    # the purpose is to prove that every match satisfies all selected facets,
    # especially that package+stock is backed by the same SKU.
    exercised = 0
    nonzero = 0
    for package_group in PACKAGE_GROUPS:
        for method in METHOD_GROUPS:
            for culture in CULTURES:
                exercised += 1
                matched = []
                for p in nonpot:
                    if not _package_match(p, package_group):
                        continue
                    if not _method_match(p, method):
                        continue
                    if not _culture_match(p, culture):
                        continue
                    pid = str(p.get("id") or "")
                    rows = by_product.get(pid, [])
                    if not any(
                        str(_facets(sku).get("package_group") or "") == package_group
                        and bool(_facets(sku).get("in_stock"))
                        for sku in rows
                    ):
                        continue
                    matched.append(pid)
                if matched:
                    nonzero += 1
                    combination_counts[
                        f"{package_group}+{method}+{culture}+stock"
                    ] = len(matched)

    print("===== CATALOG FILTER COMBINATIONS AUDIT =====")
    print(f"SOURCE={master.get('source')}")
    print(f"PRODUCTS={len(products)}")
    print(f"NON_POT_PRODUCTS={len(nonpot)}")
    print(f"CONTAINERS={len(containers)}")
    print(f"COMBINATION_CASES={exercised}")
    print(f"NONZERO_COMBINATIONS={nonzero}")
    print(f"MISSING_BRAND={len(missing_brand)}")
    print(f"PACKAGE_STOCK_MISMATCHES={len(package_stock_mismatches)}")
    print(f"CULTURE_WILDCARD_ERRORS={len(culture_wildcard_errors)}")
    print(f"CONTAINER_FACET_LEAKS={len(container_facet_leaks)}")

    top = combination_counts.most_common(12)
    if top:
        print("TOP_COMBINATIONS=" + "; ".join(f"{k}:{v}" for k, v in top))
    if missing_brand:
        print("MISSING_BRAND_IDS=" + ",".join(missing_brand[:30]))
    if package_stock_mismatches:
        print("PACKAGE_STOCK_MISMATCH_IDS=" + ",".join(package_stock_mismatches[:30]))
    if culture_wildcard_errors:
        print("CULTURE_WILDCARD_ERROR_IDS=" + ",".join(culture_wildcard_errors[:30]))
    if container_facet_leaks:
        print("CONTAINER_FACET_LEAK_IDS=" + ",".join(container_facet_leaks[:30]))

    ok = (
        not missing_brand
        and not package_stock_mismatches
        and not culture_wildcard_errors
        and not container_facet_leaks
    )
    print("CHECKS=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
