#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import struct
import sys
import urllib.error
import urllib.request

SITE = os.getenv("BB610_SITE_BASE", "https://market.bb610.com.ua").rstrip("/")
API = os.getenv("BB610_API_BASE", "https://api.market.bb610.com.ua").rstrip("/")
MIN_IMAGE_PX = int(os.getenv("BB610_ADS_MIN_IMAGE_PX", "500"))

PRODUCT_IDS = [
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
]

failures: list[str] = []
warnings: list[str] = []


def get(url: str, *, timeout: int = 20) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BB610-Ads-Prelaunch-Audit/1.0",
            "Accept": "*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            return body, ctype
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc


def get_text(url: str) -> str:
    body, _ = get(url)
    return body.decode("utf-8", "replace")


def get_json(url: str) -> dict:
    return json.loads(get_text(url))


def image_size(data: bytes) -> tuple[int, int] | None:
    # PNG
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])

    # JPEG
    if len(data) >= 4 and data[:2] == b"\xff\xd8":
        i = 2
        sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while i + 9 <= len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            while i < len(data) and data[i] == 0xFF:
                i += 1
            if i >= len(data):
                break
            marker = data[i]
            i += 1
            if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue
            if i + 2 > len(data):
                break
            seglen = int.from_bytes(data[i:i+2], "big")
            if seglen < 2 or i + seglen > len(data):
                break
            if marker in sof and i + 7 < len(data):
                h = int.from_bytes(data[i+3:i+5], "big")
                w = int.from_bytes(data[i+5:i+7], "big")
                return w, h
            i += seglen

    # WEBP
    if len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8X" and len(data) >= 30:
            w = 1 + int.from_bytes(data[24:27], "little")
            h = 1 + int.from_bytes(data[27:30], "little")
            return w, h
        if kind == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
            b0, b1, b2, b3 = data[21:25]
            w = 1 + (((b1 & 0x3F) << 8) | b0)
            h = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
            return w, h
        if kind == b"VP8 ":
            pos = data.find(b"\x9d\x01\x2a", 20)
            if pos >= 0 and pos + 7 <= len(data):
                w = int.from_bytes(data[pos+3:pos+5], "little") & 0x3FFF
                h = int.from_bytes(data[pos+5:pos+7], "little") & 0x3FFF
                return w, h
    return None


def truthy(value) -> bool:
    return value is True or value == 1 or str(value).lower() in {"1", "true", "yes"}


def active_sku(sku: dict) -> bool:
    return (
        truthy(sku.get("enabled"))
        and truthy(sku.get("commerce_enabled"))
        and str(sku.get("availability") or "") not in {"", "unknown", "out_of_stock"}
    )


print("BB610 Ads pre-launch audit")
print(f"site={SITE} api={API} min_image={MIN_IMAGE_PX}px")

# Shared landing-page and analytics checks.
html = get_text(f"{SITE}/product.html?id=kendal")
robots = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', html, re.I)
if not robots or "noindex" in robots.group(1).lower() or "index" not in robots.group(1).lower():
    failures.append("product.html robots meta is not indexable")
if "analytics-config.js" not in html or "js/analytics.js" not in html:
    failures.append("product.html is missing analytics scripts")
if "js/product.js" not in html:
    failures.append("product.html is missing product.js")

product_js = get_text(f"{SITE}/js/product.js")
for needle in ("canonicalProductUrl", "syncSeoMeta", "application/ld+json"):
    if needle not in product_js:
        failures.append(f"product.js missing SEO marker: {needle}")

analytics_cfg = get_text(f"{SITE}/config/analytics-config.js")
for needle in ("GTM-MF8PZJCJ", "G-QWG1K17HC3", "AW-18468335580"):
    if needle not in analytics_cfg:
        failures.append(f"analytics config missing {needle}")

analytics_js = get_text(f"{SITE}/js/analytics.js")
for needle in ("event!=='purchase'", "transaction_id", "params.value=value"):
    if needle not in analytics_js:
        failures.append(f"Google Ads purchase implementation missing marker: {needle}")

for product_id in PRODUCT_IDS:
    url = f"{API}/api/v1/catalog/v5/products/{product_id}"
    try:
        p = get_json(url)
    except Exception as exc:
        failures.append(f"{product_id}: V5 API unavailable ({exc})")
        continue

    def txt(key: str) -> str:
        return str(p.get(key) or "").strip()

    checks = [
        ("short_description", len(txt("short_description")), 80),
        ("description", len(txt("description")), 300),
        ("application", len(txt("application")), 150),
        ("how_it_works", len(txt("how_it_works")), 100),
    ]
    for label, actual, minimum in checks:
        if actual < minimum:
            failures.append(f"{product_id}: {label} too short ({actual} < {minimum})")

    if len(p.get("characteristics") or []) < 3:
        failures.append(f"{product_id}: fewer than 3 characteristics")
    if len(p.get("sources") or []) < 1:
        failures.append(f"{product_id}: no verified content source")
    if len(p.get("media") or []) < 2:
        failures.append(f"{product_id}: fewer than 2 product-level images")

    sellable = [sku for sku in (p.get("skus") or []) if active_sku(sku)]
    if not sellable:
        failures.append(f"{product_id}: no active sellable SKU")
        continue

    for sku in sellable:
        sku_id = str(sku.get("sku_id") or "")
        label = str(sku.get("package_label") or sku_id)
        if sku.get("price") in (None, "") and str(sku.get("availability")) != "request_price":
            failures.append(f"{product_id}/{label}: active SKU has no price")

        exact = [
            m for m in (sku.get("media") or [])
            if str(m.get("binding_kind") or "") == "exact"
            and str(m.get("verification_status") or "") == "verified"
            and str(m.get("kind") or "image") == "image"
        ]
        if not exact:
            failures.append(f"{product_id}/{label}: no exact verified SKU image")
            continue

        primary = next((m for m in exact if truthy(m.get("is_primary"))), exact[0])
        path = str(primary.get("path") or "")
        if not path:
            failures.append(f"{product_id}/{label}: primary exact image has no path")
            continue
        try:
            data, ctype = get(SITE + path)
        except Exception as exc:
            failures.append(f"{product_id}/{label}: image unavailable ({exc})")
            continue
        size = image_size(data)
        if not size:
            failures.append(f"{product_id}/{label}: cannot read image dimensions ({path})")
            continue
        w, h = size
        if min(w, h) < MIN_IMAGE_PX:
            failures.append(
                f"{product_id}/{label}: image too small for BB610 launch standard "
                f"({w}x{h}, need >= {MIN_IMAGE_PX}px)"
            )
        if "image/" not in ctype.lower():
            warnings.append(f"{product_id}/{label}: unusual image content-type {ctype!r}")

print(f"checked_products={len(PRODUCT_IDS)}")
if warnings:
    print("\nWARNINGS")
    for item in warnings:
        print(" -", item)

if failures:
    print("\nFAIL")
    for item in failures:
        print(" -", item)
    sys.exit(1)

print("\nPASS: BB610 Search landing pages meet the pre-launch gate.")
