from __future__ import annotations

from typing import Any

from .product_master_v5 import snapshot as v5_snapshot


SOURCE_ID = "bb610-product-master-v5"

# Exact channel-safe image overrides are used only when the canonical SKU image
# is verified but its stored derivative is too small for shopping channels.
# Keep these package-specific: never substitute media from another SKU.
_CHANNEL_IMAGE_OVERRIDES = {
    "BB610-906E45D6FF4693": "https://godomall.speedycdn.net/d7edf57af8cba2f9de6fa9e1e88e0c40/goods/1000001036/image/detail/1000001036_detail_011.jpg",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _primary_media(rows: Any) -> str:
    if not isinstance(rows, list):
        return ""
    primary = next(
        (
            row for row in rows
            if isinstance(row, dict) and row.get("is_primary") and row.get("path")
        ),
        None,
    )
    if primary:
        return _text(primary.get("path"))
    first = next(
        (row for row in rows if isinstance(row, dict) and row.get("path")),
        None,
    )
    return _text(first.get("path")) if first else ""


def _identifier(attributes: Any, *keys: str) -> str:
    if not isinstance(attributes, dict):
        return ""
    lowered = {str(key).strip().casefold(): value for key, value in attributes.items()}
    for key in keys:
        value = lowered.get(key.casefold())
        if value not in (None, ""):
            return _text(value)
    return ""


def snapshot(commerce_override: dict[str, dict] | None = None) -> dict[str, Any]:
    """Flat feed projection from canonical public Product Master V5 only.

    Merchant/Meta exports must not reopen V4 catalog data or emit legacy SKU
    aliases. Product Master V5 already overlays live commerce onto canonical
    SKU identities, so this adapter only normalizes the nested V5 shape for the
    existing channel/feed code.
    """
    data = v5_snapshot(public_only=True)
    products: list[dict] = []
    skus: list[dict] = []
    commerce: dict[str, dict] = {}

    for source_product in data.get("products") or []:
        if not isinstance(source_product, dict):
            continue
        pid = _text(source_product.get("product_id"))
        if not pid:
            continue

        product_image = _primary_media(source_product.get("media"))
        product = {
            "id": pid,
            "name": _text(source_product.get("name")) or pid,
            "official_name": _text(source_product.get("name")) or pid,
            "brand": _text(source_product.get("brand")),
            "category_id": _text(source_product.get("category_id")),
            "product_type": _text(source_product.get("category_id")),
            "short_description": _text(source_product.get("short_description") or source_product.get("subtitle")),
            "description": _text(source_product.get("description")),
            "application": _text(source_product.get("application")),
            "composition": _text(source_product.get("composition")),
            "how_it_works": _text(source_product.get("how_it_works")),
            "seo_description": _text(source_product.get("seo_description")),
            "canonical_product_url": "/product.html?id=" + pid,
            "image": {"local": product_image} if product_image else {},
            "feed_policy": "allowed",
        }
        products.append(product)

        for source_sku in source_product.get("skus") or []:
            if not isinstance(source_sku, dict):
                continue
            sid = _text(source_sku.get("sku_id"))
            if not sid:
                continue

            attributes = source_sku.get("attributes")
            sku_image = _CHANNEL_IMAGE_OVERRIDES.get(sid) or _primary_media(source_sku.get("media")) or product_image
            sku = {
                "id": sid,
                "product_id": pid,
                "variant": _text(source_sku.get("package_label")),
                "image": sku_image,
                "mpn": _text(source_sku.get("manufacturer_sku")),
                "gtin_ean": _identifier(attributes, "gtin_ean", "gtin", "ean", "barcode"),
                "feed_policy": "allowed",
            }
            skus.append(sku)

            current = {
                "price": source_sku.get("price"),
                "sale_price": source_sku.get("sale_price"),
                "availability": _text(source_sku.get("availability")) or "unknown",
                "stock_qty": source_sku.get("stock_qty"),
                "enabled": bool(source_sku.get("commerce_enabled")),
            }
            if commerce_override and isinstance(commerce_override.get(sid), dict):
                current.update(commerce_override[sid])
            current["effective_price"] = (
                current.get("sale_price")
                if current.get("sale_price") is not None
                else current.get("price")
            )
            commerce[sid] = current

    return {
        "schema_version": "5.0-feed",
        "source": data.get("source") or SOURCE_ID,
        "products": products,
        "skus": skus,
        "commerce": commerce,
    }
