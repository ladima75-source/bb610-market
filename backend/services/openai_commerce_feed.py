from __future__ import annotations

import csv
import io
import json
from collections import Counter

from .catalog_feeds import channel_snapshot

SELLER_NAME = "BB610 Market"
SELLER_URL = "https://market.bb610.com.ua/"

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
    "gtin",
    "mpn",
    "condition",
    "product_category",
    "is_eligible_search",
]


def _availability(value: str) -> str:
    return {
        "in_stock": "in_stock",
        "out_of_stock": "out_of_stock",
        "preorder": "pre_order",
        "backorder": "backorder",
    }.get(value, "unknown")


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
            "url": str(base.get("link") or "").strip(),
            "brand": str(base.get("brand") or "").strip(),
            "seller_name": SELLER_NAME,
            "seller_url": SELLER_URL,
            "image_url": str(base.get("image_link") or "").strip(),
            "availability": _availability(str(availability_raw or "")),
            "price": str(base.get("price") or "").strip(),
            "group_id": group_id if has_variations else "",
            "listing_has_variations": "true" if has_variations else "",
            "variant_dict": (
                json.dumps({"package": variant}, ensure_ascii=False, separators=(",", ":"))
                if has_variations and variant
                else ""
            ),
            "gtin": str(base.get("gtin") or "").strip(),
            "mpn": str(base.get("mpn") or "").strip(),
            "condition": "new",
            "product_category": str(base.get("product_type") or "").strip(),
            "is_eligible_search": "true",
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
        if "variant_dict" in item and isinstance(item["variant_dict"], str):
            item["variant_dict"] = json.loads(item["variant_dict"])
        normalized.append(item)
    return "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in normalized) + ("\n" if normalized else "")
