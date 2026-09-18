from __future__ import annotations

"""Read-only reproduction of the storefront JS product/SKU/commerce merge.

This audit mirrors:
  data/catalog.runtime.js base
  + /api/v1/catalog/content overlay
  + /api/v1/catalog/commerce overlay
  + js/app.js displaySku()

It compares the storefront-resolved display SKU with admin_detail() for every
public product and reports any case where backend has a priced SKU but storefront
would still render "Ціна уточнюється".

NO WRITES.
"""

import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_provider import load_catalog
from backend.services.catalog_cms import public_content, admin_detail
from backend.services.product_commerce import commerce_map

REPORT_ROOT = ROOT / "var" / "reports"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def has_price(sku: dict | None) -> bool:
    if not isinstance(sku, dict):
        return False
    value = sku.get("price")
    return value is not None


def active(sku: dict | None) -> bool:
    if not isinstance(sku, dict):
        return False
    return sku.get("commercial_status") == "active" or sku.get("offer_status") == "active"


def display_sku(product: dict, skus: list[dict]) -> dict | None:
    pid = str(product.get("id") or "")
    pskus = [s for s in skus if str(s.get("product_id") or "") == pid]
    default_id = str(product.get("default_sku_id") or "")
    default = next(
        (s for s in pskus if str(s.get("id") or s.get("sku") or "") == default_id),
        None,
    )
    if has_price(default):
        return default
    return (
        next((s for s in pskus if has_price(s) and active(s)), None)
        or next((s for s in pskus if has_price(s)), None)
        or default
        or (pskus[0] if pskus else None)
    )


def sku_summary(row: dict) -> dict:
    return {
        "id": row.get("id") or row.get("sku"),
        "product_id": row.get("product_id"),
        "variant": row.get("variant") or row.get("package") or row.get("label"),
        "price": row.get("price"),
        "base_price": row.get("base_price"),
        "sale_price": row.get("sale_price"),
        "availability": row.get("availability"),
        "commercial_status": row.get("commercial_status"),
        "offer_status": row.get("offer_status"),
        "enabled": row.get("enabled"),
        "runtime_dynamic": row.get("runtime_dynamic"),
    }


def main() -> int:
    base = load_catalog()
    products = [deepcopy(x) for x in (base.get("products") or []) if isinstance(x, dict)]
    skus = [deepcopy(x) for x in (base.get("skus") or []) if isinstance(x, dict)]

    # Exact js/data-source.js content overlay semantics.
    content = public_content()
    for patch in content.get("products") or []:
        if not isinstance(patch, dict) or not patch.get("id"):
            continue
        pid = str(patch["id"])
        index = next((i for i, p in enumerate(products) if str(p.get("id") or "") == pid), -1)
        if index >= 0:
            products[index] = {**products[index], **deepcopy(patch)}
        else:
            products.append(deepcopy(patch))

    for patch in content.get("skus") or []:
        if not isinstance(patch, dict) or not patch.get("id"):
            continue
        sid = str(patch["id"])
        index = next((i for i, s in enumerate(skus) if str(s.get("id") or "") == sid), -1)
        if index >= 0:
            skus[index] = {**skus[index], **deepcopy(patch)}
        else:
            skus.append(deepcopy(patch))

    # Exact js/data-source.js commerce overlay semantics.
    cm = commerce_map()
    for sku in skus:
        sid = str(sku.get("id") or "")
        live = cm.get(sid)
        if not isinstance(live, dict):
            continue
        sku["base_price"] = live.get("price")
        sku["sale_price"] = live.get("sale_price")
        sku["price"] = live.get("effective_price")
        sku["availability"] = live.get("availability")
        sku["stock_qty"] = live.get("stock_qty")
        sku["commercial_status"] = "active" if live.get("enabled") else "paused"
        sku["offer_status"] = "active" if live.get("enabled") else "draft"

    public_products = [
        p for p in products
        if not p.get("internal_only") and not p.get("runtime_hidden")
    ]

    mismatches = []
    storefront_no_price = []
    rows = []

    for p in public_products:
        pid = str(p.get("id") or "")
        frontend_skus = [s for s in skus if str(s.get("product_id") or "") == pid]
        chosen = display_sku(p, skus)
        detail = admin_detail(pid) or {}
        admin_skus = [x for x in (detail.get("skus") or []) if isinstance(x, dict)]
        admin_priced = [
            x for x in admin_skus
            if x.get("price") is not None
        ]

        row = {
            "product_id": pid,
            "slug": p.get("slug"),
            "name": p.get("name"),
            "default_sku_id": p.get("default_sku_id"),
            "frontend_sku_count": len(frontend_skus),
            "frontend_skus": [sku_summary(x) for x in frontend_skus],
            "display_sku": sku_summary(chosen) if chosen else None,
            "display_price": (chosen or {}).get("price") if chosen else None,
            "admin_sku_count": len(admin_skus),
            "admin_priced_sku_count": len(admin_priced),
            "admin_skus": [sku_summary(x) for x in admin_skus],
        }
        rows.append(row)

        if row["display_price"] is None:
            storefront_no_price.append(row)
            if admin_priced:
                mismatches.append(row)

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"storefront-js-merge-audit-{stamp()}.json"
    payload = {
        "mode": "READ_ONLY",
        "public_products": len(public_products),
        "storefront_no_price": len(storefront_no_price),
        "backend_priced_but_storefront_no_price": len(mismatches),
        "mismatches": mismatches,
        "storefront_no_price_products": storefront_no_price,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("BB610 STOREFRONT JS MERGE AUDIT")
    print("MODE: READ_ONLY")
    print("PUBLIC PRODUCTS:", len(public_products))
    print("STOREFRONT WOULD SHOW NO PRICE:", len(storefront_no_price))
    print("BACKEND PRICED / STOREFRONT NO PRICE:", len(mismatches))
    print()

    for i, row in enumerate(mismatches, start=1):
        print(
            f"{i:02d}. {row['slug'] or row['product_id']} | {row['name']} | "
            f"default={row['default_sku_id']} | frontend_sku={row['frontend_sku_count']} | "
            f"admin_sku={row['admin_sku_count']} priced={row['admin_priced_sku_count']}"
        )
        print("    DISPLAY:", row["display_sku"])
        print("    FRONTEND:")
        for sku in row["frontend_skus"]:
            print("      ", sku)
        print("    ADMIN:")
        for sku in row["admin_skus"]:
            print("      ", sku)

    print()
    print("ALL STOREFRONT NO-PRICE PRODUCTS:")
    for i, row in enumerate(storefront_no_price, start=1):
        print(
            f"{i:02d}. {row['slug'] or row['product_id']} | {row['name']} | "
            f"frontend_sku={row['frontend_sku_count']} | admin_priced={row['admin_priced_sku_count']}"
        )

    print()
    print("REPORT:", path)
    print("RESULT: PASS (READ_ONLY)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
