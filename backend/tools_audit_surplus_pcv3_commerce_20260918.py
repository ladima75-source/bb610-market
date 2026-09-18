from __future__ import annotations

"""Read-only diagnostic for the 9 duplicate/canonical commerce pairs + example-product.

No Product Card, commerce_map, sku_commerce, price, stock or media data is modified.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as cards
from backend.services.product_commerce import commerce_map as live_commerce_map
from backend.services.catalog_cms import admin_detail

REPORT_ROOT = ROOT / "var" / "reports"

PAIRS = {
    "master-npk-13-40-13": "master-13-40-13",
    "master-npk-15-5-30": "master-15-5-30",
    "master-npk-20-20-20": "master-20-20-20",
    "master-npk-3-11-38": "master-3-11-38",
    "plantafol-npk-0-25-50": "plantafol-0-25-50",
    "plantafol-npk-10-54-10": "plantafol-10-54-10",
    "plantafol-npk-20-20-20": "plantafol-20-20-20",
    "plantafol-npk-30-10-10": "plantafol-30-10-10",
    "plantafol-npk-5-15-45": "plantafol-5-15-45",
}
EXAMPLE_SLUG = "example-product"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def card_by_slug(slug: str) -> dict:
    hits = [x for x in cards.list_cards() if str(x.get("slug") or "") == slug]
    if len(hits) != 1:
        raise RuntimeError(f"{slug}: expected exactly one card, got {len(hits)}")
    card = cards.get(str(hits[0].get("product_id") or ""))
    if not isinstance(card, dict):
        raise RuntimeError(f"{slug}: product file missing")
    return card


def mapping_index() -> dict[str, dict]:
    return {
        str(x.get("product_id") or ""): x
        for x in (cards.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }


def card_skus(card: dict) -> dict[str, dict]:
    return {
        str(x.get("sku_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict) and x.get("sku_id")
    }


def describe_side(card: dict, mapping: dict | None, live: dict[str, dict]) -> dict:
    content = card.get("content") or {}
    skus = card_skus(card)

    parent = str((mapping or {}).get("existing_product_key") or "").strip()
    detail = admin_detail(parent) if parent else None

    bindings = []
    for row in (mapping or {}).get("skus") or []:
        if not isinstance(row, dict):
            continue
        v3_sku_id = str(row.get("sku_id") or "").strip()
        commerce_key = str(row.get("existing_commerce_sku_key") or "").strip()
        sku = skus.get(v3_sku_id) or {}
        commerce = live.get(commerce_key) if commerce_key else None
        bindings.append({
            "sku_id": v3_sku_id,
            "package": sku.get("package"),
            "sku_code": sku.get("sku_code"),
            "commerce_key": commerce_key,
            "price": (commerce or {}).get("price"),
            "sale_price": (commerce or {}).get("sale_price"),
            "effective_price": (commerce or {}).get("effective_price"),
            "availability": (commerce or {}).get("availability"),
            "stock_qty": (commerce or {}).get("stock_qty"),
            "enabled": bool((commerce or {}).get("enabled")) if commerce else None,
            "commerce_row_exists": bool(commerce),
        })

    return {
        "product_id": card.get("product_id"),
        "slug": card.get("slug"),
        "title": content.get("title"),
        "enabled": card.get("enabled"),
        "parent": parent,
        "parent_published": (detail or {}).get("published") if isinstance(detail, dict) else None,
        "parent_detail_exists": isinstance(detail, dict),
        "mapping_exists": bool(mapping),
        "bindings": bindings,
    }


def _package_map(side: dict) -> dict[str, dict]:
    out = {}
    for x in side["bindings"]:
        key = str(x.get("package") or "").strip().lower()
        if key:
            out[key] = x
    return out


def compare_pair(duplicate: dict, canonical: dict) -> dict:
    d = _package_map(duplicate)
    c = _package_map(canonical)
    packages = sorted(set(d) | set(c))
    rows = []

    for package in packages:
        a = d.get(package)
        b = c.get(package)
        rows.append({
            "package": package,
            "duplicate_commerce_key": (a or {}).get("commerce_key"),
            "canonical_commerce_key": (b or {}).get("commerce_key"),
            "duplicate_price": (a or {}).get("effective_price"),
            "canonical_price": (b or {}).get("effective_price"),
            "duplicate_enabled": (a or {}).get("enabled"),
            "canonical_enabled": (b or {}).get("enabled"),
            "duplicate_availability": (a or {}).get("availability"),
            "canonical_availability": (b or {}).get("availability"),
            "same_commerce_key": bool(a and b and a.get("commerce_key") == b.get("commerce_key")),
            "same_price": bool(a and b and a.get("effective_price") == b.get("effective_price")),
        })

    return {
        "same_parent": duplicate.get("parent") == canonical.get("parent"),
        "same_package_set": set(d) == set(c),
        "rows": rows,
    }


def main() -> int:
    mappings = mapping_index()
    live = live_commerce_map()

    pairs = []
    for duplicate_slug, canonical_slug in PAIRS.items():
        duplicate_card = card_by_slug(duplicate_slug)
        canonical_card = card_by_slug(canonical_slug)

        duplicate = describe_side(
            duplicate_card,
            mappings.get(str(duplicate_card.get("product_id") or "")),
            live,
        )
        canonical = describe_side(
            canonical_card,
            mappings.get(str(canonical_card.get("product_id") or "")),
            live,
        )
        comparison = compare_pair(duplicate, canonical)
        pairs.append({
            "duplicate": duplicate,
            "canonical": canonical,
            "comparison": comparison,
        })

    example_card = card_by_slug(EXAMPLE_SLUG)
    example = describe_side(
        example_card,
        mappings.get(str(example_card.get("product_id") or "")),
        live,
    )

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"pcv3-surplus-commerce-audit-{stamp()}.json"
    payload = {
        "schema_version": "1.0",
        "pairs": pairs,
        "example": example,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("BB610 PCV3 SURPLUS COMMERCE AUDIT")
    print("MODE: READ_ONLY")
    print("PAIRS:", len(pairs))
    print()

    for item in pairs:
        d = item["duplicate"]
        c = item["canonical"]
        cmp = item["comparison"]
        print("PAIR:", d["slug"], "=>", c["slug"])
        print(
            "  DUPLICATE:",
            "parent=", d["parent"] or "-",
            "published=", d["parent_published"],
            "card_enabled=", d["enabled"],
        )
        print(
            "  CANONICAL:",
            "parent=", c["parent"] or "-",
            "published=", c["parent_published"],
            "card_enabled=", c["enabled"],
        )
        print(
            "  CHECK:",
            "same_parent=", cmp["same_parent"],
            "same_package_set=", cmp["same_package_set"],
        )
        for row in cmp["rows"]:
            print(
                "   ",
                row["package"],
                "| DUP", row["duplicate_commerce_key"],
                "price=", row["duplicate_price"],
                "enabled=", row["duplicate_enabled"],
                "avail=", row["duplicate_availability"],
                "|| CAN", row["canonical_commerce_key"],
                "price=", row["canonical_price"],
                "enabled=", row["canonical_enabled"],
                "avail=", row["canonical_availability"],
                "| same_price=", row["same_price"],
            )
        print()

    print("EXAMPLE-PRODUCT")
    print(
        "  product_id=", example["product_id"],
        "parent=", example["parent"] or "-",
        "published=", example["parent_published"],
        "card_enabled=", example["enabled"],
    )
    for row in example["bindings"]:
        print(
            "   ",
            row["package"],
            "|", row["commerce_key"],
            "price=", row["effective_price"],
            "enabled=", row["enabled"],
            "avail=", row["availability"],
        )

    print()
    print("REPORT:", path)
    print("RESULT: PASS (READ_ONLY)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
