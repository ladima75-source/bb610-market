from __future__ import annotations

from copy import deepcopy
from typing import Any

from .catalog_cms import public_content
from .product_commerce import commerce_map


SOURCE_ID = "product-master-v4-runtime"


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
        if isinstance(row, dict) and row.get("id") and not row.get("runtime_hidden")
    ]
    product_ids = {str(row.get("id")) for row in products}

    skus = [
        deepcopy(row)
        for row in (public.get("skus") or [])
        if isinstance(row, dict)
        and (row.get("id") or row.get("sku"))
        and str(row.get("product_id") or "") in product_ids
    ]

    commerce = commerce_override if commerce_override is not None else commerce_map()
    commerce = {
        str(key): deepcopy(value)
        for key, value in (commerce or {}).items()
        if isinstance(value, dict)
    }

    return {
        "schema_version": "4.0",
        "source": SOURCE_ID,
        "products": products,
        "skus": skus,
        "commerce": commerce,
    }
