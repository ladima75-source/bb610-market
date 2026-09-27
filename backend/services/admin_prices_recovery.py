from __future__ import annotations

from .product_commerce import admin_products

def _row(item: dict) -> dict:
    return {
        "product": item.get("name") or item.get("product_id") or "",
        "brand": item.get("brand") or "",
        "sku": item.get("sku") or "",
        "display_sku": item.get("sku") or "",
        "sku_id": item.get("sku") or "",
        "product_id": item.get("product_id") or "",
        "pack": item.get("variant") or "",
        "price": item.get("price"),
        "sale_price": item.get("sale_price"),
        "availability": item.get("availability") or "unknown",
        "qty": item.get("stock_qty"),
        "sale_enabled": bool(item.get("enabled")),
        "gtin": "",
        "mpn": "",
        "commerce_found": True,
        "mapped": True,
        "source": "product_master_v5",
        "legacy_alias": False,
    }

def rows():
    return [_row(item) for item in admin_products(include_inactive=False, include_aliases=False)]

def diagnostics():
    result = rows()
    return {
        "source": "product_master_v5",
        "rows": len(result),
        "canonical_skus": len(result),
        "legacy_aliases_exposed": 0,
        "rows_with_commerce": sum(
            1 for row in result
            if row["price"] is not None
            or row["sale_price"] is not None
            or row["availability"] == "request_price"
        ),
    }
