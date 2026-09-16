from __future__ import annotations

import json
from pathlib import Path

from . import product_cards_v3 as pcv3

ROOT = Path(__file__).resolve().parents[2]


def _load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _catalog_products():
    raw = _load_json(ROOT / "data" / "catalog.master.json", {})
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("products", "items", "catalog"):
            if isinstance(raw.get(key), list):
                return raw[key]
    return []


def _commerce_map():
    try:
        from .product_commerce import commerce_map
        m = commerce_map()
        if isinstance(m, dict):
            return m
    except Exception:
        pass
    return {}


def _sku_ids(product):
    ids = []
    for key in ("default_sku_id", "sku"):
        v = product.get(key)
        if isinstance(v, str) and v.strip():
            ids.append(v.strip())
    for key in ("launch_sku_ids", "sku_ids"):
        arr = product.get(key)
        if isinstance(arr, list):
            for v in arr:
                if isinstance(v, str) and v.strip():
                    ids.append(v.strip())
    seen = set()
    return [x for x in ids if not (x in seen or seen.add(x))]


def _value(c, *keys, default=None):
    for k in keys:
        if isinstance(c, dict) and c.get(k) is not None:
            return c.get(k)
    return default


def _commerce_fields(c):
    c = c if isinstance(c, dict) else {}
    return {
        "price": _value(c, "price", "base_price", "regular_price"),
        "sale_price": _value(c, "sale_price", "promo_price", "special_price"),
        "availability": _value(c, "availability", "stock_status", "status", default="unknown") or "unknown",
        "qty": _value(c, "qty", "quantity", "stock", "stock_qty"),
        "sale_enabled": bool(_value(c, "sale_enabled", "enabled", "active", default=False)),
        "gtin": _value(c, "gtin", "ean", "barcode", default=""),
        "mpn": _value(c, "mpn", "manufacturer_part_number", default=""),
    }


def _v3_rows():
    summaries = pcv3.list_cards()
    cmap_doc = pcv3.commerce_map()
    mappings = {
        str(x.get("product_id") or ""): x
        for x in (cmap_doc.get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }
    if not summaries or not mappings:
        return None

    commerce = _commerce_map()
    out = []
    linked_keys = set()
    active_sku_count = 0
    missing_bindings = 0

    for summary in summaries:
        pid = str(summary.get("product_id") or "")
        card = pcv3.get(pid)
        if not isinstance(card, dict) or card.get("enabled") is False:
            continue

        content = card.get("content") or {}
        title = str(content.get("title") or summary.get("title") or pid).strip()
        brand = str(content.get("brand") or summary.get("brand") or "").strip()
        mapping = mappings.get(pid) or {}
        links = {
            str(x.get("sku_id") or ""): str(x.get("existing_commerce_sku_key") or "").strip()
            for x in (mapping.get("skus") or [])
            if isinstance(x, dict) and x.get("sku_id")
        }

        for sku in (card.get("sku_media") or {}).get("skus") or []:
            if not isinstance(sku, dict) or sku.get("enabled") is False:
                continue
            active_sku_count += 1
            sku_id = str(sku.get("sku_id") or "").strip()
            commerce_key = links.get(sku_id, "")
            if not commerce_key:
                missing_bindings += 1
            else:
                linked_keys.add(commerce_key)

            c = commerce.get(commerce_key, {}) if commerce_key else {}
            display_sku = str(sku.get("sku_code") or commerce_key or sku_id).strip()
            pack = str(sku.get("package") or sku.get("label") or "").strip()
            fields = _commerce_fields(c)
            out.append({
                "product": title,
                "brand": brand,
                "sku": commerce_key or display_sku,
                "display_sku": display_sku,
                "sku_id": sku_id,
                "product_id": pid,
                "pack": pack,
                **fields,
                "commerce_found": bool(commerce_key and commerce_key in commerce),
                "mapped": bool(commerce_key),
                "source": "product_cards_v3",
                "sort_order": int(sku.get("sort_order") or 0),
            })

    out.sort(key=lambda x: (
        str(x["product"]).lower(),
        int(x.get("sort_order") or 0),
        str(x.get("pack") or "").lower(),
        str(x.get("display_sku") or "").lower(),
    ))
    return {
        "rows": out,
        "active_sku_count": active_sku_count,
        "missing_bindings": missing_bindings,
        "linked_keys": linked_keys,
        "commerce": commerce,
        "product_count": sum(1 for s in summaries if s.get("enabled") is not False),
        "mapping_count": len(mappings),
    }


def _legacy_rows():
    products = _catalog_products()
    commerce = _commerce_map()
    out = []
    matched = set()

    for p in products:
        if not isinstance(p, dict):
            continue
        title = str(p.get("name") or p.get("official_name") or p.get("title") or "").strip()
        brand = str(p.get("brand") or "").strip()
        ppack = p.get("pack") or p.get("size") or ""
        ids = _sku_ids(p)

        for sku in ids:
            c = commerce.get(sku, {}) if isinstance(commerce, dict) else {}
            if not isinstance(c, dict):
                c = {}
            matched.add(sku)
            fields = _commerce_fields(c)
            out.append({
                "product": title,
                "brand": brand,
                "sku": sku,
                "display_sku": sku,
                "pack": _value(c, "pack", "packing", "size", "variant", "label", default=ppack or ""),
                **fields,
                "commerce_found": sku in commerce,
                "mapped": True,
                "source": "legacy_catalog",
            })

    out.sort(key=lambda x: (str(x["product"]).lower(), str(x["pack"]).lower(), str(x["sku"]).lower()))
    return out


def rows():
    v3 = _v3_rows()
    if v3 is not None:
        return v3["rows"]
    return _legacy_rows()


def diagnostics():
    v3 = _v3_rows()
    if v3 is not None:
        commerce = v3["commerce"]
        linked = v3["linked_keys"]
        result_rows = v3["rows"]
        return {
            "source": "product_cards_v3",
            "v3_products": v3["product_count"],
            "v3_product_mappings": v3["mapping_count"],
            "v3_active_skus": v3["active_sku_count"],
            "v3_missing_bindings": v3["missing_bindings"],
            "commerce_records": len(commerce),
            "linked_commerce_records": len(linked & set(commerce)),
            "orphan_commerce_records_hidden": len(set(commerce) - linked),
            "rows": len(result_rows),
            "rows_with_commerce": sum(1 for x in result_rows if x["commerce_found"]),
        }

    products = _catalog_products()
    commerce = _commerce_map()
    referenced = []
    for p in products:
        if isinstance(p, dict):
            referenced.extend(_sku_ids(p))
    r = _legacy_rows()
    return {
        "source": "legacy_catalog_fallback",
        "catalog_products": len(products),
        "commerce_records": len(commerce),
        "referenced_sku_ids": len(set(referenced)),
        "rows": len(r),
        "rows_with_commerce": sum(1 for x in r if x["commerce_found"]),
    }
