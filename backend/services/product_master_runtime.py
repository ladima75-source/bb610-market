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


def _culture_facets(product: dict) -> list[str]:
    aliases = {
        "лохина": "лохина",
        "полуниця": "полуниця",
        "суниця": "полуниця",
        "малина": "малина",
        "овочі": "овочі",
        "сад": "сад",
        "хвойні": "хвойні",
        "газон": "газон",
    }
    out: list[str] = []
    for raw in product.get("cultures") or []:
        value = aliases.get(_norm(raw), _norm(raw))
        if value:
            out.append(value)
    return _uniq(out)


def _method_facets(product: dict) -> list[str]:
    raw_values: list[str] = []
    for key in ("applicationMethods", "application_methods"):
        value = product.get(key)
        if isinstance(value, list):
            raw_values.extend(str(x) for x in value)
        elif value:
            raw_values.extend(str(value).split(";"))
    if not raw_values and product.get("application"):
        raw_values.extend(str(product.get("application") or "").split(";"))

    out: list[str] = []
    for raw in raw_values:
        value = _norm(raw)
        is_foliar = (
            "позакорен" in value
            or "листков" in value
            or "foliar" in value
        )
        if "фертигац" in value or "крапель" in value or "drip" in value:
            out.append("fertigation")
        if is_foliar:
            out.append("foliar")
        elif "коренев" in value or "під корін" in value or "root" in value:
            out.append("root")
    return _uniq(out)


def _package_metric(sku: dict) -> float | None:
    vw = sku.get("volume_weight")
    if isinstance(vw, dict):
        try:
            value = float(str(vw.get("value")).replace(",", "."))
        except (TypeError, ValueError):
            value = None
        unit = _norm(vw.get("unit"))
        if value is not None:
            if unit in {"kg", "кг", "l", "л"}:
                return value * 1000
            if unit in {"g", "г", "гр", "ml", "мл"}:
                return value
            if unit in {"pcs", "pc", "шт"}:
                return None

    import re
    variant = _norm(sku.get("variant")).replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(кг|kg|г|гр|g|л|l|мл|ml)\b", variant, re.I)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).casefold()
    return value * 1000 if unit in {"кг", "kg", "л", "l"} else value


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

    for product in products:
        pid = str(product.get("id") or "")
        rows = by_product.get(pid, [])
        package_groups = _uniq([_package_group(row) for row in rows if _package_group(row)])

        in_stock = False
        for row in rows:
            sid = str(row.get("id") or row.get("sku") or "")
            state = commerce.get(sid) or {}
            availability = _norm(state.get("availability") or row.get("availability"))
            enabled = state.get("enabled")
            if enabled is False:
                continue
            if availability in {"in_stock", "dnipro"}:
                in_stock = True
                break

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
