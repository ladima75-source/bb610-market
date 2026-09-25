#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LAUNCH_PRODUCTS = (
    "kendal",
    "plantafol-npk-10-54-10",
    "plantafol-npk-5-15-45",
    "brexil-mix",
    "pekacid-npk-0-60-20",
    "master-npk-20-20-20",
    "viva",
    "master-npk-13-40-13",
    "plantafol-npk-20-20-20",
    "megafol",
    "radifarm",
    "kendal-te",
)

# These candidate assets were manually inspected against the visible
# product/formula/package label on 2026-09-25. A binary change invalidates
# that review and must fail the gate until the replacement is reviewed.
AUDITED_CANDIDATE_SHA256 = {
    "BB610-0BDAED34128BDA": "146dbd278150498ae157652418951a212af91466968261dace239e46bd44ef7f",
    "BB610-32DA4F652F73A1": "ad3434331aae65aec38db00fd4f14117b420f97824bf8e69e8c9208d0ee97c03",
    "BB610-VLG-MASTER134013-25KG": "5ff16767afd9c682e4fad77fb5f22afc75429df4aada31d077755734914b0cb2",
    "BB610-VLG-MASTER202020-20G": "8beecf484e8d837e427a89a5ed7e99b79c2191a4465ecc84ccff81df1d1e4c78",
    "BB610-VLG-MASTER202020-25KG": "7a3aedb92ce7711d92618dd9bf7c38c436b8ef22278a358837c24c54cbdc7c39",
    "BB610-VLG-MEGAFOL-100ML": "bcc1b7947da8b00fcbc9ba347aea67a704f501e938c9b002d98a938f1e1481bf",
    "BB610-VLG-MEGAFOL-25ML": "673f210d22563764539f29723eaa0873a4186c6f0be388c18e303af88eaf2d56",
    "BB610-VLG-PLANTAFOL105410-1KG": "d97ea4e1d943af52d3ebec57fed20491e81eb36f3b8aa0c3f1d73a8766d9785e",
    "BB610-VLG-PLANTAFOL105410-25G": "6abbd5afd6692dd5655ae389c8f70d051a7bbc42c727f74c88d3431c9c68a664",
    "BB610-VLG-PLANTAFOL105410-5KG": "af902cf2ed187ad0e0f19377ed45ac102cb22cee7c4aaad8e1ef7ce748742a28",
    "BB610-VLG-PLANTAFOL202020-25G": "5261c8125712ce7a15adabfe180a373b3ecb20d546eed163f739bb0ec6204316",
    "BB610-VLG-PLANTAFOL51545-1KG": "c3a397daa5a996ec8ad43bf0adad6ece51dc3897d850b915cf3bbe331bd7e77b",
    "BB610-VLG-PLANTAFOL51545-25G": "01a74f15ffaf1590ce6a3f748f75923044d650d8d120d274c5f090819fe6df50",
    "BB610-VLG-PLANTAFOL51545-5KG": "8a1f8b48540faf4ce1412d2ccbcb3b92e3b19f06c98539cdea8ed134563ba0fb",
}

# This SKU previously carried a 25 g image while the sellable SKU is 20 g.
# It must have a source-verified exact image before launch.
MUST_BE_VERIFIED = {"BB610-VLG-MASTER134013-20G"}


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_catalog(errors: list[str]) -> dict:
    stage = load("v5/staging/production-current.json")
    content = load("v5/content/verified-current.json")
    media = load("v5/media/verified-current.json")

    content_by_id = {x["product_id"]: x for x in content.get("products") or []}
    media_by_id = {x["media_id"]: x for x in media.get("media") or []}
    bindings_by_sku: dict[str, list[dict]] = {}
    for row in media.get("sku_bindings") or []:
        bindings_by_sku.setdefault(row["sku_id"], []).append(row)

    launch_skus = [
        row for row in stage.get("skus") or []
        if row.get("product_id") in LAUNCH_PRODUCTS and row.get("enabled") in (1, True)
    ]

    verified = 0
    audited = 0
    seen_products = set()

    for pid in LAUNCH_PRODUCTS:
        product = content_by_id.get(pid)
        if not product:
            fail(errors, f"{pid}: missing verified content product")
            continue
        seen_products.add(pid)
        if product.get("public_enabled") is not True:
            fail(errors, f"{pid}: product is not public")
        for field, minimum in (
            ("short_description", 70),
            ("description", 250),
            ("application", 80),
            ("how_it_works", 70),
        ):
            value = str(product.get(field) or "").strip()
            if len(value) < minimum:
                fail(errors, f"{pid}: weak {field} ({len(value)} < {minimum})")
        if len(product.get("characteristics") or []) < 3:
            fail(errors, f"{pid}: fewer than 3 characteristics")
        if len(product.get("benefits") or []) < 3:
            fail(errors, f"{pid}: fewer than 3 benefits")
        if not product.get("sources"):
            fail(errors, f"{pid}: no content provenance sources")

        product_skus = [x for x in launch_skus if x.get("product_id") == pid]
        if not product_skus:
            fail(errors, f"{pid}: no enabled sellable SKU")

        for sku in product_skus:
            sku_id = sku["sku_id"]
            if not (isinstance(sku.get("price"), (int, float)) and float(sku["price"]) > 0):
                fail(errors, f"{sku_id}: missing/invalid launch price")
            if sku.get("availability") != "in_stock":
                fail(errors, f"{sku_id}: availability={sku.get('availability')!r}, expected in_stock")

            rows = bindings_by_sku.get(sku_id) or []
            primary = next((x for x in rows if x.get("is_primary")), None)
            if not primary:
                fail(errors, f"{sku_id}: no primary exact SKU media")
                continue
            if primary.get("binding_kind") != "exact":
                fail(errors, f"{sku_id}: primary media is not exact")
                continue

            asset = media_by_id.get(primary.get("media_id"))
            if not asset:
                fail(errors, f"{sku_id}: primary media asset missing from graph")
                continue
            public_path = str(asset.get("path") or "")
            file_path = ROOT / public_path.lstrip("/")
            if not file_path.is_file():
                fail(errors, f"{sku_id}: primary media file missing: {public_path}")
                continue

            actual_hash = digest(file_path)
            graph_hash = str(asset.get("sha256") or "")
            if graph_hash and graph_hash != actual_hash:
                fail(errors, f"{sku_id}: media hash mismatch")

            status = asset.get("verification_status")
            if sku_id in MUST_BE_VERIFIED and status != "verified":
                fail(errors, f"{sku_id}: historically mismatched package image is not source-verified")
            elif status == "verified":
                if not (primary.get("source_url") or asset.get("source_url")):
                    fail(errors, f"{sku_id}: verified media has no provenance URL")
                verified += 1
            elif status == "candidate":
                expected = AUDITED_CANDIDATE_SHA256.get(sku_id)
                if not expected:
                    fail(errors, f"{sku_id}: unaudited candidate media")
                elif actual_hash != expected:
                    fail(errors, f"{sku_id}: candidate media changed since visual audit")
                else:
                    audited += 1
            else:
                fail(errors, f"{sku_id}: unsupported media verification status {status!r}")

    if len(seen_products) != len(LAUNCH_PRODUCTS):
        fail(errors, "not all launch products resolved")
    if len(launch_skus) != 47:
        fail(errors, f"launch SKU set changed: {len(launch_skus)} != 47; review required")

    return {
        "products": len(seen_products),
        "skus": len(launch_skus),
        "verified_media": verified,
        "audited_candidate_media": audited,
    }


def check_seo_and_tracking(errors: list[str]) -> dict:
    product_html = (ROOT / "product.html").read_text(encoding="utf-8")
    product_js = (ROOT / "js/product.js").read_text(encoding="utf-8")
    data_source = (ROOT / "js/data-source.js").read_text(encoding="utf-8")
    analytics = (ROOT / "js/analytics.js").read_text(encoding="utf-8")
    order_success = (ROOT / "js/order-success.js").read_text(encoding="utf-8")
    config = (ROOT / "config/analytics-config.js").read_text(encoding="utf-8")
    routes_js = (ROOT / "config/seo-routes.js").read_text(encoding="utf-8")

    required = {
        "GTM-MF8PZJCJ": config,
        "G-QWG1K17HC3": config,
        "AW-18468335580": config,
        "TnTkCK6GtoEdENzfseZE": config,
        'name="robots" content="noindex,follow"': product_html,
        "config/seo-routes.js": product_html,
        "canonicalProductUrl": product_js,
        "seoProductUrl": data_source,
        "setMeta('og:title'": product_js,
        "syncLiveProductSchema": product_js,
        "ecommerce.transaction_id": analytics,
        "params.value=value": analytics,
        "purchase_ready===true": order_success,
        "bb610_purchase_sent:${tx}": order_success,
    }
    for needle, haystack in required.items():
        if needle not in haystack:
            fail(errors, f"tracking/SEO contract missing: {needle}")

    route_re = re.compile(r'"([^"]+)"\s*:\s*"(/products/[^"]+/)"')
    routes = dict(route_re.findall(routes_js))
    landing_checks = {}
    for pid in LAUNCH_PRODUCTS:
        route = routes.get(pid)
        if not route:
            fail(errors, f"{pid}: SEO route missing")
            continue
        rel = route.strip("/")
        page_path = ROOT / rel / "index.html"
        if not page_path.is_file():
            fail(errors, f"{pid}: SEO landing file missing: {route}")
            continue
        page = page_path.read_text(encoding="utf-8")
        expected_url = "https://market.bb610.com.ua" + route
        checks = {
            "indexable": 'name="robots" content="index,follow,max-image-preview:large"' in page,
            "canonical": f'<link rel="canonical" href="{expected_url}">' in page,
            "product_schema": '"@type":"Product"' in page,
            "breadcrumb_schema": '"@type":"BreadcrumbList"' in page,
            "og_url": f'<meta property="og:url" content="{expected_url}">' in page,
            "data_source_current": "js/data-source.js?v=20260925-seo-routes-1" in page,
            "product_js_current": "js/product.js?v=20260925-seo-canonical-2" in page,
        }
        landing_checks[pid] = checks
        for name, ok in checks.items():
            if not ok:
                fail(errors, f"{pid}: SEO landing check failed: {name}")

    conversion_re = re.compile(
        r"gtag\s*\(\s*['\"]event['\"]\s*,\s*['\"]conversion['\"]"
    )
    senders = []
    for path in (ROOT / "js").glob("*.js"):
        text_value = path.read_text(encoding="utf-8", errors="ignore")
        count = len(conversion_re.findall(text_value))
        senders.extend([path.relative_to(ROOT).as_posix()] * count)
    if senders != ["js/analytics.js"]:
        fail(errors, f"Google Ads conversion senders changed: {senders}")

    if analytics.count("trackGoogleAdsEvent(event,data)") < 2:
        fail(errors, "Google Ads purchase tracking function is not wired into event push")

    return {
        "gtm": "GTM-MF8PZJCJ",
        "ga4": "G-QWG1K17HC3",
        "google_ads": "AW-18468335580",
        "conversion_senders": senders,
        "seo_landings": landing_checks,
    }

def main() -> None:
    errors: list[str] = []
    catalog = check_catalog(errors)
    tracking = check_seo_and_tracking(errors)
    report = {
        "status": "FAIL" if errors else "PASS",
        "catalog": catalog,
        "tracking": tracking,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
