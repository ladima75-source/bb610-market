from __future__ import annotations

"""Read-only production storefront audit for visible Product Card v3.

The audit intentionally performs no writes. It verifies that the main FastAPI
application exposes the Product Card v3 storefront routes and that every
currently visible in-scope V3 card projects through the HTTP runtime with:
- HTTP 200;
- runtime_version 3.0 / source product-card-v3;
- matching slug and title;
- all enabled V3 SKU present;
- every storefront SKU commerce-bound to live sku_commerce;
- primary media present for every storefront SKU.

Scope is identical to the structural repair audit:
- enabled Product Card v3;
- excludes Plantlogic;
- excludes the temporarily hidden "Захист рослин" category.
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.tools_repair_visible_pcv3_structural_20260918 import (
    card_exclusion,
    catalog_indexes,
    enabled_v3_skus,
    load_authoritative_catalog,
    mapping_index,
)


def http_json(url: str, timeout: float = 10.0) -> tuple[int, dict | list | None, str]:
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return int(resp.status), None, raw[:500]
            return int(resp.status), payload, ""
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), None, raw[:500]
    except URLError as exc:
        return 0, None, str(exc)


def scoped_cards() -> tuple[list[dict], list[dict]]:
    catalog = load_authoritative_catalog()
    by_id, _by_slug, _sku_by_product = catalog_indexes(catalog)
    mappings = mapping_index()

    cards: list[dict] = []
    excluded: list[dict] = []
    for summary in pcv3.list_cards():
        pid = str(summary.get("product_id") or "")
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            excluded.append({"product_id": pid, "reason": "card_file_missing"})
            continue
        mapping = mappings.get(pid)
        reason = card_exclusion(card, mapping, by_id)
        if reason:
            excluded.append({"product_id": pid, "slug": card.get("slug"), "reason": reason})
            continue
        if not card.get("enabled", False):
            excluded.append({"product_id": pid, "slug": card.get("slug"), "reason": "card_disabled"})
            continue
        cards.append(card)
    return cards, excluded


def validate_runtime(card: dict, runtime: dict) -> list[str]:
    problems: list[str] = []
    slug = str(card.get("slug") or "").strip()
    if str(runtime.get("runtime_version") or "") != "3.0":
        problems.append("runtime_version_not_3")
    if str(runtime.get("source") or "") != "product-card-v3":
        problems.append("runtime_source_not_v3")
    if str(runtime.get("slug") or "").strip() != slug:
        problems.append("slug_mismatch")

    expected_title = str((card.get("content") or {}).get("title") or "").strip()
    actual_title = str((runtime.get("content") or {}).get("title") or "").strip()
    if not actual_title or actual_title != expected_title:
        problems.append("title_mismatch")

    expected_skus = enabled_v3_skus(card)
    runtime_skus = runtime.get("skus") or []
    if not isinstance(runtime_skus, list):
        problems.append("runtime_skus_not_list")
        return problems
    if len(runtime_skus) != len(expected_skus):
        problems.append(f"sku_count:{len(runtime_skus)}!={len(expected_skus)}")

    expected_ids = {str(x.get("sku_id") or "") for x in expected_skus}
    actual_ids = {str(x.get("sku_id") or "") for x in runtime_skus if isinstance(x, dict)}
    if actual_ids != expected_ids:
        problems.append("sku_identity_mismatch")

    for row in runtime_skus:
        if not isinstance(row, dict):
            problems.append("runtime_sku_not_object")
            continue
        sid = str(row.get("sku_id") or "-")
        if not row.get("commerce_bound"):
            problems.append(f"{sid}:commerce_unbound")
        if not str(row.get("commerce_key") or "").strip():
            problems.append(f"{sid}:commerce_key_missing")
        if not isinstance(row.get("commerce"), dict):
            problems.append(f"{sid}:commerce_projection_missing")
        primary = row.get("primary_media")
        if not isinstance(primary, dict) or not str(primary.get("path") or "").strip():
            problems.append(f"{sid}:primary_media_missing")

    binding = runtime.get("commerce_binding") or {}
    if not isinstance(binding, dict):
        problems.append("commerce_binding_missing")
    else:
        total = len(runtime_skus)
        if int(binding.get("total") or 0) != total:
            problems.append("commerce_binding_total_mismatch")
        if int(binding.get("bound") or 0) != total:
            problems.append("commerce_binding_not_all_bound")
        if int(binding.get("unbound") or 0) != 0:
            problems.append("commerce_binding_has_unbound")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only visible Product Card v3 storefront/API audit")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    cards, excluded = scoped_cards()
    failures: list[dict] = []

    count_status, count_payload, count_error = http_json(
        base + "/api/v1/storefront/product-card-v3-count",
        timeout=args.timeout,
    )
    if count_status != 200 or not isinstance(count_payload, dict):
        failures.append({
            "slug": "_route_mount_",
            "reason": "v3_count_endpoint_failed",
            "status": count_status,
            "detail": count_error,
        })
    else:
        reported = count_payload.get("count")
        if not isinstance(reported, int) or reported < len(cards):
            failures.append({
                "slug": "_route_mount_",
                "reason": "v3_count_invalid",
                "reported": reported,
                "scope": len(cards),
            })

    checked = 0
    for card in cards:
        slug = str(card.get("slug") or "").strip()
        status, runtime, detail = http_json(
            base + "/api/v1/storefront/product-card-v3/" + quote(slug, safe=""),
            timeout=args.timeout,
        )
        if status != 200 or not isinstance(runtime, dict):
            failures.append({
                "slug": slug,
                "reason": "http_runtime_failed",
                "status": status,
                "detail": detail,
            })
            continue
        checked += 1
        problems = validate_runtime(card, runtime)
        if problems:
            failures.append({"slug": slug, "reason": "runtime_contract", "details": problems})

    print("BB610 VISIBLE PCV3 STOREFRONT AUDIT")
    print("BASE:", base)
    print("SCOPE:", len(cards))
    print("EXCLUDED:", len(excluded))
    print("HTTP RUNTIME OK:", checked)
    print("FAILURES:", len(failures))
    for row in failures:
        print("FAIL:", json.dumps(row, ensure_ascii=False, sort_keys=True))

    if failures:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
