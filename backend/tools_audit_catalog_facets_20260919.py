from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.product_master_runtime import snapshot


def main() -> int:
    master = snapshot()
    products = [x for x in (master.get("products") or []) if isinstance(x, dict)]
    skus = [x for x in (master.get("skus") or []) if isinstance(x, dict)]

    category = Counter()
    brand = Counter()
    culture = Counter()
    method = Counter()
    package = Counter()
    missing_facets = []
    nonpot = 0
    no_culture = 0
    no_method = 0
    no_package = 0

    for p in products:
        facets = p.get("facets")
        if not isinstance(facets, dict):
            missing_facets.append(str(p.get("id") or "?"))
            continue
        category[str(facets.get("category") or "")] += 1
        brand[str(facets.get("brand") or "")] += 1

        if facets.get("category") == "containers":
            continue
        nonpot += 1

        cultures = [str(x) for x in (facets.get("cultures") or []) if x]
        methods = [str(x) for x in (facets.get("application_methods") or []) if x]
        packages = [str(x) for x in (facets.get("package_groups") or []) if x]

        if not cultures:
            no_culture += 1
        if not methods:
            no_method += 1
        if not packages:
            no_package += 1

        culture.update(cultures)
        method.update(methods)
        package.update(packages)

    print("===== CATALOG FACETS AUDIT =====")
    print(f"SOURCE={master.get('source')}")
    print(f"PRODUCTS={len(products)}")
    print(f"SKUS={len(skus)}")
    print(f"NON_POT_PRODUCTS={nonpot}")
    print(f"MISSING_FACET_OBJECT={len(missing_facets)}")
    print("CATEGORY=" + ",".join(f"{k}:{v}" for k, v in sorted(category.items()) if k))
    print("METHOD=" + ",".join(f"{k}:{v}" for k, v in sorted(method.items())))
    print("PACKAGE=" + ",".join(f"{k}:{v}" for k, v in sorted(package.items())))
    print("CULTURE=" + ",".join(f"{k}:{v}" for k, v in sorted(culture.items())))
    print(f"NO_METHOD={no_method}")
    print(f"NO_CULTURE={no_culture}")
    print(f"NO_PACKAGE_GROUP={no_package}")

    allowed_methods = {"fertigation", "foliar", "root"}
    allowed_packages = {"small", "medium", "large"}
    bad_methods = set(method) - allowed_methods
    bad_packages = set(package) - allowed_packages

    ok = not missing_facets and not bad_methods and not bad_packages
    print("CHECKS=" + ("PASS" if ok else "FAIL"))
    if missing_facets:
        print("MISSING_FACET_IDS=" + ",".join(missing_facets[:20]))
    if bad_methods:
        print("BAD_METHODS=" + ",".join(sorted(bad_methods)))
    if bad_packages:
        print("BAD_PACKAGES=" + ",".join(sorted(bad_packages)))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
