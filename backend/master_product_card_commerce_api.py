from pathlib import Path
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from .services import product_commerce

router = APIRouter()

ROOT = Path(__file__).resolve().parents[1]
CARDS_PATH = ROOT / "data" / "product_cards.master.json"


def _load_cards() -> Dict[str, Any]:
    if not CARDS_PATH.exists():
        return {}
    try:
        data = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("Unable to read product_cards.master.json: %s" % exc)
    products = data.get("products")
    return products if isinstance(products, dict) else {}


def _effective_price(row: Dict[str, Any]) -> Optional[float]:
    sale = row.get("sale_price")
    if sale not in (None, ""):
        try:
            return float(sale)
        except Exception:
            pass
    price = row.get("price")
    if price not in (None, ""):
        try:
            return float(price)
        except Exception:
            pass
    return None


def _variant_payload(card_variant: Dict[str, Any], commerce_row: Dict[str, Any]) -> Dict[str, Any]:
    sku = str(card_variant.get("sku") or "").strip()
    price = commerce_row.get("price")
    sale_price = commerce_row.get("sale_price")
    availability = commerce_row.get("availability", "unknown")
    stock_qty = commerce_row.get("stock_qty")
    enabled = bool(commerce_row.get("enabled"))
    return {
        "sku": sku,
        "label": card_variant.get("label") or sku,
        "image": card_variant.get("image") or "",
        "price": price,
        "sale_price": sale_price,
        "effective_price": _effective_price(commerce_row),
        "availability": availability,
        "stock_qty": stock_qty,
        "enabled": enabled,
        "updated_at": commerce_row.get("updated_at"),
    }


@router.get("/api/v1/storefront/product-commerce/{slug}")
def storefront_product_commerce(slug: str) -> Dict[str, Any]:
    """
    Public commerce projection for Product Card v2.

    Source of truth:
      - SKU/label/image/order: data/product_cards.master.json
      - price/sale/availability/stock/enabled: product_commerce.commerce_map()

    Legacy catalog price/availability/offer_status are intentionally ignored.
    """
    cards = _load_cards()
    card = cards.get(slug)
    if not isinstance(card, dict):
        raise HTTPException(status_code=404, detail="Product Card v2 not found")

    raw_variants = card.get("variants")
    if not isinstance(raw_variants, list):
        raw_variants = []

    cm = product_commerce.commerce_map()
    variants: List[Dict[str, Any]] = []
    missing: List[str] = []

    for item in raw_variants:
        if not isinstance(item, dict):
            continue
        sku = str(item.get("sku") or "").strip()
        if not sku:
            continue
        row = cm.get(sku)
        if not isinstance(row, dict):
            missing.append(sku)
            row = {
                "sku": sku,
                "price": None,
                "sale_price": None,
                "availability": "unknown",
                "stock_qty": None,
                "enabled": False,
            }
        variants.append(_variant_payload(item, row))

    return {
        "id": slug,
        "product_id": slug,
        "default_sku": variants[0]["sku"] if variants else None,
        "variants": variants,
        "missing_commerce_skus": missing,
        "source": "product_card_v2+commerce_map",
    }
