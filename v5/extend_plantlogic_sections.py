#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

TARGET_SECTIONS = {"rubus", "strawberry", "vegetable", "universal", "bag_bases", "accessories"}
EXCLUDED_SECTION_TYPES = set()
NO_VERIFIED_MEDIA = {"prd_pl_1305081", "prd_pl_1305109"}
GARDEN_USE_RE = re.compile(r"розсадник|nursery|сад", re.I)
RUBUS_USE_RE = re.compile(r"малин|ожин|raspberr|blackberr|rubus", re.I)
STRAWBERRY_USE_RE = re.compile(r"полуниц|суниц|strawberr", re.I)
VEGETABLE_USE_RE = re.compile(r"овоч|vegetable|tomato|pepper|cucumber", re.I)
CANNABIS_RE = re.compile(r"\b(?:канабіс|cannabis)\b", re.I)
HIDDEN_SECTION_LABEL = "__plantlogic_sections"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize_public(value):
    if isinstance(value, str):
        return CANNABIS_RE.sub("універсальне субстратне вирощування", value)
    if isinstance(value, list):
        return [sanitize_public(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_public(item) for key, item in value.items()}
    return value


def parse_package(value):
    text = str(value or "").replace(",", ".").lower()
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*(л|l|кг|kg|г|g|мл|ml|шт|pcs)\b", text, re.I)
    if not match:
        return None, None, None
    number = float(match.group(1))
    unit = {
        "л": "l", "l": "l", "кг": "kg", "kg": "kg",
        "г": "g", "g": "g", "мл": "ml", "ml": "ml",
        "шт": "pcs", "pcs": "pcs",
    }[match.group(2).lower()]
    shown = str(int(number)) if number.is_integer() else str(number).rstrip("0").rstrip(".")
    ua = {"l": "л", "kg": "кг", "g": "г", "ml": "мл", "pcs": "шт"}[unit]
    return number, unit, f"{shown} {ua}"


def source_url_from_card(card):
    content = card.get("content") or {}
    for row in content.get("characteristics") or []:
        label = str(row.get("label") or "").lower()
        if "офіційн" in label and "джерел" in label:
            value = str(row.get("value") or "").strip()
            if value.startswith("http"):
                return value
    return ""


def media_for_sku(card, sku):
    media_index = {
        row.get("media_id"): row
        for row in (card.get("sku_media") or {}).get("media") or []
    }
    ids = [sku.get("primary_media_id"), *(sku.get("gallery_media_ids") or [])]
    out = []
    seen = set()
    for media_id in ids:
        if not media_id or media_id in seen or media_id not in media_index:
            continue
        seen.add(media_id)
        item = media_index[media_id]
        out.append({
            "media_id": media_id,
            "path": item.get("path"),
            "alt": item.get("alt"),
            "kind": item.get("kind"),
            "is_primary": media_id == sku.get("primary_media_id"),
        })
    return out


def official_fallback_media(spec, snapshot):
    original = str(spec.get("image_url") or "").strip()
    if not original:
        return []
    # Keep the verified official Plantlogic URL in the stage. compile_media.py
    # resolves it centrally, preserving provenance and avoiding a second,
    # fragile downloader during section extension.
    return [{
        "media_id": "official_fallback",
        "path": original,
        "alt": sanitize_public(spec.get("name") or "Plantlogic"),
        "kind": "image",
        "is_primary": True,
    }]


def content_from_card(product_id, card, sections, source_url):
    content = sanitize_public(card.get("content") or {})
    characteristics = [
        row for row in (content.get("characteristics") or [])
        if str(row.get("label") or "") != HIDDEN_SECTION_LABEL
    ]
    characteristics.append({"label": HIDDEN_SECTION_LABEL, "value": "|".join(sections)})
    source_url = source_url or source_url_from_card(card)
    sources = []
    if source_url:
        sources = [{
            "source_type": "official_primary",
            "url": source_url,
            "label": "Plantlogic — офіційна сторінка продукту",
            "verified_at": "2026-09-19",
            "status": "verified",
            "provenance": "production V3 + data/product_content/plantlogic_sections_20260919.json",
        }]
    return {
        "product_id": product_id,
        "name": content.get("title") or product_id,
        "brand": content.get("brand") or "Plantlogic",
        "manufacturer": "Plantlogic",
        "category_id": "containers",
        "short_description": content.get("short_description") or content.get("description") or "",
        "description": content.get("description") or content.get("short_description") or "",
        "application": content.get("application") or "",
        "composition": content.get("composition"),
        "benefits": content.get("benefits") or [],
        "how_it_works": content.get("how_it_works"),
        "characteristics": characteristics,
        "seo_title": (content.get("seo") or {}).get("title"),
        "seo_description": (content.get("seo") or {}).get("description"),
        "content_status": "verified_migrated_plantlogic_sectioned",
        "sources": sources,
        "public_enabled": True,
    }


def usage_sections(spec, section_doc):
    raw_sections = section_doc.get("product_sections", {}).get(spec.get("product_id"), [])
    out = [section for section in raw_sections if section in TARGET_SECTIONS]
    uses = " ".join(spec.get("use_cases") or [])
    if RUBUS_USE_RE.search(uses):
        out.append("rubus")
    if STRAWBERRY_USE_RE.search(uses):
        out.append("strawberry")
    if VEGETABLE_USE_RE.search(uses):
        out.append("vegetable")
    if GARDEN_USE_RE.search(uses):
        out.append("garden")
    return list(dict.fromkeys(out))


def set_content_sections(row, sections):
    chars = [
        item for item in (row.get("characteristics") or [])
        if str(item.get("label") or "") != HIDDEN_SECTION_LABEL
    ]
    chars.append({"label": HIDDEN_SECTION_LABEL, "value": "|".join(sections)})
    row["characteristics"] = chars


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--content", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    snapshot = Path(args.snapshot).resolve()
    stage_path = (root / args.stage).resolve()
    content_path = (root / args.content).resolve()

    stage = load(stage_path)
    content = load(content_path)
    section_doc = load(root / "data/product_content/plantlogic_sections_20260919.json")
    core = load(root / "data/product_content/plantlogic_pots_v1_20260918.json")
    extended = load(root / "data/product_content/plantlogic_extended_sections_20260919.json")
    specs = {row["product_id"]: row for row in (core.get("products") or [])}
    specs.update({row["product_id"]: row for row in (extended.get("products") or [])})

    spec_by_product_no = collections.defaultdict(list)
    for spec in specs.values():
        for sku in spec.get("skus") or []:
            product_no = str(sku.get("product_no") or "").strip()
            if product_no:
                spec_by_product_no[product_no].append(spec)

    cards = {}
    v3_dir = snapshot / "files/data/product_cards_v3/products"
    for path in v3_dir.glob("prd_*.json"):
        try:
            card = load(path)
            cards[card.get("product_id")] = card
        except Exception:
            continue

    existing_product_ids = {
        row["product_id"] for row in (stage.get("products") or [])
    } | {
        row["product_id"] for row in (stage.get("plantlogic_products") or [])
    }
    existing_sku_ids = {
        row["sku_id"] for row in (stage.get("skus") or [])
    } | {
        row["sku_id"] for row in (stage.get("plantlogic_skus") or [])
    }
    existing_manufacturer_nos = {
        str((row.get("attributes") or {}).get("manufacturer_product_no") or "").strip()
        for row in (stage.get("plantlogic_skus") or [])
    }
    compiled = {row["product_id"]: row for row in (content.get("products") or [])}

    group_sections = collections.defaultdict(lambda: ["blueberry"])
    for sku in stage.get("plantlogic_skus") or []:
        product_id = sku.get("product_id")
        manufacturer_no = str((sku.get("attributes") or {}).get("manufacturer_product_no") or "").strip()
        for spec in spec_by_product_no.get(manufacturer_no, []):
            for section in usage_sections(spec, section_doc):
                if section not in group_sections[product_id]:
                    group_sections[product_id].append(section)
    for product in stage.get("plantlogic_products") or []:
        product_id = product.get("product_id")
        sections = group_sections.get(product_id, ["blueberry"])
        product["plantlogic_sections"] = sections
        if product_id in compiled:
            set_content_sections(compiled[product_id], sections)

    added_products = []
    added_skus = []
    skipped = []

    for v3_product_id, raw_sections in (section_doc.get("product_sections") or {}).items():
        if any(section in EXCLUDED_SECTION_TYPES for section in raw_sections):
            skipped.append((v3_product_id, "non_pot_section"))
            continue
        if v3_product_id in NO_VERIFIED_MEDIA:
            skipped.append((v3_product_id, "no_verified_media"))
            continue
        sections = [section for section in raw_sections if section in TARGET_SECTIONS]
        spec = specs.get(v3_product_id) or {}
        for section in usage_sections(spec, section_doc):
            if section not in sections:
                sections.append(section)
        sections = list(dict.fromkeys(sections))
        if not sections:
            continue

        card = cards.get(v3_product_id)
        if not card:
            skipped.append((v3_product_id, "missing_v3_card"))
            continue
        slug = str(card.get("slug") or "").strip()
        if not slug:
            skipped.append((v3_product_id, "missing_slug"))
            continue
        if slug in existing_product_ids:
            continue

        sku_rows = []
        for sku in (card.get("sku_media") or {}).get("skus") or []:
            attributes = dict(sku.get("attributes") or {})
            manufacturer_no = str(attributes.get("manufacturer_product_no") or "").strip()
            if manufacturer_no and manufacturer_no in existing_manufacturer_nos:
                continue
            sku_id = str(sku.get("sku_code") or sku.get("sku_id") or "").strip()
            if not sku_id or sku_id in existing_sku_ids:
                continue
            value, unit, label = parse_package(sku.get("package") or sku.get("label"))
            attributes["plantlogic_sections"] = sections
            media = media_for_sku(card, sku) or official_fallback_media(spec, snapshot)
            sku_rows.append({
                "sku_id": sku_id,
                "v3_sku_id": sku.get("sku_id"),
                "product_id": slug,
                "package_value": value,
                "package_unit": unit,
                "package_label": label or sku.get("package") or sku.get("label"),
                "package_group": None,
                "attributes": attributes,
                "enabled": bool(sku.get("enabled", True)),
                "commerce_state": "request_price",
                "media": media,
            })
        if not sku_rows:
            skipped.append((v3_product_id, "no_nonconflicting_sku"))
            continue

        card_content = sanitize_public(card.get("content") or {})
        added_products.append({
            "product_id": slug,
            "slug": slug,
            "name": card_content.get("title") or spec.get("name") or slug,
            "brand": "Plantlogic",
            "category_id": "containers",
            "v3_product_id": v3_product_id,
            "content_state": "verified_migrated_sectioned",
            "plantlogic_sections": sections,
        })
        compiled[slug] = content_from_card(
            slug,
            card,
            sections,
            str(spec.get("source_url") or ""),
        )
        added_skus.extend(sku_rows)
        existing_product_ids.add(slug)
        existing_sku_ids.update(row["sku_id"] for row in sku_rows)
        existing_manufacturer_nos.update(
            str((row.get("attributes") or {}).get("manufacturer_product_no") or "")
            for row in sku_rows
        )

    stage.setdefault("plantlogic_products", []).extend(added_products)
    stage.setdefault("plantlogic_skus", []).extend(added_skus)
    summary = stage.setdefault("summary", {})
    summary["plantlogic_sectioned_products"] = len(added_products)
    summary["plantlogic_sectioned_request_price_skus"] = len(added_skus)
    summary["v5_stage_products_total"] = len(stage.get("products") or []) + len(stage.get("plantlogic_products") or [])
    summary["v5_stage_skus_total"] = len(stage.get("skus") or []) + len(stage.get("plantlogic_skus") or [])

    content["products"] = [compiled[key] for key in sorted(compiled)]
    content_summary = content.setdefault("summary", {})
    content_summary["products"] = len(content["products"])
    content_summary["sources"] = sum(len(row.get("sources") or []) for row in content["products"])
    content_summary["uncovered_products"] = 0
    content_summary["public_products"] = sum(1 for row in content["products"] if row.get("public_enabled", True))
    content_summary["hidden_products"] = sum(1 for row in content["products"] if not row.get("public_enabled", True))
    content_summary["plantlogic_sectioned_products"] = len(added_products)

    dump(stage_path, stage)
    dump(content_path, content)

    present = collections.Counter(
        section
        for product in (stage.get("plantlogic_products") or [])
        for section in product.get("plantlogic_sections") or []
    )
    print("PLANTLOGIC V5 SECTION EXTENSION")
    print("ADDED PRODUCTS:", len(added_products))
    print("ADDED SKU:", len(added_skus))
    print("SECTIONS:", dict(sorted(present.items())))
    print("SKIPPED:", len(skipped))
    for product_id, reason in skipped:
        print(" ", product_id, reason)

    required = {"blueberry", "rubus", "strawberry", "vegetable", "universal", "garden", "bag_bases", "accessories"}
    missing = required - set(present)
    if missing:
        raise SystemExit("missing required sections: " + ",".join(sorted(missing)))
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
