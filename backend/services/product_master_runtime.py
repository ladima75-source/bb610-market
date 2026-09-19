from __future__ import annotations

from copy import deepcopy
from typing import Any

from .catalog_cms import public_content
from .product_commerce import commerce_map


SOURCE_ID = "product-master-v4-runtime"
HIDDEN_PUBLIC_CATEGORIES = {"protection", "захист рослин", "средства защиты растений"}
HIDDEN_PUBLIC_PRODUCT_IDS = {
    "aktara-25-wg",
    "switch-625-wg",
    "switch-62-5-wg",
    "control-dmp",
}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _public_category(row: dict) -> str:
    return _norm(row.get("category_id") or row.get("category"))


def _hidden_public_product(row: dict) -> bool:
    pid = _norm(row.get("id"))
    slug = _norm(row.get("slug"))
    category_id = _norm(row.get("category_id"))
    category = _norm(row.get("category"))
    return (
        pid in HIDDEN_PUBLIC_PRODUCT_IDS
        or slug in HIDDEN_PUBLIC_PRODUCT_IDS
        or category_id in HIDDEN_PUBLIC_CATEGORIES
        or category in HIDDEN_PUBLIC_CATEGORIES
    )


def _uniq(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        raw = str(value or "").strip()
        if not raw:
            continue
        key = raw.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(raw)
    return out


CULTURE_FACETS = {"all", "лохина", "полуниця", "малина", "овочі", "сад", "хвойні", "газон"}


def _application_texts(product: dict) -> list[str]:
    app = product.get("application")
    out: list[str] = []
    if isinstance(app, str):
        out.extend(x.strip() for x in app.split(";") if x.strip())
    elif isinstance(app, dict):
        for key in ("intro", "note"):
            value = str(app.get(key) or "").strip()
            if value:
                out.append(value)
        for row in app.get("rows") or []:
            if not isinstance(row, dict):
                continue
            for key in ("crop", "method", "period"):
                value = str(row.get(key) or "").strip()
                if value:
                    out.append(value)
    elif isinstance(app, list):
        for row in app:
            if isinstance(row, str) and row.strip():
                out.append(row.strip())
            elif isinstance(row, dict):
                for key in ("crop", "method", "period"):
                    value = str(row.get(key) or "").strip()
                    if value:
                        out.append(value)
    return out


def _culture_values_from_text(raw: Any) -> list[str]:
    value = _norm(raw)
    if not value:
        return []
    if any(token in value for token in ("усі культури", "всі культури", "all crops")):
        return ["all"]

    out: list[str] = []
    if "лохин" in value or "blueberr" in value:
        out.append("лохина")
    if "полуниц" in value or "суниц" in value or "strawberr" in value:
        out.append("полуниця")
    if "малин" in value or "raspberr" in value:
        out.append("малина")
    if "овоч" in value or "vegetable" in value:
        out.append("овочі")
    if "плодов" in value or "сад" in value or "orchard" in value or "fruit crop" in value:
        out.append("сад")
    if "хвой" in value or "conifer" in value:
        out.append("хвойні")
    if "газон" in value or "lawn" in value or "turf" in value:
        out.append("газон")
    return out


def _culture_facets(product: dict) -> list[str]:
    raw_values: list[Any] = list(product.get("cultures") or [])
    if not raw_values:
        raw_values.extend(_application_texts(product))
    out: list[str] = []
    for raw in raw_values:
        out.extend(_culture_values_from_text(raw))
    return _uniq(out)


def _method_facets(product: dict) -> list[str]:
    raw_values: list[str] = []
    for key in ("applicationMethods", "application_methods"):
        value = product.get(key)
        if isinstance(value, list):
            raw_values.extend(str(x) for x in value)
        elif value:
            raw_values.extend(str(value).split(";"))
    if not raw_values:
        raw_values.extend(_application_texts(product))

    out: list[str] = []
    for raw in raw_values:
        value = _norm(raw)
        is_foliar = (
            "позакорен" in value
            or "листков" in value
            or "по лист" in value
            or "обприск" in value
            or "foliar" in value
        )
        if "фертигац" in value or "крапель" in value or "drip" in value:
            out.append("fertigation")
        if is_foliar:
            out.append("foliar")
        elif (
            "коренев" in value
            or "під корін" in value
            or "полив" in value
            or "root" in value
        ):
            out.append("root")
    return _uniq(out)


def _metric_from_variant(sku: dict) -> float | None:
    import re
    variant = _norm(sku.get("variant")).replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(кг|kg|г|гр|g|л|l|мл|ml)\b", variant, re.I)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).casefold()
    return value * 1000 if unit in {"кг", "kg", "л", "l"} else value


def _metric_from_volume_weight(sku: dict) -> float | None:
    vw = sku.get("volume_weight")
    if not isinstance(vw, dict):
        return None
    try:
        value = float(str(vw.get("value")).replace(",", "."))
    except (TypeError, ValueError):
        return None
    unit = _norm(vw.get("unit"))
    if unit in {"kg", "кг", "l", "л"}:
        return value * 1000
    if unit in {"g", "г", "гр", "ml", "мл"}:
        return value
    return None


def _package_metric(sku: dict) -> float | None:
    # The visible SKU variant is authoritative for catalog filtering.
    # volume_weight is a fallback because legacy rows can contain stale metadata.
    variant_metric = _metric_from_variant(sku)
    if variant_metric is not None:
        return variant_metric
    return _metric_from_volume_weight(sku)


def _package_group(sku: dict) -> str:
    value = _package_metric(sku)
    if value is None:
        return ""
    if value <= 50:
        return "small"
    if 100 <= value <= 1000:
        return "medium"
    if value >= 5000:
        return "large"
    return ""


def _attach_facets(products: list[dict], skus: list[dict], commerce: dict[str, dict]) -> None:
    by_product: dict[str, list[dict]] = {}
    for sku in skus:
        by_product.setdefault(str(sku.get("product_id") or ""), []).append(sku)

    for row in skus:
        sid = str(row.get("id") or row.get("sku") or "")
        state = commerce.get(sid) or {}
        availability = _norm(state.get("availability") or row.get("availability"))
        enabled = state.get("enabled")
        row_facets = row.get("facets") if isinstance(row.get("facets"), dict) else {}
        row["facets"] = {
            **row_facets,
            "package_group": _package_group(row),
            "in_stock": enabled is not False and availability in {"in_stock", "dnipro"},
        }

    for product in products:
        pid = str(product.get("id") or "")
        rows = by_product.get(pid, [])
        package_groups = _uniq([
            str((row.get("facets") or {}).get("package_group") or "")
            for row in rows
            if str((row.get("facets") or {}).get("package_group") or "")
        ])
        in_stock = any(bool((row.get("facets") or {}).get("in_stock")) for row in rows)

        product["facets"] = {
            "category": str(product.get("category_id") or product.get("category") or "").strip(),
            "brand": str(product.get("brand") or product.get("manufacturer") or "").strip(),
            "cultures": _culture_facets(product),
            "application_methods": _method_facets(product),
            "package_groups": package_groups,
            "in_stock": in_stock,
        }


def snapshot(commerce_override: dict[str, dict] | None = None) -> dict[str, Any]:
    """Canonical public product/SKU snapshot.

    Descriptive product data comes from catalog_cms.public_content(), whose
    Product Card v3 overlay is the curated descriptive source. SKU identity and
    presentation metadata come through the same public catalog projection.
    Live commercial state is attached from sku_commerce.

    Every public consumer that exports product data should start here rather
    than reopening catalog.master.json or rebuilding CMS/V3 overlays itself.
    """
    public = public_content()
    products = [
        deepcopy(row)
        for row in (public.get("products") or [])
        if isinstance(row, dict)
        and row.get("id")
        and not row.get("runtime_hidden")
        and not _hidden_public_product(row)
    ]
    product_ids = {str(row.get("id")) for row in products}

    skus = [
        deepcopy(row)
        for row in (public.get("skus") or [])
        if isinstance(row, dict)
        and (row.get("id") or row.get("sku"))
        and str(row.get("product_id") or "") in product_ids
    ]

    public_sku_ids = {
        str(row.get("id") or row.get("sku"))
        for row in skus
        if row.get("id") or row.get("sku")
    }
    commerce = commerce_override if commerce_override is not None else commerce_map()
    commerce = {
        str(key): deepcopy(value)
        for key, value in (commerce or {}).items()
        if isinstance(value, dict) and str(key) in public_sku_ids
    }

    _attach_facets(products, skus, commerce)

    return {
        "schema_version": "4.0",
        "source": SOURCE_ID,
        "products": products,
        "skus": skus,
        "commerce": commerce,
    }
