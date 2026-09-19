from __future__ import annotations

"""Read-only integrity audit for all BB610 Product Card v3 cards.

Unlike the historical content-coverage audit, this audit does not assume a fixed
catalog cardinality. It validates every runtime card and the relationships
between Product Card v3, SKU media and commerce mappings.
"""

from collections import Counter, defaultdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3


def _norm(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def main() -> int:
    rows = pcv3.list_cards()
    cards: list[dict] = []
    invalid_cards: list[str] = []
    duplicate_slugs: list[str] = []
    duplicate_sku_codes: list[str] = []
    enabled_without_enabled_sku: list[str] = []
    enabled_sku_without_primary: list[str] = []
    missing_local_media: list[str] = []
    missing_mapping: list[str] = []
    mapping_unknown_product: list[str] = []
    mapping_unknown_sku: list[str] = []
    duplicate_enabled_commerce_keys: list[str] = []

    slug_counts: Counter[str] = Counter()
    title_groups: dict[str, list[str]] = defaultdict(list)
    card_by_id: dict[str, dict] = {}
    sku_ids_by_product: dict[str, set[str]] = {}
    global_sku_code_map: dict[str, list[str]] = defaultdict(list)

    for row in rows:
        pid = str(row.get("product_id") or "").strip()
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            invalid_cards.append(f"{pid}:missing_file")
            continue

        try:
            pcv3.validate(card)
        except Exception as exc:
            invalid_cards.append(f"{pid}:{exc}")

        cards.append(card)
        card_by_id[pid] = card

        slug = str(card.get("slug") or "").strip()
        slug_counts[slug] += 1

        content = card.get("content") or {}
        title = _norm(content.get("title"))
        if title:
            title_groups[title].append(pid)

        sm = card.get("sku_media") or {}
        media = sm.get("media") or [] if isinstance(sm, dict) else []
        skus = sm.get("skus") or [] if isinstance(sm, dict) else []
        media_index = {
            str(x.get("media_id") or ""): x
            for x in media if isinstance(x, dict)
        }
        sku_ids: set[str] = set()
        enabled_skus = []

        for sku in skus:
            if not isinstance(sku, dict):
                continue
            sid = str(sku.get("sku_id") or "").strip()
            sku_ids.add(sid)
            if sku.get("enabled") is True:
                enabled_skus.append(sku)

            code = _norm(sku.get("sku_code"))
            if code:
                global_sku_code_map[code].append(f"{pid}:{sid}")

            if sku.get("enabled") is True:
                primary = str(sku.get("primary_media_id") or "").strip()
                if not primary or primary not in media_index:
                    enabled_sku_without_primary.append(f"{pid}:{sid}")

            for mid in [
                str(sku.get("primary_media_id") or "").strip(),
                *[str(x).strip() for x in (sku.get("gallery_media_ids") or [])],
            ]:
                if not mid or mid not in media_index:
                    continue
                path = str((media_index[mid] or {}).get("path") or "").strip()
                if not path or path.startswith(("http://", "https://", "data:")):
                    continue
                local = ROOT / path.lstrip("/")
                if not local.exists():
                    missing_local_media.append(f"{pid}:{sid}:{mid}:{path}")

        sku_ids_by_product[pid] = sku_ids
        if card.get("enabled") is True and not enabled_skus:
            enabled_without_enabled_sku.append(pid)

    duplicate_slugs = [
        slug for slug, count in slug_counts.items()
        if slug and count > 1
    ]
    duplicate_sku_codes = [
        f"{code}=>{','.join(owners)}"
        for code, owners in global_sku_code_map.items()
        if len(owners) > 1
    ]

    mappings = [
        x for x in (pcv3.commerce_map().get("products") or [])
        if isinstance(x, dict)
    ]
    mapping_by_product = {
        str(x.get("product_id") or "").strip(): x
        for x in mappings if str(x.get("product_id") or "").strip()
    }

    enabled_ids = {
        str(card.get("product_id") or "").strip()
        for card in cards if card.get("enabled") is True
    }
    for pid in sorted(enabled_ids):
        if pid not in mapping_by_product:
            missing_mapping.append(pid)

    commerce_key_owners: dict[str, list[str]] = defaultdict(list)
    for mapping in mappings:
        pid = str(mapping.get("product_id") or "").strip()
        if not pid:
            continue
        if pid not in card_by_id:
            mapping_unknown_product.append(pid)
            continue

        known_skus = sku_ids_by_product.get(pid, set())
        for link in mapping.get("skus") or []:
            if not isinstance(link, dict):
                continue
            sid = str(link.get("sku_id") or "").strip()
            key = str(link.get("existing_commerce_sku_key") or "").strip()
            if sid and sid not in known_skus:
                mapping_unknown_sku.append(f"{pid}:{sid}")
            if key and pid in enabled_ids:
                commerce_key_owners[key].append(f"{pid}:{sid}")

    duplicate_enabled_commerce_keys = [
        f"{key}=>{','.join(owners)}"
        for key, owners in commerce_key_owners.items()
        if len(owners) > 1
    ]

    duplicate_titles = [
        f"{title}=>{','.join(ids)}"
        for title, ids in sorted(title_groups.items())
        if len(ids) > 1
    ]

    print("===== PRODUCT CARD V3 INTEGRITY AUDIT =====")
    print(f"RUNTIME_CARDS={len(cards)}")
    print(f"ENABLED_CARDS={len(enabled_ids)}")
    print(f"COMMERCE_MAPPINGS={len(mappings)}")
    print(f"INVALID_CARDS={len(invalid_cards)}")
    print(f"DUPLICATE_SLUGS={len(duplicate_slugs)}")
    print(f"DUPLICATE_TITLES={len(duplicate_titles)}")
    print(f"DUPLICATE_SKU_CODES={len(duplicate_sku_codes)}")
    print(f"ENABLED_WITHOUT_ENABLED_SKU={len(enabled_without_enabled_sku)}")
    print(f"ENABLED_SKU_WITHOUT_PRIMARY_MEDIA={len(enabled_sku_without_primary)}")
    print(f"MISSING_LOCAL_MEDIA={len(missing_local_media)}")
    print(f"ENABLED_WITHOUT_COMMERCE_MAPPING={len(missing_mapping)}")
    print(f"MAPPING_UNKNOWN_PRODUCT={len(mapping_unknown_product)}")
    print(f"MAPPING_UNKNOWN_SKU={len(mapping_unknown_sku)}")
    print(f"DUPLICATE_ENABLED_COMMERCE_KEYS={len(duplicate_enabled_commerce_keys)}")

    def emit(label: str, values: list[str]) -> None:
        if values:
            print(label + "=" + " | ".join(values[:40]))

    emit("INVALID_CARD_DETAILS", invalid_cards)
    emit("DUPLICATE_SLUG_DETAILS", duplicate_slugs)
    emit("DUPLICATE_TITLE_DETAILS", duplicate_titles)
    emit("DUPLICATE_SKU_CODE_DETAILS", duplicate_sku_codes)
    emit("ENABLED_WITHOUT_ENABLED_SKU_IDS", enabled_without_enabled_sku)
    emit("ENABLED_SKU_WITHOUT_PRIMARY_MEDIA_IDS", enabled_sku_without_primary)
    emit("MISSING_LOCAL_MEDIA_DETAILS", missing_local_media)
    emit("ENABLED_WITHOUT_COMMERCE_MAPPING_IDS", missing_mapping)
    emit("MAPPING_UNKNOWN_PRODUCT_IDS", mapping_unknown_product)
    emit("MAPPING_UNKNOWN_SKU_IDS", mapping_unknown_sku)
    emit("DUPLICATE_ENABLED_COMMERCE_KEY_DETAILS", duplicate_enabled_commerce_keys)

    # Duplicate titles are reported for review because one product may
    # intentionally appear in multiple official storefront sections. Missing
    # commerce mappings are also reported rather than failed because some
    # market-test cards legitimately use request-price/preorder workflows.
    hard_errors = (
        invalid_cards
        or duplicate_slugs
        or duplicate_sku_codes
        or enabled_without_enabled_sku
        or enabled_sku_without_primary
        or missing_local_media
        or mapping_unknown_product
        or mapping_unknown_sku
        or duplicate_enabled_commerce_keys
    )
    print("CHECKS=" + ("FAIL" if hard_errors else "PASS"))
    return 2 if hard_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
