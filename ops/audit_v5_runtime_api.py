#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from decimal import Decimal

DEFAULT_URL = "https://api.market.bb610.com.ua/api/v1/catalog/v5"

EXACT_MEDIA_BLOCKERS = {
    "PL-BB-1308303-BK": {
        "reason": "official_model_media_is_terracotta_selected_sku_is_black",
        "source_url": "https://getplantlogic.com/portfolio-items/30-liter-round-pot-u-groove/",
    },
    "PL-BB-1308041-TC": {
        "reason": "official_model_media_is_black_selected_sku_is_terracotta",
        "source_url": "https://getplantlogic.com/portfolio-items/40l-round-pot-with-u-grooves/",
    },
    "PL-BB-1301153-BK": {
        "reason": "official_zephyr_page_confirms_30l_model_but_published_detail_media_is_25l_1301144",
        "source_url": "https://getplantlogic.com/portfolio-items/zephyr-v2/",
    },
    "PL-BB-1301143-BK": {
        "reason": "official_zephyr_page_confirms_40l_model_but_published_detail_media_is_25l_1301144",
        "source_url": "https://getplantlogic.com/portfolio-items/zephyr-v2/",
    },
}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "bb610-v5-runtime-audit/1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def expected_package_group(value, unit):
    if value is None:
        return None
    unit = str(unit or "").strip().lower()
    amount = Decimal(str(value))
    if unit == "kg":
        amount *= 1000
    elif unit == "g":
        pass
    elif unit == "l":
        amount *= 1000
    elif unit == "ml":
        pass
    else:
        return None
    if amount <= 50:
        return "small"
    if Decimal("100") <= amount <= Decimal("1000"):
        return "medium"
    if amount >= Decimal("5000"):
        return "large"
    return None



def expected_package_label(value, unit):
    if value is None:
        return None
    unit_map = {"kg": "кг", "g": "г", "l": "л", "ml": "мл", "pcs": "шт"}
    unit = str(unit or "").strip().lower()
    label_unit = unit_map.get(unit)
    if not label_unit:
        return None
    amount = Decimal(str(value))
    amount_text = str(int(amount)) if amount == amount.to_integral() else format(amount.normalize(), "f").replace(".", ",")
    return f"{amount_text} {label_unit}"



def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    data = fetch(url)
    products = data.get("products") or []

    product_ids = [p.get("product_id") for p in products]
    slugs = [p.get("slug") for p in products]
    all_skus = [s for p in products for s in (p.get("skus") or [])]
    sku_ids = [s.get("sku_id") for s in all_skus]

    def duplicates(values):
        return sorted(k for k, n in Counter(values).items() if k and n > 1)

    package_group_mismatches = []
    package_label_mismatches = []
    duplicate_package_variants = []
    suspicious_product_names = []
    internal_public_language = []
    current_without_exact = []
    documented_exact_blockers = []
    no_media = []
    candidate_exact_media = []
    multi_primary = []
    weak_sources = []
    missing_content = []
    commerce_anomalies = []
    per_brand_missing_exact = defaultdict(int)

    for product in products:
        pid = product.get("product_id")
        name = str(product.get("name") or "")
        pmedia = product.get("media") or []
        if re.search(r"plantlogic|контейнер|#\d{5,}", name, flags=re.IGNORECASE):
            suspicious_product_names.append({"product_id": pid, "name": name})

        package_seen = {}
        if not pmedia:
            no_media.append(pid)

        public_text = json.dumps({
            "name": product.get("name"),
            "short_description": product.get("short_description"),
            "description": product.get("description"),
            "application": product.get("application"),
            "composition": product.get("composition"),
            "benefits": product.get("benefits"),
            "how_it_works": product.get("how_it_works"),
            "characteristics": product.get("characteristics"),
        }, ensure_ascii=False).lower()
        internal_terms = (
            "legacy", "не публікувати", "потребує верифікації",
            "потрібна етикетка", "не вдалося", "вихідній матриці",
            "матриці bb610", "legacy match", "status review",
        )
        found_internal = [term for term in internal_terms if term in public_text]
        if found_internal:
            internal_public_language.append({
                "product_id": pid,
                "terms": found_internal,
            })

        required = {
            "name": product.get("name"),
            "brand": product.get("brand"),
            "category_id": product.get("category_id"),
            "short_description": product.get("short_description"),
            "description": product.get("description"),
            "application": product.get("application"),
            "characteristics": product.get("characteristics"),
            "sources": product.get("sources"),
        }
        absent = [
            key for key, value in required.items()
            if value is None or value == "" or (isinstance(value, list) and not value)
        ]
        if absent:
            missing_content.append({"product_id": pid, "fields": absent})

        for package_key, ids in package_seen.items():
            if len(ids) > 1:
                duplicate_package_variants.append({
                    "product_id": pid,
                    "package_value": package_key[0],
                    "package_unit": package_key[1],
                    "sku_ids": ids,
                })

        for source in product.get("sources") or []:
            st = str(source.get("source_type") or "").lower()
            status = str(source.get("status") or "").lower()
            if "unverified" in st or "conflict" in st or "unverified" in status or "conflict" in status:
                weak_sources.append({
                    "product_id": pid,
                    "source_type": source.get("source_type"),
                    "status": source.get("status"),
                    "source_url": source.get("source_url"),
                })

        for sku in product.get("skus") or []:
            expected = expected_package_group(sku.get("package_value"), sku.get("package_unit"))
            actual = sku.get("package_group")
            expected_label = expected_package_label(sku.get("package_value"), sku.get("package_unit"))
            actual_label = str(sku.get("package_label") or "").strip()
            if expected_label and actual_label != expected_label:
                package_label_mismatches.append({
                    "sku_id": sku.get("sku_id"),
                    "product_id": pid,
                    "actual": actual_label,
                    "expected": expected_label,
                })

            if bool(sku.get("enabled")) and sku.get("commerce_enabled") not in (0, False):
                package_key = (
                    str(sku.get("package_value")),
                    str(sku.get("package_unit") or "").lower(),
                )
                package_seen.setdefault(package_key, []).append(sku.get("sku_id"))
            if actual != expected:
                package_group_mismatches.append({
                    "sku_id": sku.get("sku_id"),
                    "product_id": pid,
                    "package_label": sku.get("package_label"),
                    "package_unit": sku.get("package_unit"),
                    "actual": actual,
                    "expected": expected,
                })

            identity_enabled = bool(sku.get("enabled"))
            commerce_enabled = sku.get("commerce_enabled")
            current = identity_enabled and commerce_enabled not in (0, False)
            exact = sku.get("media") or []
            if current and not exact:
                missing_row = {
                    "sku_id": sku.get("sku_id"),
                    "product_id": pid,
                    "brand": product.get("brand"),
                    "package_label": sku.get("package_label"),
                    "has_product_fallback": bool(pmedia),
                    "availability": sku.get("availability"),
                }
                blocker = EXACT_MEDIA_BLOCKERS.get(str(sku.get("sku_id") or ""))
                if blocker:
                    documented_exact_blockers.append({**missing_row, **blocker})
                else:
                    current_without_exact.append(missing_row)
                    per_brand_missing_exact[str(product.get("brand") or "?")] += 1

            primaries = [m for m in exact if m.get("is_primary")]
            if len(primaries) > 1:
                multi_primary.append({
                    "sku_id": sku.get("sku_id"),
                    "media_ids": [m.get("media_id") for m in primaries],
                })

            for media in exact:
                verification = str(media.get("verification_status") or "").lower()
                if verification in {"candidate", "representative", ""}:
                    candidate_exact_media.append({
                        "sku_id": sku.get("sku_id"),
                        "product_id": pid,
                        "package_label": sku.get("package_label"),
                        "media_id": media.get("media_id"),
                        "verification_status": media.get("verification_status"),
                        "source_kind": media.get("source_kind"),
                        "path": media.get("path"),
                    })

            if current and sku.get("availability") not in {"request_price", "legacy_disabled"}:
                if sku.get("price") is None and sku.get("sale_price") is None:
                    commerce_anomalies.append({
                        "sku_id": sku.get("sku_id"),
                        "product_id": pid,
                        "package_label": sku.get("package_label"),
                        "availability": sku.get("availability"),
                        "reason": "current_sellable_without_price",
                    })

    report = {
        "schema": "bb610-v5-runtime-catalog-audit-1",
        "source": url,
        "api_counts": data.get("counts") or {},
        "observed": {
            "public_products": len(products),
            "public_skus": len(all_skus),
        },
        "identity": {
            "duplicate_product_ids": duplicates(product_ids),
            "duplicate_slugs": duplicates(slugs),
            "duplicate_sku_ids": duplicates(sku_ids),
        },
        "packages": {
            "group_mismatch_count": len(package_group_mismatches),
            "group_mismatches": package_group_mismatches,
            "label_mismatch_count": len(package_label_mismatches),
            "label_mismatches": package_label_mismatches,
            "duplicate_current_package_variant_count": len(duplicate_package_variants),
            "duplicate_current_package_variants": duplicate_package_variants,
        },
        "media": {
            "products_without_product_media_count": len(no_media),
            "products_without_product_media": no_media,
            "current_skus_without_exact_count": len(current_without_exact),
            "current_skus_without_exact_by_brand": dict(sorted(per_brand_missing_exact.items())),
            "current_skus_without_exact": current_without_exact,
            "documented_exact_blocker_count": len(documented_exact_blockers),
            "documented_exact_blockers": documented_exact_blockers,
            "candidate_exact_media_count": len(candidate_exact_media),
            "candidate_exact_media": candidate_exact_media,
            "multi_primary_skus": multi_primary,
        },
        "content": {
            "suspicious_product_name_count": len(suspicious_product_names),
            "suspicious_product_names": suspicious_product_names,
            "internal_public_language_count": len(internal_public_language),
            "internal_public_language": internal_public_language,
            "missing_required_count": len(missing_content),
            "missing_required": missing_content,
            "weak_or_conflicting_sources_count": len(weak_sources),
            "weak_or_conflicting_sources": weak_sources,
        },
        "commerce": {
            "anomaly_count": len(commerce_anomalies),
            "anomalies": commerce_anomalies,
        },
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
