from __future__ import annotations

"""Read-only readiness audit for the 34 Plantlogic Product Card v3 drafts.

Checks:
- exact V3 card presence and SKU count from the verified Plantlogic master;
- media readiness per SKU (resolvable primary image + gallery count);
- V3 commerce-map coverage and live sku_commerce state;
- legacy catalog identity/media/commerce for the two known legacy Plantlogic products;
- publication/enabled state.

No writes.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.services.product_cards_v3_media import _is_resolvable
from backend.services.product_commerce import commerce_map as live_commerce_map
from backend.services.catalog_cms import admin_detail

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_pots_v1_20260918.json"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37

KNOWN_LEGACY = {
    "plantlogic-25l-round-new-1308125": "plantlogic-25-round-1308125",
    "plantlogic-40l-round-u-grooves-1308041": "plantlogic-40-round-ugroove-1308041",
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_manifest() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    products = doc.get("products") if isinstance(doc, dict) else None
    if not isinstance(products, list) or len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} Plantlogic products")
    total_skus = sum(len(x.get("skus") or []) for x in products if isinstance(x, dict))
    if total_skus != EXPECTED_SKUS:
        raise RuntimeError(f"expected {EXPECTED_SKUS} Plantlogic SKU; got {total_skus}")
    return doc


def card_by_pid(pid: str) -> dict | None:
    card = pcv3.get(pid)
    return card if isinstance(card, dict) else None


def mapping_index() -> dict[str, dict]:
    return {
        str(x.get("product_id") or ""): x
        for x in (pcv3.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }


def media_index(card: dict) -> dict[str, dict]:
    return {
        str(x.get("media_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }


def sku_readiness(card: dict, mapping: dict | None, live: dict[str, dict]) -> list[dict]:
    media = media_index(card)
    links = {
        str(x.get("sku_id") or ""): str(x.get("existing_commerce_sku_key") or "").strip()
        for x in (mapping or {}).get("skus") or []
        if isinstance(x, dict) and x.get("sku_id")
    }

    rows = []
    for sku in ((card.get("sku_media") or {}).get("skus") or []):
        if not isinstance(sku, dict):
            continue
        mid = str(sku.get("primary_media_id") or "")
        mrow = media.get(mid)
        mpath = str((mrow or {}).get("path") or "")
        key = links.get(str(sku.get("sku_id") or ""), "")
        commerce = live.get(key) if key else None
        rows.append({
            "sku_id": sku.get("sku_id"),
            "sku_code": sku.get("sku_code"),
            "package": sku.get("package"),
            "primary_media_id": sku.get("primary_media_id"),
            "primary_media_path": mpath,
            "primary_media_ready": bool(mpath and _is_resolvable(mpath)),
            "gallery_count": len(sku.get("gallery_media_ids") or []),
            "commerce_key": key,
            "commerce_bound": bool(key and isinstance(commerce, dict)),
            "commerce_price": (commerce or {}).get("price") if isinstance(commerce, dict) else None,
            "commerce_availability": (commerce or {}).get("availability") if isinstance(commerce, dict) else None,
            "commerce_enabled": bool((commerce or {}).get("enabled")) if isinstance(commerce, dict) else None,
        })
    return rows


def legacy_media(detail: dict | None) -> list[str]:
    if not isinstance(detail, dict):
        return []
    values: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, str):
            raw = value.strip()
            if raw and (
                raw.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".avif", ".svg"))
                or "/media/" in raw
                or raw.startswith("http://")
                or raw.startswith("https://")
            ):
                values.add(raw)
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(detail)
    return sorted(values)


def main() -> int:
    doc = load_manifest()
    mappings = mapping_index()
    live = live_commerce_map()

    rows = []
    missing = []
    total_skus = media_ready = commerce_bound = 0

    for spec in doc["products"]:
        pid = str(spec["product_id"])
        slug = str(spec["slug"])
        card = card_by_pid(pid)
        if not card:
            missing.append({"product_id": pid, "slug": slug, "reason": "v3 card missing"})
            continue
        if str(card.get("slug") or "") != slug:
            missing.append({"product_id": pid, "slug": slug, "reason": f"runtime slug={card.get('slug')}"})
            continue

        mapping = mappings.get(pid)
        skus = sku_readiness(card, mapping, live)
        total_skus += len(skus)
        media_ready += sum(1 for x in skus if x["primary_media_ready"])
        commerce_bound += sum(1 for x in skus if x["commerce_bound"])

        legacy_key = KNOWN_LEGACY.get(slug)
        legacy = admin_detail(legacy_key) if legacy_key else None
        legacy_images = legacy_media(legacy)

        rows.append({
            "product_id": pid,
            "slug": slug,
            "title": (card.get("content") or {}).get("title"),
            "enabled": bool(card.get("enabled")),
            "sku_count": len(skus),
            "media_ready_sku": sum(1 for x in skus if x["primary_media_ready"]),
            "commerce_bound_sku": sum(1 for x in skus if x["commerce_bound"]),
            "mapping_parent": str((mapping or {}).get("existing_product_key") or ""),
            "legacy_key": legacy_key,
            "legacy_exists": isinstance(legacy, dict),
            "legacy_published": (legacy or {}).get("published") if isinstance(legacy, dict) else None,
            "legacy_sku_count": len((legacy or {}).get("skus") or []) if isinstance(legacy, dict) else 0,
            "legacy_media": legacy_images,
            "skus": skus,
        })

    report = {
        "runtime_cards_expected": EXPECTED_PRODUCTS,
        "runtime_cards_found": len(rows),
        "missing": missing,
        "sku_expected": EXPECTED_SKUS,
        "sku_found": total_skus,
        "media_ready_sku": media_ready,
        "commerce_bound_sku": commerce_bound,
        "cards_enabled": sum(1 for x in rows if x["enabled"]),
        "cards_with_any_media": sum(1 for x in rows if x["media_ready_sku"] > 0),
        "cards_with_any_commerce": sum(1 for x in rows if x["commerce_bound_sku"] > 0),
        "known_legacy_cards": sum(1 for x in rows if x["legacy_exists"]),
        "products": rows,
    }

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"plantlogic-readiness-{stamp()}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("BB610 PLANTLOGIC PRODUCT CARD V3 READINESS AUDIT")
    print("MODE: READ_ONLY")
    print(f"CARDS: {len(rows)}/{EXPECTED_PRODUCTS}")
    print(f"SKU: {total_skus}/{EXPECTED_SKUS}")
    print(f"ENABLED CARDS: {report['cards_enabled']}")
    print(f"SKU WITH PRIMARY MEDIA: {media_ready}/{EXPECTED_SKUS}")
    print(f"SKU WITH COMMERCE BINDING: {commerce_bound}/{EXPECTED_SKUS}")
    print(f"CARDS WITH ANY MEDIA: {report['cards_with_any_media']}/{EXPECTED_PRODUCTS}")
    print(f"CARDS WITH ANY COMMERCE: {report['cards_with_any_commerce']}/{EXPECTED_PRODUCTS}")
    print(f"KNOWN LEGACY CARDS FOUND: {report['known_legacy_cards']}/{len(KNOWN_LEGACY)}")
    print()

    for item in rows:
        print(
            f"{item['slug']} | enabled={item['enabled']} | sku={item['sku_count']} | "
            f"media={item['media_ready_sku']}/{item['sku_count']} | "
            f"commerce={item['commerce_bound_sku']}/{item['sku_count']} | "
            f"parent={item['mapping_parent'] or '-'}"
        )
        if item["legacy_key"]:
            print(
                f"  LEGACY {item['legacy_key']} | exists={item['legacy_exists']} | "
                f"published={item['legacy_published']} | legacy_sku={item['legacy_sku_count']} | "
                f"legacy_media={len(item['legacy_media'])}"
            )
            for media in item["legacy_media"][:8]:
                print("   MEDIA:", media)

    print()
    if missing:
        print("MISSING:")
        for row in missing:
            print(" ", row)
    print("REPORT:", path)
    print("RESULT: PASS (READ_ONLY)" if not missing and len(rows) == EXPECTED_PRODUCTS and total_skus == EXPECTED_SKUS else "RESULT: REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
