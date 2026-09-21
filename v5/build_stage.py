#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path


PRODUCT_ALIASES = {
    "megafol-copy": "megafol",
    "master-13-40-13": "master-npk-13-40-13",
    "master-15-5-30": "master-npk-15-5-30",
    "master-20-20-20": "master-npk-20-20-20",
    "master-3-11-38": "master-npk-3-11-38",
    "plantafol-0-25-50": "plantafol-npk-0-25-50",
    "plantafol-10-54-10": "plantafol-npk-10-54-10",
    "plantafol-20-20-20": "plantafol-npk-20-20-20",
    "plantafol-30-10-10": "plantafol-npk-30-10-10",
    "plantafol-5-15-45": "plantafol-npk-5-15-45",
    "pekacid-0-60-20": "pekacid-npk-0-60-20",
    "ferrilene": "ferrilene-4-8-orto-orto",
    "kemira-rooter": "kemira-ukorinyuvach",
    "magnesium-sulfate": "sulfat-mahniyu",
    "osmocote-landscape-16-9-12": "osmocote-landscape-16-9-12-34m",
    "osmocote-quick-start-22-5-6": "osmocote-quick-start-22-5-6-45m",
    "osmocote-potassium-12-8-19": "osmocote-potassium-12-8-19-34m",
    "osmocote-flowering-12-7-18": "osmocote-bloom-12-7-18-23m",
    "solupotasse": "solupotasse-sulfat-kaliyu",
}

MANUAL_COMMERCE_PRODUCT = {
    "BB610-VLG-KENDALROOT-10L": "kendal-root",
    "BB610-VLG-KENDAL-100ML": "kendal",
    "BB610-VLG-KENDAL-1L": "kendal",
}

MANUAL_PACKAGE = {
    "BB610-VLG-KENDALROOT-10L": (10.0, "l", "10 л"),
    "BB610-VLG-KENDAL-100ML": (100.0, "ml", "100 мл"),
    "BB610-VLG-KENDAL-1L": (1.0, "l", "1 л"),
}

PLANTLOGIC_GROUPS = [
    "prd_pl_bb_round",
    "prd_pl_bb_round_short_legs",
    "prd_pl_bb_round_u",
    "prd_pl_bb_square",
    "prd_pl_bb_square_u",
    "prd_pl_bb_zephyr_v2",
]

PACKAGE_RE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(кг|kg|г|g|мл|ml|л|l)\b",
    re.I,
)
UNIT_MAP = {
    "кг": "kg", "kg": "kg",
    "г": "g", "g": "g",
    "мл": "ml", "ml": "ml",
    "л": "l", "l": "l",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_package(value):
    if not value:
        return None, None, None
    match = PACKAGE_RE.search(str(value).lower())
    if not match:
        return None, None, None
    number = float(match.group(1).replace(",", "."))
    unit = UNIT_MAP[match.group(2).lower()]
    shown = str(int(number)) if number.is_integer() else str(number).rstrip("0").rstrip(".")
    ua = {"kg": "кг", "g": "г", "ml": "мл", "l": "л"}[unit]
    return number, unit, f"{shown} {ua}"


def base_amount(value, unit):
    if value is None or not unit:
        return None, None
    if unit == "kg":
        return value * 1000, "g"
    if unit == "g":
        return value, "g"
    if unit == "l":
        return value * 1000, "ml"
    if unit == "ml":
        return value, "ml"
    return None, None


def package_group(value, unit):
    amount, _ = base_amount(value, unit)
    if amount is None:
        return None
    if amount <= 50:
        return "small"
    if 100 <= amount <= 1000:
        return "medium"
    if amount >= 5000:
        return "large"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--md-out", required=True)
    args = ap.parse_args()

    root = Path(args.snapshot).resolve()
    manifest = load(root / "manifest.json")
    catalog = load(root / "files/data/catalog.master.json")
    commerce = load(root / "db/sku_commerce.json")
    dynamic = load(root / "db/dynamic_skus.json")
    v3_map = load(root / "files/data/product_cards_v3/commerce_map.json")

    v3_cards = {}
    v3_dir = root / "files/data/product_cards_v3/products"
    for path in sorted(v3_dir.glob("prd_*.json")):
        card = load(path)
        v3_cards[card["product_id"]] = card

    catalog_skus = {row["id"]: row for row in catalog.get("skus") or []}
    dynamic_skus = {row["sku"]: row for row in dynamic}

    v3_sku_info = {}
    for product_id, card in v3_cards.items():
        for sku in (card.get("sku_media") or {}).get("skus") or []:
            sid = sku.get("sku_id")
            if sid:
                v3_sku_info[sid] = {
                    "v3_product_id": product_id,
                    "slug": card.get("slug"),
                    "title": (card.get("content") or {}).get("title"),
                    "sku": sku,
                }

    commerce_v3 = {}
    product_to_v3 = {}
    for product in v3_map.get("products") or []:
        raw_key = product.get("existing_product_key")
        canonical = PRODUCT_ALIASES.get(raw_key, raw_key)
        card = v3_cards.get(product.get("product_id"))
        if canonical and card and card.get("enabled"):
            product_to_v3[canonical] = card
        for row in product.get("skus") or []:
            commerce_key = row.get("existing_commerce_sku_key")
            if not commerce_key:
                continue
            info = v3_sku_info.get(row.get("sku_id")) or {}
            commerce_v3[commerce_key] = {
                "existing_product_key": raw_key,
                "v3_product_id": product.get("product_id"),
                "v3_sku_id": row.get("sku_id"),
                **info,
            }

    stage = []
    for row in commerce:
        sku_id = row["sku"]
        raw_product = None
        source = None
        value = unit = label = None

        if sku_id in dynamic_skus:
            src = dynamic_skus[sku_id]
            raw_product = src["product_id"]
            source = "dynamic_sku"
            value = src.get("volume_value")
            unit = (src.get("volume_unit") or "").lower() or None
            label = src.get("variant")
        elif sku_id in catalog_skus:
            src = catalog_skus[sku_id]
            raw_product = src["product_id"]
            source = "catalog_master_sku"
            value, unit, label = parse_package(src.get("variant") or src.get("volume_weight"))
        elif sku_id in commerce_v3:
            src = commerce_v3[sku_id]
            raw_product = src.get("existing_product_key") or src.get("slug")
            source = "commerce_v3_map"
            sku = src.get("sku") or {}
            value, unit, label = parse_package(sku.get("package") or sku.get("label"))
        else:
            raw_product = MANUAL_COMMERCE_PRODUCT.get(sku_id)
            source = "commerce_manual_identity"
            if sku_id in MANUAL_PACKAGE:
                value, unit, label = MANUAL_PACKAGE[sku_id]

        canonical = PRODUCT_ALIASES.get(raw_product, raw_product)
        status = "carry"
        if sku_id == "BB610-TEST-ORDER-001" or canonical == "example-product":
            status = "exclude_test"

        base_value, base_unit = base_amount(value, unit)
        stage.append({
            "sku_id": sku_id,
            "source": source,
            "legacy_product_key": raw_product,
            "canonical_product_key": canonical,
            "package_value": value,
            "package_unit": unit,
            "package_label": label,
            "package_base_value": base_value,
            "package_base_unit": base_unit,
            "package_group": package_group(value, unit),
            "price": row.get("price"),
            "sale_price": row.get("sale_price"),
            "availability": row.get("availability"),
            "stock_qty": row.get("stock_qty"),
            "enabled": row.get("enabled"),
            "updated_at": row.get("updated_at"),
            "migration_status": status,
        })

    carry = [row for row in stage if row["migration_status"] == "carry"]
    grouped = collections.defaultdict(list)
    for row in carry:
        key = (
            row["canonical_product_key"],
            row["package_base_value"],
            row["package_base_unit"],
        )
        grouped[key].append(row)

    duplicate_groups = {
        key: rows for key, rows in grouped.items()
        if key[1] is not None and len(rows) > 1
    }
    v3_referenced = set(commerce_v3)

    def choose(rows):
        def score(row):
            return (
                1 if row.get("enabled") == 1 else 0,
                1 if row.get("price") is not None else 0,
                1 if row["sku_id"] in v3_referenced else 0,
                1 if row["source"] == "catalog_master_sku" else 0,
                row.get("updated_at") or "",
            )
        return max(rows, key=score)

    canonical_ids = {row["sku_id"] for row in carry}
    sku_aliases = []
    price_conflicts = []

    for key, rows in duplicate_groups.items():
        canonical = choose(rows)
        active_prices = {
            row["price"] for row in rows
            if row.get("enabled") == 1 and row.get("price") is not None
        }
        if len(active_prices) > 1:
            price_conflicts.append({
                "product_id": key[0],
                "package_base_value": key[1],
                "package_base_unit": key[2],
                "selected_canonical_sku": canonical["sku_id"],
                "candidates": [
                    {
                        "sku_id": row["sku_id"],
                        "price": row["price"],
                        "updated_at": row.get("updated_at"),
                        "source": row["source"],
                        "v3_mapped": row["sku_id"] in v3_referenced,
                    }
                    for row in rows
                    if row.get("enabled") == 1 and row.get("price") is not None
                ],
            })

        for row in rows:
            if row["sku_id"] == canonical["sku_id"]:
                continue
            canonical_ids.discard(row["sku_id"])
            sku_aliases.append({
                "alias_sku_id": row["sku_id"],
                "canonical_sku_id": canonical["sku_id"],
                "product_id": canonical["canonical_product_key"],
                "package_label": canonical["package_label"],
                "reason": "same_product_same_package",
                "alias_commerce": {
                    "price": row.get("price"),
                    "sale_price": row.get("sale_price"),
                    "availability": row.get("availability"),
                    "stock_qty": row.get("stock_qty"),
                    "enabled": row.get("enabled"),
                    "updated_at": row.get("updated_at"),
                },
            })

    canonical_rows = [row for row in carry if row["sku_id"] in canonical_ids]

    # One old Plantlogic item already exists inside the current grouped family.
    # Keep its stable SKU as a disabled legacy identity, but do not keep a duplicate product card.
    legacy_reparent_product = {
        "plantlogic-40-round-ugroove-1308041": "blueberry-round-u-groove-pots",
    }
    legacy_reparent_rows = [
        row for row in canonical_rows
        if row["canonical_product_key"] in legacy_reparent_product
    ]
    canonical_rows = [
        row for row in canonical_rows
        if row["canonical_product_key"] not in legacy_reparent_product
    ]
    canonical_products = sorted({row["canonical_product_key"] for row in canonical_rows})

    missing_cards = [key for key in canonical_products if key not in product_to_v3]
    if missing_cards:
        raise SystemExit(f"Missing exact V3 product mapping: {missing_cards}")

    products = []
    product_aliases = set()
    for key in canonical_products:
        card = product_to_v3[key]
        content = card.get("content") or {}
        products.append({
            "product_id": key,
            "slug": card.get("slug") or key,
            "name": content.get("title") or key,
            "brand": content.get("brand"),
            "category_id": content.get("category"),
            "v3_product_id": card.get("product_id"),
            "content_state": "candidate_from_v3",
        })
        if card.get("slug") and card["slug"] != key:
            product_aliases.add((card["slug"], key, "legacy_slug"))

    for row in stage:
        raw = row.get("legacy_product_key")
        canonical = row.get("canonical_product_key")
        if raw and canonical and raw != canonical:
            product_aliases.add((raw, canonical, "legacy_product_key"))

    for legacy_product_id, target_product_id in legacy_reparent_product.items():
        product_aliases.add((legacy_product_id, target_product_id, "legacy_product_reparent"))

    def exact_media(commerce_key):
        info = commerce_v3.get(commerce_key)
        if not info:
            return []
        card = v3_cards.get(info.get("v3_product_id"))
        if not card:
            return []
        target = None
        for row in (card.get("sku_media") or {}).get("skus") or []:
            if row.get("sku_id") == info.get("v3_sku_id"):
                target = row
                break
        if not target:
            return []
        media_index = {
            row.get("media_id"): row
            for row in (card.get("sku_media") or {}).get("media") or []
        }
        ids = [target.get("primary_media_id"), *(target.get("gallery_media_ids") or [])]
        result = []
        seen = set()
        for media_id in ids:
            if not media_id or media_id in seen or media_id not in media_index:
                continue
            seen.add(media_id)
            media = media_index[media_id]
            result.append({
                "media_id": media_id,
                "path": media.get("path"),
                "alt": media.get("alt"),
                "kind": media.get("kind"),
                "is_primary": media_id == target.get("primary_media_id"),
            })
        return result

    skus = []
    for row in canonical_rows:
        media = exact_media(row["sku_id"])
        skus.append({
            "sku_id": row["sku_id"],
            "product_id": row["canonical_product_key"],
            "package_value": row["package_value"],
            "package_unit": row["package_unit"],
            "package_label": row["package_label"],
            "package_group": row["package_group"],
            "price": row["price"],
            "sale_price": row["sale_price"],
            "availability": row["availability"],
            "stock_qty": row["stock_qty"],
            "enabled": row["enabled"],
            "updated_at": row["updated_at"],
            "source": row["source"],
            "media_state": "exact_v3_binding" if media else "none",
            "media": media,
        })

    plantlogic_products = []
    plantlogic_skus = []
    for v3_product_id in PLANTLOGIC_GROUPS:
        card = v3_cards[v3_product_id]
        content = card.get("content") or {}
        product_id = card["slug"]
        plantlogic_products.append({
            "product_id": product_id,
            "slug": product_id,
            "name": content.get("title"),
            "brand": content.get("brand"),
            "category_id": "containers",
            "v3_product_id": v3_product_id,
            "content_state": "candidate_from_v3_verified_plantlogic_work",
        })
        media_index = {
            row.get("media_id"): row
            for row in (card.get("sku_media") or {}).get("media") or []
        }
        for sku in (card.get("sku_media") or {}).get("skus") or []:
            value, unit, label = parse_package(sku.get("package") or sku.get("label"))
            ids = [sku.get("primary_media_id"), *(sku.get("gallery_media_ids") or [])]
            media = []
            seen = set()
            for media_id in ids:
                if not media_id or media_id in seen or media_id not in media_index:
                    continue
                seen.add(media_id)
                item = media_index[media_id]
                media.append({
                    "media_id": media_id,
                    "path": item.get("path"),
                    "alt": item.get("alt"),
                    "is_primary": media_id == sku.get("primary_media_id"),
                })
            plantlogic_skus.append({
                "sku_id": sku.get("sku_code") or sku.get("sku_id"),
                "v3_sku_id": sku.get("sku_id"),
                "product_id": product_id,
                "package_value": value,
                "package_unit": unit,
                "package_label": label,
                "package_group": package_group(value, unit),
                "attributes": sku.get("attributes") or {},
                "enabled": bool(sku.get("enabled", True)),
                "commerce_state": "request_price",
                "media": media,
            })

    for legacy in legacy_reparent_rows:
        target_product_id = legacy_reparent_product[legacy["canonical_product_key"]]
        plantlogic_skus.append({
            "sku_id": legacy["sku_id"],
            "v3_sku_id": None,
            "product_id": target_product_id,
            "package_value": legacy.get("package_value"),
            "package_unit": legacy.get("package_unit"),
            "package_label": legacy.get("package_label"),
            "package_group": legacy.get("package_group"),
            "attributes": {
                "legacy_sku": True,
                "legacy_product_id": legacy["canonical_product_key"],
                "identity_status": "preserved_disabled_unresolved_color",
            },
            "enabled": False,
            "commerce_state": "legacy_disabled",
            "media": [],
        })

    excluded = [
        {
            "sku_id": row["sku_id"],
            "product_key": row["canonical_product_key"],
            "reason": row["migration_status"],
        }
        for row in stage
        if row["migration_status"] != "carry"
    ]

    summary = {
        "snapshot_created_at": manifest["created_at"],
        "production_head": manifest["git"]["head"],
        "production_origin_main_at_snapshot": manifest["git"]["origin_main"],
        "source_commerce_rows": len(commerce),
        "excluded_test_rows": len(excluded),
        "canonical_non_plantlogic_products": len(products),
        "canonical_non_plantlogic_skus": len(skus),
        "sku_aliases": len(sku_aliases),
        "price_conflicts": len(price_conflicts),
        "plantlogic_grouped_products": len(plantlogic_products),
        "plantlogic_request_price_skus": len(plantlogic_skus),
        "v5_stage_products_total": len(products) + len(plantlogic_products),
        "v5_stage_skus_total": len(skus) + len(plantlogic_skus),
    }

    output = {
        "schema": "bb610-v5-stage-1",
        "summary": summary,
        "products": products,
        "product_aliases": [
            {"alias": alias, "product_id": product_id, "kind": kind}
            for alias, product_id, kind in sorted(product_aliases)
        ],
        "skus": sorted(skus, key=lambda row: (row["product_id"], row["sku_id"])),
        "sku_aliases": sorted(sku_aliases, key=lambda row: row["alias_sku_id"]),
        "price_conflicts": price_conflicts,
        "plantlogic_products": plantlogic_products,
        "plantlogic_skus": plantlogic_skus,
        "excluded": excluded,
    }

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# BB610 V5 production staging",
        "",
        f"Production snapshot: `{summary['production_head']}`.",
        "",
        f"- Commerce source rows: **{summary['source_commerce_rows']}**",
        f"- Excluded test/example rows: **{summary['excluded_test_rows']}**",
        f"- Canonical non-Plantlogic products: **{summary['canonical_non_plantlogic_products']}**",
        f"- Canonical non-Plantlogic SKU: **{summary['canonical_non_plantlogic_skus']}**",
        f"- Legacy/duplicate SKU aliases: **{summary['sku_aliases']}**",
        f"- Plantlogic grouped products: **{summary['plantlogic_grouped_products']}**",
        f"- Plantlogic request-price SKU: **{summary['plantlogic_request_price_skus']}**",
        f"- Total V5 staging: **{summary['v5_stage_products_total']} products / {summary['v5_stage_skus_total']} SKU**",
        "",
        "## Price conflicts",
        "",
    ]
    if not price_conflicts:
        lines.append("None.")
    else:
        for conflict in price_conflicts:
            candidates = ", ".join(
                f"`{row['sku_id']}` = {row['price']} UAH"
                for row in conflict["candidates"]
            )
            lines.append(
                f"- `{conflict['product_id']}` "
                f"{conflict['package_base_value']:g} {conflict['package_base_unit']}: "
                f"{candidates}; selected `{conflict['selected_canonical_sku']}`."
            )

    lines += [
        "",
        "Production has not been modified or cut over.",
        "",
    ]
    md_out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
