from __future__ import annotations

"""Read-only audit of storefront price selection.

Emulates the storefront rule:
1) use default SKU when it has a configured price;
2) otherwise use an active priced sibling SKU;
3) otherwise use any priced sibling SKU;
4) otherwise keep the default/first SKU and show no fabricated price.

No catalog, commerce or Product Card data is modified.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_provider import load_catalog
from backend.services.catalog_cms import _dynamic_skus, _overrides
from backend.services.product_commerce import commerce_map

REPORT_ROOT = ROOT / "var" / "reports"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def has_price(row: dict | None) -> bool:
    if not isinstance(row, dict):
        return False
    value = row.get("effective_price")
    return value is not None


def active(row: dict | None) -> bool:
    return bool((row or {}).get("enabled"))


def choose(default_sku: dict | None, skus: list[dict], cm: dict[str, dict]) -> dict | None:
    if default_sku and has_price(cm.get(str(default_sku.get("id") or default_sku.get("sku") or ""))):
        return default_sku
    for sku in skus:
        key = str(sku.get("id") or sku.get("sku") or "")
        if has_price(cm.get(key)) and active(cm.get(key)):
            return sku
    for sku in skus:
        key = str(sku.get("id") or sku.get("sku") or "")
        if has_price(cm.get(key)):
            return sku
    return default_sku or (skus[0] if skus else None)


def main() -> int:
    catalog = load_catalog()
    products = {
        str(x.get("id") or ""): dict(x)
        for x in (catalog.get("products") or [])
        if isinstance(x, dict) and x.get("id")
    }
    for pid, patch in _overrides().items():
        if pid in products:
            products[pid].update({k: v for k, v in patch.items() if not k.startswith("cms_")})
        else:
            products[pid] = {k: v for k, v in patch.items() if not k.startswith("cms_")}
            products[pid]["id"] = pid

    skus = [dict(x) for x in (catalog.get("skus") or []) if isinstance(x, dict)]
    skus.extend(dict(x) for x in _dynamic_skus() if isinstance(x, dict))
    by_product: dict[str, list[dict]] = defaultdict(list)
    for sku in skus:
        by_product[str(sku.get("product_id") or "")].append(sku)

    cm = commerce_map()
    fallback_rows = []
    true_missing = []
    selected_rows = []

    for pid, product in products.items():
        pskus = by_product.get(pid, [])
        if not pskus:
            continue
        default_id = str(product.get("default_sku_id") or "")
        default = next(
            (x for x in pskus if str(x.get("id") or x.get("sku") or "") == default_id),
            None,
        )
        if default is None:
            default = pskus[0]

        chosen = choose(default, pskus, cm)
        if not chosen:
            continue

        default_key = str(default.get("id") or default.get("sku") or "")
        chosen_key = str(chosen.get("id") or chosen.get("sku") or "")
        default_c = cm.get(default_key) or {}
        chosen_c = cm.get(chosen_key) or {}
        priced = [
            {
                "sku": str(x.get("id") or x.get("sku") or ""),
                "variant": x.get("variant"),
                "price": (cm.get(str(x.get("id") or x.get("sku") or "")) or {}).get("effective_price"),
                "enabled": bool((cm.get(str(x.get("id") or x.get("sku") or "")) or {}).get("enabled")),
                "availability": (cm.get(str(x.get("id") or x.get("sku") or "")) or {}).get("availability"),
            }
            for x in pskus
            if has_price(cm.get(str(x.get("id") or x.get("sku") or "")))
        ]

        row = {
            "product_id": pid,
            "slug": product.get("slug"),
            "name": product.get("name"),
            "brand": product.get("brand"),
            "default_sku": default_key,
            "default_variant": default.get("variant"),
            "default_price": default_c.get("effective_price"),
            "default_enabled": bool(default_c.get("enabled")),
            "display_sku": chosen_key,
            "display_variant": chosen.get("variant"),
            "display_price": chosen_c.get("effective_price"),
            "display_enabled": bool(chosen_c.get("enabled")),
            "display_availability": chosen_c.get("availability"),
            "priced_skus": priced,
        }
        selected_rows.append(row)

        if not has_price(default_c) and has_price(chosen_c):
            fallback_rows.append(row)
        if not priced:
            true_missing.append(row)

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"storefront-price-resolution-{stamp()}.json"
    payload = {
        "products_with_skus": len(selected_rows),
        "default_unpriced_but_sibling_priced": len(fallback_rows),
        "products_with_no_configured_price": len(true_missing),
        "fallback_products": fallback_rows,
        "true_missing_products": true_missing,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("BB610 STOREFRONT PRICE RESOLUTION AUDIT")
    print("MODE: READ_ONLY")
    print("PRODUCTS WITH SKU:", len(selected_rows))
    print("DEFAULT UNPRICED / SIBLING PRICED:", len(fallback_rows))
    print("NO CONFIGURED PRICE ON ANY SKU:", len(true_missing))
    print()

    for row in fallback_rows:
        print(
            "FALLBACK:",
            row["slug"] or row["product_id"],
            "|", row["name"],
            "| default", row["default_variant"], "=", row["default_price"],
            "=> display", row["display_variant"], "=", row["display_price"],
        )

    for row in true_missing:
        print(
            "NO PRICE:",
            row["slug"] or row["product_id"],
            "|", row["name"],
            "| SKU", ",".join(str(x.get("variant") or x.get("id") or "") for x in by_product.get(row["product_id"], [])),
        )

    print()
    print("REPORT:", path)
    print("RESULT: PASS (READ_ONLY)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
