from __future__ import annotations

from typing import Any

from .product_master_v5 import snapshot as v5_snapshot


SOURCE_ID = "bb610-product-master-v5"

# Exact channel-safe image overrides are package-specific and preserve a
# verified image already used by the sales channel when the canonical SKU media
# binding is missing or its stored derivative is unsuitable for shopping.
# Never substitute media from another SKU.
_CHANNEL_IMAGE_OVERRIDES = {
    "BB610-02A58A1A393719": "/assets/img/v5/media/6aaeaed0087c0e7f68f0.jpg",
    "BB610-0BDAED34128BDA": "/assets/img/v5/media/146dbd278150498ae157.webp",
    "BB610-1E396B98D1779E": "/assets/img/v5/media/77f9adb9331f33afdb92.png",
    "BB610-5C50CFED57B2BD": "/assets/img/v5/media/ec30b3bafe67e0bddd52.jpg",
    "BB610-63DFC68206EF52": "/assets/img/v5/media/588144745cbafbff370f.png",
    "BB610-75DA86689E220C": "/assets/img/v5/media/11d0bf623e6192622180.jpg",
    "BB610-7CAECCDF081CBB": "/assets/img/v5/media/f97a5a2c2434009cebf1.png",
    "BB610-8AF90FA8223437": "/assets/img/v5/media/3ee61179db04ff908095.png",
    "BB610-A02CF54E375533": "/assets/img/v5/media/2adf4e93546de5e0ece0.png",
    "BB610-B1881030364E52": "/assets/img/v5/media/246f830bbd7893fb5d7e.png",
    "BB610-CFFC5BB95623B9": "/assets/img/v5/media/d3b90963ebacabfb9a94.png",
    "BB610-D357BA80A4242C": "/assets/img/v5/media/34390bab18da3c61585e.jpg",
    "BB610-D886B6AD2D6C04": "/assets/img/v5/media/c1cb781c514d2fb61c2c.png",
    "BB610-E4A0F69C3768B0": "/assets/img/v5/media/d33e51563b9dbdc54da1.jpg",
    "BB610-EDD4D8789728B8": "/assets/img/v5/media/795434bfb61d17c9e384.png",
    "BB610-FDF73DEFF6CCEC": "/assets/img/v5/media/2d02993966feccbe12a8.jpg",
    "BB610-VLG-MASTER134013-25KG": "/assets/img/v5/media/5ff16767afd9c682e4fa.jpg",
    "BB610-VLG-MASTER202020-10KG": "/assets/img/v5/media/110dc313fa69fd719e75.jpg",
    "BB610-VLG-MASTER202020-20G": "/assets/img/v5/media/8beecf484e8d837e427a.jpg",
    "BB610-VLG-MASTER202020-25KG": "/assets/img/v5/media/7a3aedb92ce7711d9261.jpg",
    "BB610-VLG-PLANTAFOL105410-1KG": "/assets/img/v5/media/d97ea4e1d943af52d3eb.jpg",
    "BB610-VLG-PLANTAFOL51545-1KG": "/assets/img/v5/media/c3a397daa5a996ec8ad4.jpg",
    "BB610-VLG-RADIFARM-25ML": "/assets/img/v5/media/a8f72fa0c704b35aa69c.jpg",
    "BB610-VLG-VIVA-100ML": "/assets/img/v5/media/eb3844af14f0436026b1.png",
    "BB610-906E45D6FF4693": "/assets/img/v5/channel/seasailer-20kg.jpg",
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
            canonical_title = _identifier(attributes, "canonical_title")
            sku = {
                "id": sid,
                "product_id": pid,
                "variant": _text(source_sku.get("package_label")),
                "canonical_title": canonical_title,
                "item_group_id": _identifier(attributes, "item_group_id", "related_group_id") or pid,
                "feed": {"title": canonical_title} if canonical_title else {},
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
