from __future__ import annotations

import csv
import io
import time
from typing import Any

from .product_master_feed_v5 import SOURCE_ID, snapshot as master_snapshot

SITE = "https://market.bb610.com.ua"
API = "https://api.market.bb610.com.ua"

GOOGLE_FIELDS = [
    "id", "title", "description", "availability", "condition", "price",
    "link", "image_link", "brand", "gtin", "mpn", "item_group_id",
    "product_type", "custom_label_0",
]
META_FIELDS = list(GOOGLE_FIELDS)

REASON_LABELS = {
    "sale_disabled": "Продаж вимкнено",
    "price_missing_or_zero": "Немає коректної ціни",
    "availability_unknown": "Некоректний availability",
    "feed_policy_blocked": "Feed policy: blocked",
    "feed_policy_review_required": "Потрібна ручна перевірка",
    "feed_policy_not_allowed": "Feed policy не визначено",
    "real_product_image_missing": "Немає придатного зображення",
    "image_missing": "Немає зображення",
    "link_missing": "Немає посилання",
    "title_missing": "Немає назви",
    "brand_missing": "Немає бренду",
}

WARNING_LABELS = {
    "gtin_mpn_unverified": "GTIN/MPN не вказано",
    "identifiers_require_source_check": "Ідентифікатори потребують перевірки джерела",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _image_raw(product: dict, sku: dict) -> str:
    raw = sku.get("image")
    if not raw:
        raw = product.get("image")
        if isinstance(raw, dict):
            raw = raw.get("local") or raw.get("url") or ""
    return _text(raw)


def _image(product: dict, sku: dict) -> str:
    raw = _image_raw(product, sku)
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/media/") or raw.startswith("media/"):
        return API + "/" + raw.lstrip("/")
    return SITE + "/" + raw.lstrip("/")


def _real_image_ready(product: dict, sku: dict) -> bool:
    raw = _image_raw(product, sku)
    low = raw.lower()
    if not raw or low.endswith(".svg"):
        return False
    if (
        "/real/" in low
        or low.startswith("/media/products/")
        or low.startswith("media/products/")
        or low.startswith("assets/media/")
        or low.startswith("assets/img/real/")
        or low.startswith("/assets/img/v5/media/")
        or low.startswith("assets/img/v5/media/")
        or low.startswith("https://")
        or low.startswith("http://")
    ):
        return True
    explicit = sku.get("feed_image_ready")
    if explicit is None:
        explicit = product.get("feed_image_ready")
    return bool(explicit) if explicit is not None else False


def _title(product: dict, sku: dict) -> str:
    feed = sku.get("feed") if isinstance(sku.get("feed"), dict) else {}
    sku_title = _text(feed.get("title"))
    if sku_title:
        return sku_title[:150]

    pfeed = product.get("feed") if isinstance(product.get("feed"), dict) else {}
    base = _text(
        pfeed.get("title")
        or product.get("official_name")
        or product.get("name")
        or sku.get("product_id")
        or sku.get("id")
    )
    variant = _text(sku.get("variant"))
    return (base + (" " + variant if variant else "")).strip()[:150]


def _description(product: dict, sku: dict) -> str:
    pfeed = product.get("feed") if isinstance(product.get("feed"), dict) else {}
    raw_parts = [
        pfeed.get("description"),
        product.get("description"),
        product.get("short_description"),
        product.get("seo_description"),
        product.get("application"),
        product.get("composition"),
        product.get("how_it_works"),
    ]
    parts: list[str] = []
    for raw in raw_parts:
        part = " ".join(_text(raw).split())
        if not part:
            continue
        # Avoid repeating the same sentence when short/SEO descriptions are
        # already contained in the canonical long description.
        if any(part == existing or part in existing for existing in parts):
            continue
        parts.append(part)

    if not parts:
        fallback = [
            _title(product, sku),
            _text(product.get("brand")),
            _text(product.get("product_type")),
        ]
        parts = [part for part in fallback if part]

    return " ".join(parts)[:5000]


def _link(product: dict, sku: dict) -> str:
    value = _text(
        sku.get("url")
        or product.get("canonical_product_url")
        or product.get("legacy_url")
    )
    if not value:
        pid = _text(product.get("id"))
        if pid:
            value = "/product.html?id=" + pid
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        return SITE + value
    return SITE + "/" + value.lstrip("/") if value else ""


def _gtin(product: dict, sku: dict) -> str:
    return _text(
        sku.get("gtin_ean")
        or sku.get("gtin")
        or product.get("gtin_ean")
        or product.get("gtin")
    )


def _mpn(product: dict, sku: dict) -> str:
    return _text(sku.get("mpn") or product.get("mpn"))


def _effective_policy(product: dict, sku: dict) -> str:
    sku_policy = _text(sku.get("feed_policy"))
    product_policy = _text(product.get("feed_policy"))
    return sku_policy or product_policy or "allowed"


def _price(commerce: dict) -> float | None:
    value = commerce.get("effective_price")
    if value is None:
        value = commerce.get("sale_price")
    if value is None:
        value = commerce.get("price")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _availability_google(value: str) -> str:
    return {
        "in_stock": "in_stock",
        "out_of_stock": "out_of_stock",
        "preorder": "preorder",
        "backorder": "backorder",
    }.get(value, "")


def _availability_meta(value: str) -> str:
    return {
        "in_stock": "in stock",
        "out_of_stock": "out of stock",
        "preorder": "preorder",
        "backorder": "available for order",
    }.get(value, "")


def _status_row(product: dict, sku: dict, commerce: dict) -> dict:
    sid = _text(sku.get("id") or sku.get("sku"))
    policy = _effective_policy(product, sku)
    title = _title(product, sku)
    image = _image(product, sku)
    brand = _text(sku.get("brand") or product.get("brand"))
    gtin = _gtin(product, sku)
    mpn = _mpn(product, sku)
    price = _price(commerce)
    availability = _text(commerce.get("availability") or "unknown")
    enabled = bool(commerce.get("enabled"))

    reason_codes: list[str] = []
    warning_codes: list[str] = []

    if not enabled:
        reason_codes.append("sale_disabled")
    if price is None:
        reason_codes.append("price_missing_or_zero")
    if availability not in {"in_stock", "out_of_stock", "preorder", "backorder"}:
        reason_codes.append("availability_unknown")
    if not title:
        reason_codes.append("title_missing")
    if not brand:
        reason_codes.append("brand_missing")
    if not _real_image_ready(product, sku):
        reason_codes.append("real_product_image_missing")
    if not image:
        reason_codes.append("image_missing")
    if not _link(product, sku):
        reason_codes.append("link_missing")

    if policy == "blocked":
        reason_codes.append("feed_policy_blocked")
    elif policy == "review-required":
        reason_codes.append("feed_policy_review_required")
    elif policy != "allowed":
        reason_codes.append("feed_policy_not_allowed")

    if not gtin and not mpn:
        warning_codes.append("gtin_mpn_unverified")
    if sku.get("launch_matrix_2026") and sku.get("identifier_status") == "unverified":
        warning_codes.append("identifiers_require_source_check")

    if policy == "review-required":
        state = "review_required"
    elif reason_codes:
        state = "blocked"
    else:
        state = "eligible"

    return {
        "sku_id": sid,
        "sku": sid,
        "product_id": _text(sku.get("product_id")),
        "title": title,
        "brand": brand,
        "price": price,
        "availability": availability,
        "sale_enabled": enabled,
        "enabled": enabled,
        "feed_policy": policy,
        "image": image,
        "image_link": image,
        "gtin": gtin,
        "mpn": mpn,
        "launch_priority": sku.get("launch_matrix_priority"),
        "state": state,
        "included": state == "eligible",
        "reason_codes": reason_codes,
        "reasons": [REASON_LABELS.get(code, code) for code in reason_codes],
        "warning_codes": warning_codes,
        "warnings": [WARNING_LABELS.get(code, code) for code in warning_codes],
    }


def channel_snapshot(commerce_override: dict | None = None) -> dict:
    master = master_snapshot(commerce_override)
    products = {
        _text(row.get("id")): row
        for row in (master.get("products") or [])
        if isinstance(row, dict) and row.get("id")
    }
    commerce = master.get("commerce") or {}

    audit_rows: list[dict] = []
    feed_rows: list[tuple[dict, str]] = []
    seen: set[str] = set()

    for sku in master.get("skus") or []:
        if not isinstance(sku, dict):
            continue
        sid = _text(sku.get("id") or sku.get("sku"))
        if not sid or sid in seen:
            continue
        seen.add(sid)

        product = products.get(_text(sku.get("product_id")))
        if not product:
            continue

        current = commerce.get(sid) if isinstance(commerce.get(sid), dict) else {}
        status = _status_row(product, sku, current)
        audit_rows.append(status)

        if status["state"] != "eligible":
            continue

        price = status["price"]
        base = {
            "id": sid,
            "title": status["title"],
            "description": _description(product, sku),
            "condition": "new",
            "price": f"{float(price):.2f} UAH",
            "link": _link(product, sku),
            "image_link": status["image_link"],
            "brand": status["brand"],
            "gtin": status["gtin"],
            "mpn": status["mpn"],
            "item_group_id": _text(sku.get("product_id")),
            "product_type": _text(product.get("product_type")),
            "custom_label_0": (
                "warehouse"
                if sku.get("launch_matrix_priority") == "A"
                else ("test" if sku.get("launch_matrix_priority") == "B" else "")
            ),
        }
        feed_rows.append((base, status["availability"]))

    counts = {
        "total": len(audit_rows),
        "eligible": sum(1 for row in audit_rows if row["state"] == "eligible"),
        "blocked": sum(1 for row in audit_rows if row["state"] == "blocked"),
        "review_required": sum(1 for row in audit_rows if row["state"] == "review_required"),
        "warnings": sum(1 for row in audit_rows if row["warnings"]),
    }
    reasons: dict[str, int] = {}
    for row in audit_rows:
        for reason in row["reasons"]:
            reasons[reason] = reasons.get(reason, 0) + 1

    return {
        "source": master.get("source") or SOURCE_ID,
        "generated_at": time.time(),
        "counts": counts,
        "reasons": reasons,
        "audit_rows": audit_rows,
        "feed_rows": feed_rows,
        "catalog_sku_count": len(seen),
    }


# Backwards-compatible name used by older tests/integrations.
def snapshot(commerce_override: dict | None = None) -> dict:
    snap = channel_snapshot(commerce_override)
    return {
        "rows": snap["feed_rows"],
        "status": snap["audit_rows"],
        "catalog_sku_count": snap["catalog_sku_count"],
        "source": snap["source"],
    }


def channel_audit_from_snapshot(snap: dict) -> dict:
    return {
        "source": snap["source"],
        "generated_at": snap["generated_at"],
        "counts": snap["counts"],
        "reasons": snap["reasons"],
        "rows": snap["audit_rows"],
    }


def channel_audit(commerce_override: dict | None = None) -> dict:
    return channel_audit_from_snapshot(channel_snapshot(commerce_override))


def _csv(fields: list[str], rows: list[dict]) -> str:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + buf.getvalue()


def google_csv_from_snapshot(snap: dict) -> str:
    out: list[dict] = []
    for base, availability in snap["feed_rows"]:
        row = dict(base)
        row["availability"] = _availability_google(availability)
        out.append(row)
    return _csv(GOOGLE_FIELDS, out)


def google_csv(commerce_override: dict | None = None) -> str:
    return google_csv_from_snapshot(channel_snapshot(commerce_override))


def meta_csv_from_snapshot(snap: dict) -> str:
    out: list[dict] = []
    for base, availability in snap["feed_rows"]:
        row = dict(base)
        row["availability"] = _availability_meta(availability)
        out.append(row)
    return _csv(META_FIELDS, out)


def meta_csv(commerce_override: dict | None = None) -> str:
    return meta_csv_from_snapshot(channel_snapshot(commerce_override))


def feed_status_from_snapshot(snap: dict) -> dict:
    launch = [
        row for row in snap["audit_rows"]
        if row.get("launch_priority") in ("A", "B")
    ]
    return {
        "source": snap["source"],
        "generated_for": "BB610 Market",
        "catalog_sku_count": snap["catalog_sku_count"],
        "eligible_count": snap["counts"]["eligible"],
        "launch_sku_count": len(launch),
        "launch_eligible_count": sum(1 for row in launch if row["state"] == "eligible"),
        "note": (
            "Product identity, content and media come from public canonical Product Master V5 SKUs only; "
            "legacy aliases are excluded. Live commerce is overlaid onto those canonical V5 SKU identities."
        ),
        "items": snap["audit_rows"],
    }


def feed_status(commerce_override: dict | None = None) -> dict:
    return feed_status_from_snapshot(channel_snapshot(commerce_override))
