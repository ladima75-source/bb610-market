from fastapi import APIRouter,HTTPException
from .services.master_product_card_commerce import public_product_state

router=APIRouter()

@router.get("/api/v1/storefront/product-commerce/{slug}")
def public_product_commerce(slug:str):
    x=public_product_state(slug)
    if x is None: raise HTTPException(404,"Product not found")
    return x
