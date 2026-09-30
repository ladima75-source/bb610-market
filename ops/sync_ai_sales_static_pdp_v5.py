#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://market.bb610.com.ua"
API = "https://api.market.bb610.com.ua/api/v1/catalog/v5"

VALID_AVAILABILITY = {"in_stock", "out_of_stock", "preorder", "backorder"}
SCHEMA_AVAILABILITY = {
    "in_stock": "https://schema.org/InStock",
    "out_of_stock": "https://schema.org/OutOfStock",
    "preorder": "https://schema.org/PreOrder",
    "backorder": "https://schema.org/BackOrder",
}
STOCK_LABELS = {
    "in_stock": "В наявності",
    "out_of_stock": "Немає в наявності",
    "preorder": "Передзамовлення",
    "backorder": "Під замовлення",
}


def fetch() -> dict:
    req = urllib.request.Request(API, headers={"User-Agent": "BB610-AI-Sales-PDP-Sync/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def plain(value) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))).strip()


def money(value) -> str:
    try:
        number = float(value)
    except Exception:
        return ""
    if number.is_integer():
        return f"{int(number):,}".replace(",", " ") + " грн"
    return f"{number:,.2f}".replace(",", " ").replace(".", ",") + " грн"


def effective_price(sku: dict):
    return sku.get("sale_price") if sku.get("sale_price") is not None else sku.get("price")


def sale_ready(sku: dict) -> bool:
    return (
        bool(sku.get("commerce_enabled"))
        and effective_price(sku) is not None
        and str(sku.get("availability") or "").strip() in VALID_AVAILABILITY
    )


def extract_json_global(text: str, name: str):
    m = re.search(rf"window\.{re.escape(name)}\s*=\s*([^;]+);", text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def replace_robots(text: str, indexable: bool) -> str:
    value = "index,follow,max-image-preview:large" if indexable else "noindex,follow"
    tag = f'<meta name="robots" content="{value}">'
    pat = re.compile(r'<meta\s+name=["\']robots["\'][^>]*>', re.I)
    if pat.search(text):
        return pat.sub(tag, text, count=1)
    return text.replace("</head>", tag + "</head>", 1)


def replace_div(text: str, class_name: str, inner_html: str) -> str:
    pat = re.compile(
        rf'(<div\s+class=["\']{re.escape(class_name)}["\']>).*?(</div>)',
        re.I | re.S,
    )
    return pat.sub(r"\1" + inner_html + r"\2", text, count=1)


def product_schema_patch(text: str, product: dict, page_url: str, sku: dict | None) -> str:
    pat = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.I | re.S,
    )
    found = False

    def repl(match):
        nonlocal found
        try:
            obj = json.loads(match.group(1))
        except Exception:
            return match.group(0)
        if found or obj.get("@type") != "Product":
            return match.group(0)
        found = True

        obj["@context"] = "https://schema.org"
        obj["@type"] = "Product"
        obj["name"] = plain(product.get("name")) + (
            (" " + plain(sku.get("package_label"))) if sku and plain(sku.get("package_label")) else ""
        )
        obj["url"] = page_url
        if product.get("brand"):
            obj["brand"] = {"@type": "Brand", "name": plain(product.get("brand"))}
        if product.get("manufacturer"):
            obj["manufacturer"] = {
                "@type": "Organization",
                "name": plain(product.get("manufacturer")),
            }

        if sku is not None:
            obj["sku"] = str(sku.get("sku_id") or "")
            if sku.get("manufacturer_sku"):
                obj["mpn"] = str(sku.get("manufacturer_sku"))
            if sale_ready(sku):
                price = effective_price(sku)
                availability = str(sku.get("availability") or "")
                obj["offers"] = {
                    "@type": "Offer",
                    "url": page_url,
                    "priceCurrency": str(sku.get("currency") or "UAH"),
                    "price": f"{float(price):g}",
                    "availability": SCHEMA_AVAILABILITY[availability],
                    "itemCondition": "https://schema.org/NewCondition",
                }
            else:
                obj.pop("offers", None)
        else:
            active = [row for row in product.get("skus") or [] if sale_ready(row)]
            prices = [float(effective_price(row)) for row in active]
            if prices:
                obj["offers"] = {
                    "@type": "AggregateOffer",
                    "priceCurrency": str(active[0].get("currency") or "UAH"),
                    "lowPrice": f"{min(prices):g}",
                    "highPrice": f"{max(prices):g}",
                    "offerCount": len(active),
                    "url": page_url,
                }
            else:
                obj.pop("offers", None)

        return '<script type="application/ld+json">' + json.dumps(
            obj, ensure_ascii=False, separators=(",", ":")
        ) + "</script>"

    updated = pat.sub(repl, text)
    if not found:
        raise RuntimeError(f"Product JSON-LD not found: {page_url}")
    return updated


def static_patch(text: str, product: dict, sku: dict | None) -> str:
    if sku is not None:
        label = plain(sku.get("package_label"))
        if label:
            text = replace_div(text, "selected-variant", html.escape(label))
        if sale_ready(sku):
            text = replace_div(text, "price", html.escape(money(effective_price(sku))))
            availability = str(sku.get("availability") or "")
            text = replace_div(text, "stock", html.escape(STOCK_LABELS.get(availability, "Наявність уточнюється")))
        else:
            text = replace_div(text, "price", "Ціна уточнюється")
            availability = str(sku.get("availability") or "")
            label = STOCK_LABELS.get(availability, "Наявність уточнюється")
            text = replace_div(text, "stock", html.escape(label))
        return text

    active = [row for row in product.get("skus") or [] if sale_ready(row)]
    if not active:
        text = replace_div(text, "price", "Ціна уточнюється")
        text = replace_div(text, "stock", "Наявність уточнюється")
        return text

    prices = [float(effective_price(row)) for row in active]
    if min(prices) == max(prices):
        price_label = money(min(prices))
    else:
        price_label = "від " + money(min(prices))
    text = replace_div(text, "price", html.escape(price_label))

    states = {str(row.get("availability") or "") for row in active}
    if "in_stock" in states:
        stock_label = "В наявності"
    elif states & {"preorder", "backorder"}:
        stock_label = "Під замовлення"
    else:
        stock_label = "Наявність уточнюється"
    text = replace_div(text, "stock", html.escape(stock_label))
    return text


def build_indexes(data: dict):
    products = {
        str(p.get("product_id")): p
        for p in data.get("products") or []
        if p.get("product_id")
    }
    aliases = {
        str(row.get("alias")): str(row.get("product_id"))
        for row in data.get("product_aliases") or []
        if row.get("alias") and row.get("product_id")
    }
    skus = {}
    for product in products.values():
        for sku in product.get("skus") or []:
            if sku.get("sku_id"):
                skus[str(sku["sku_id"])] = (product, sku)
    return products, aliases, skus


def patch_pages(data: dict, *, check: bool) -> dict:
    products, aliases, skus = build_indexes(data)
    scanned_sku_urls: set[str] = set()
    active_sku_urls: set[str] = set()
    changed = 0
    sku_pages = 0
    product_pages = 0
    errors: list[str] = []

    for path in sorted((ROOT / "products").glob("*/index.html")):
        original = path.read_text(encoding="utf-8")
        page_pid = extract_json_global(original, "BB610_PRODUCT_ID")
        page_sid = extract_json_global(original, "BB610_SKU_ID")
        if not page_pid:
            continue

        canonical_pid = str(page_pid)
        if canonical_pid not in products:
            canonical_pid = aliases.get(canonical_pid, canonical_pid)
        product = products.get(canonical_pid)
        if not product:
            continue

        page_url = SITE + "/products/" + path.parent.name + "/"
        updated = original

        if page_sid:
            sku_pages += 1
            scanned_sku_urls.add(page_url)
            pair = skus.get(str(page_sid))
            if not pair:
                errors.append(f"{path}: SKU {page_sid} missing from V5")
                continue
            live_product, sku = pair
            if live_product.get("product_id") != product.get("product_id"):
                product = live_product
            indexable = sale_ready(sku)
            if indexable:
                active_sku_urls.add(page_url)
            updated = replace_robots(updated, indexable)
            updated = static_patch(updated, product, sku)
            updated = product_schema_patch(updated, product, page_url, sku)
        else:
            product_pages += 1
            updated = replace_robots(updated, True)
            updated = static_patch(updated, product, None)
            updated = product_schema_patch(updated, product, page_url, None)

        if updated != original:
            changed += 1
            if not check:
                path.write_text(updated, encoding="utf-8")

        if check:
            robots = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)["\']', updated, re.I)
            robots_value = robots.group(1) if robots else ""
            if page_sid:
                _product, sku = skus.get(str(page_sid), (None, None))
                should_index = bool(sku and sale_ready(sku))
                if should_index and not robots_value.startswith("index,"):
                    errors.append(f"{path}: sale-ready SKU is not indexable")
                if not should_index and not robots_value.startswith("noindex,"):
                    errors.append(f"{path}: non-sale SKU is indexable")

    if not check:
        sitemap_path = ROOT / "sitemap.xml"
        sitemap = sitemap_path.read_text(encoding="utf-8")
        existing = re.findall(r"<loc>(.*?)</loc>", sitemap)
        kept = [url for url in existing if url not in scanned_sku_urls]
        for url in sorted(active_sku_urls):
            if url not in kept:
                kept.append(url)
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml += "".join(f"  <url><loc>{xml_escape(url)}</loc></url>\n" for url in kept)
        xml += "</urlset>\n"
        if xml != sitemap:
            sitemap_path.write_text(xml, encoding="utf-8")

    return {
        "status": "PASS" if not errors else "FAIL",
        "product_pages": product_pages,
        "sku_pages": sku_pages,
        "sale_ready_sku_pages": len(active_sku_urls),
        "changed_pages": changed,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = patch_pages(fetch(), check=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
