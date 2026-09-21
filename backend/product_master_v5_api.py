from fastapi import APIRouter, HTTPException

from .services.product_master_v5 import product, resolve_sku_id, snapshot

router = APIRouter(prefix="/api/v1/catalog/v5", tags=["catalog-v5"])


@router.get("")
def catalog_v5():
    return snapshot()


@router.get("/products/{product_id}")
def catalog_v5_product(product_id: str):
    item = product(product_id)
    if not item:
        raise HTTPException(404, "Product not found")
    return item


@router.get("/resolve-sku/{sku_id}")
def catalog_v5_resolve_sku(sku_id: str):
    canonical = resolve_sku_id(sku_id)
    if not canonical:
        raise HTTPException(404, "SKU not found")
    return {"requested": sku_id, "canonical_sku_id": canonical}
