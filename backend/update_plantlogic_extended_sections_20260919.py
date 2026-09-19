from __future__ import annotations

"""Add current-menu Plantlogic products beyond the original pot-only master.

Scope in this batch:
- Strawberry: 18 L trough #1305909
- Bag Bases: Culti-base #13079250/#13079300
- Bag Bases: VF Bag Base #12010300
- Bag Bases + Accessories: Drainage Collection Bag Base #1301036

Rules:
- only Product # values confirmed on current official Plantlogic pages;
- cards are enabled as request-price market-test products through the existing projection;
- no price, stock, availability, sku_commerce or commerce_map writes.
"""

import argparse
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.tools_prepare_pcv3_release import _snapshot_tables

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_extended_sections_20260919.json"
BACKUP_ROOT = ROOT / "var" / "release-backups"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_manifest() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if doc.get("schema_version") != "1.0":
        raise RuntimeError("unexpected manifest schema")
    products = doc.get("products")
    if not isinstance(products, list) or not products:
        raise RuntimeError("manifest has no products")
    return doc


def build_card(spec: dict) -> dict:
    title = str(spec["name"])
    source = str(spec["source_url"])
    image = str(spec["image_url"])
    product_type = str(spec["product_type"])
    purpose = str(spec["purpose"])
    dimensions = str(spec.get("dimensions") or "")
    media_id = f"media_{spec['product_id']}_hero"

    characteristics = [
        {"label": "Виробник", "value": "Plantlogic"},
        {"label": "Тип", "value": product_type},
        {"label": "Призначення", "value": purpose},
        {"label": "Артикул виробника", "value": ", ".join(str(x["product_no"]) for x in spec["skus"])},
        {"label": "Офіційне джерело", "value": source},
    ]
    if dimensions:
        characteristics.insert(4, {"label": "Габарити", "value": dimensions})

    skus = []
    for i, row in enumerate(spec["skus"]):
        skus.append({
            "sku_id": str(row["sku_id"]),
            "sku_code": str(row["sku_code"]),
            "label": str(row["label"]),
            "package": str(row["package"]),
            "primary_media_id": media_id,
            "gallery_media_ids": [],
            "sort_order": i,
            "enabled": True,
            "attributes": {"manufacturer_product_no": str(row["product_no"])},
        })

    card = {
        "schema_version": "3.0",
        "product_id": str(spec["product_id"]),
        "slug": str(spec["slug"]),
        "enabled": True,
        "content": {
            "title": title,
            "brand": "Plantlogic",
            "category": "Контейнери",
            "short_description": str(spec["description"]),
            "description": str(spec["description"]) + " Дані та Product # звірені з поточною офіційною сторінкою Plantlogic.",
            "benefits": [
                {"title": "Офіційна модель Plantlogic", "text": "Модель і Product # взяті з поточної продуктової сторінки виробника."},
                {"title": "Для професійного субстратного виробництва", "text": purpose + "."},
            ],
            "how_it_works": str(spec["description"]),
            "application": purpose,
            "composition": "Конструктивний виріб Plantlogic для систем субстратного вирощування; точний склад матеріалу на використаній сторінці не специфікований.",
            "characteristics": characteristics,
            "seo": {
                "title": title + " | BB610 Market",
                "description": title + ". Офіційна модель Plantlogic, Product # та основні характеристики.",
            },
        },
        "sku_media": {
            "skus": skus,
            "media": [{
                "media_id": media_id,
                "path": image,
                "alt": title,
                "kind": "hero",
                "sort_order": 0,
            }],
        },
    }
    pcv3.validate(card)
    return card


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    doc = load_manifest()
    cards = [build_card(x) for x in doc["products"]]

    runtime = {str(x.get("product_id") or ""): x for x in pcv3.list_cards()}
    creates = [c for c in cards if c["product_id"] not in runtime]
    updates = [c for c in cards if c["product_id"] in runtime and pcv3.get(c["product_id"]) != c]

    print("PLANTLOGIC EXTENDED PRODUCT SECTIONS")
    print("CARDS:", len(cards))
    print("SKU:", sum(len(c["sku_media"]["skus"]) for c in cards))
    print("CREATE:", len(creates))
    print("UPDATE:", len(updates))
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        print("RESULT: PASS (PLAN ONLY)")
        return 0

    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    backup = BACKUP_ROOT / f"plantlogic-extended-sections-{stamp()}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pcv3.BASE, backup / "product_cards_v3")

    try:
        for card in cards:
            if pcv3.get(card["product_id"]) is None:
                pcv3.create(deepcopy(card))
            else:
                pcv3.put(card["product_id"], deepcopy(card))

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce database changed")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed")

        for card in cards:
            live = pcv3.get(card["product_id"])
            if live != card or live.get("enabled") is not True:
                raise RuntimeError(f"post-check mismatch: {card['product_id']}")

        print("RESULT: PASS")
        print("ENABLED CARDS:", len(cards))
        print("ENABLED SKU:", sum(len(c["sku_media"]["skus"]) for c in cards))
        print("COMMERCE/PRICES UNCHANGED: PASS")
        print("BACKUP:", backup)
        return 0
    except Exception:
        if pcv3.BASE.exists():
            shutil.rmtree(pcv3.BASE)
        shutil.copytree(backup / "product_cards_v3", pcv3.BASE)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
