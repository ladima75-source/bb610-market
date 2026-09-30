from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter

from .catalog_feeds import channel_snapshot

SELLER_NAME = "BB610 Market"
SELLER_URL = "https://market.bb610.com.ua/"
RETURN_POLICY_URL = "https://market.bb610.com.ua/returns.html"

OPENAI_FIELDS = [
    "item_id",
    "title",
    "description",
    "url",
    "brand",
    "seller_name",
    "seller_url",
    "image_url",
    "availability",
    "price",
    "group_id",
    "listing_has_variations",
    "variant_dict",
    "offer_id",
    "gtin",
    "mpn",
    "condition",
    "product_category",
    "return_policy",
    "is_eligible_search",
    "is_eligible_checkout",
    "is_ads_eligible",
    "target_countries",
]


def _availability(value: str) -> str:
    return {
        "in_stock": "in_stock",
        "out_of_stock": "out_of_stock",
        "preorder": "pre_order",
        "backorder": "backorder",
    }.get(value, "unknown")



def _variant_token(value: str) -> str:
    s = str(value or "").strip().lower().replace(",", ".")
    for src, dst in (("мл", "ml"), ("кг", "kg"), ("шт.", "pcs"), ("шт", "pcs"), ("л", "l"), ("г", "g")):
        s = s.replace(src, dst)
    s = "".join(s.split())
    s = re.sub(r"[^a-z0-9.]+", "-", s).replace(".", "-")
    return re.sub(r"-+", "-", s).strip("-")


def _openai_image_url(value: str) -> str:
    url = str(value or "").strip()
    aliases = {
        "https://market.bb610.com.ua/assets/img/v5/media/146dbd278150498ae157.webp":
            "https://market.bb610.com.ua/assets/img/v5/media/146dbd278150498ae157.jpg",
        "https://market.bb610.com.ua/assets/img/v5/media/ad3434331aae65aec38d.webp":
            "https://market.bb610.com.ua/assets/img/v5/media/ad3434331aae65aec38d.png",
    }
    return aliases.get(url, url)


def _exact_sku_url(base: dict) -> str:
    slug = str(base.get("product_slug") or "").strip()
    variant = _variant_token(str(base.get("variant") or ""))
    if slug and variant:
        url = f"https://market.bb610.com.ua/products/{slug}-{variant}/"
    else:
        url = str(base.get("link") or "").strip()
    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return url + sep + "utm_source=chatgpt&utm_medium=product_feed&utm_campaign=product_discovery"


def rows(commerce_override: dict | None = None) -> list[dict]:
    snap = channel_snapshot(commerce_override)
    feed_rows = snap["feed_rows"]

    group_counts = Counter(
        (base.get("item_group_id") or base.get("id") or "").strip()
        for base, _availability_raw in feed_rows
    )

    out: list[dict] = []
    for base, availability_raw in feed_rows:
        item_id = str(base.get("id") or "").strip()
        group_id = str(base.get("item_group_id") or item_id).strip()
        variant = str(base.get("variant") or "").strip()
        has_variations = (
            bool(group_id)
            and group_id != item_id
            and group_counts.get(group_id, 0) > 1
        )

        row = {
            "item_id": item_id,
            "title": str(base.get("title") or "").strip(),
            "description": str(base.get("description") or "").strip(),
            "url": _exact_sku_url(base),
            "brand": str(base.get("brand") or "").strip(),
            "seller_name": SELLER_NAME,
            "seller_url": SELLER_URL,
            "image_url": _openai_image_url(base.get("image_link")),
            "availability": _availability(str(availability_raw or "")),
            "price": str(base.get("price") or "").strip(),
            "group_id": group_id if has_variations else "",
            "listing_has_variations": "true" if has_variations else "",
            "variant_dict": (
                json.dumps({"package": variant}, ensure_ascii=False, separators=(",", ":"))
                if has_variations and variant
                else ""
            ),
            "offer_id": f"bb610-{item_id}" if item_id else "",
            "gtin": str(base.get("gtin") or "").strip(),
            "mpn": str(base.get("mpn") or "").strip(),
            "condition": "new",
            "product_category": str(base.get("product_type") or "").strip(),
            "return_policy": RETURN_POLICY_URL,
            "is_eligible_search": "true",
            "is_eligible_checkout": "false",
            "is_ads_eligible": "false",
            # Market setup is integration-specific. Standard uploads do not turn a blank
            # country into worldwide distribution, so BB610 must not fabricate US/UA here.
            # Keep blank until OpenAI confirms the registered market configuration.
            "target_countries": "",
        }
        out.append(row)

    return out


def csv_feed(commerce_override: dict | None = None) -> str:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=OPENAI_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows(commerce_override))
    return "\ufeff" + buf.getvalue()


def jsonl_feed(commerce_override: dict | None = None) -> str:
    records = rows(commerce_override)
    normalized: list[dict] = []
    for row in records:
        item = {k: v for k, v in row.items() if v not in ("", None)}
        if "listing_has_variations" in item:
            item["listing_has_variations"] = item["listing_has_variations"] == "true"
        if "is_eligible_search" in item:
            item["is_eligible_search"] = item["is_eligible_search"] == "true"
        if "is_eligible_checkout" in item:
            item["is_eligible_checkout"] = item["is_eligible_checkout"] == "true"
        if "is_ads_eligible" in item:
            item["is_ads_eligible"] = item["is_ads_eligible"] == "true"
        if "variant_dict" in item and isinstance(item["variant_dict"], str):
            item["variant_dict"] = json.loads(item["variant_dict"])
        normalized.append(item)
    return "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in normalized) + ("\n" if normalized else "")
