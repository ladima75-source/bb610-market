from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from .services.product_master_v5_admin import (
    bind_media,
    get_product,
    list_products,
    save_image,
    unbind_media,
    update_product,
    update_sku,
)

router = APIRouter(prefix="/api/v1/admin/catalog-v5", tags=["admin-catalog-v5"])


def admin_auth(authorization: Optional[str]) -> None:
    expected = os.getenv("BB610_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(503, "Admin API is disabled until BB610_ADMIN_TOKEN is configured")
    if not authorization or authorization != "Bearer " + expected:
        raise HTTPException(401, "Unauthorized")


class ProductPatch(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    category_id: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    application: Optional[str] = None
    composition: Optional[str] = None
    benefits: Optional[list] = None
    how_it_works: Optional[str] = None
    characteristics: Optional[list] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    public_enabled: Optional[bool] = None
    status: Optional[str] = None


class SkuPatch(BaseModel):
    package_value: Optional[float] = None
    package_unit: Optional[str] = None
    package_label: Optional[str] = None
    package_group: Optional[str] = None
    attributes: Optional[dict] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


@router.get("/products")
def admin_v5_products(authorization: Optional[str] = Header(default=None)):
    admin_auth(authorization)
    return {"products": list_products()}


@router.get("/products/{product_id}")
def admin_v5_product(product_id: str, authorization: Optional[str] = Header(default=None)):
    admin_auth(authorization)
    item = get_product(product_id)
    if not item:
        raise HTTPException(404, "Product not found")
    return item


@router.patch("/products/{product_id}")
def admin_v5_product_update(
    product_id: str,
    body: ProductPatch,
    authorization: Optional[str] = Header(default=None),
):
    admin_auth(authorization)
    try:
        item = update_product(product_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not item:
        raise HTTPException(404, "Product not found")
    return item


@router.patch("/products/{product_id}/skus/{sku_id}")
def admin_v5_sku_update(
    product_id: str,
    sku_id: str,
    body: SkuPatch,
    authorization: Optional[str] = Header(default=None),
):
    admin_auth(authorization)
    try:
        item = update_sku(product_id, sku_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not item:
        raise HTTPException(404, "SKU not found")
    return item


@router.post("/media", status_code=201)
async def admin_v5_media_upload(
    product_id: str = Query(min_length=1),
    sku_id: Optional[str] = Query(default=None),
    primary: bool = Query(default=False),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    admin_auth(authorization)
    try:
        content = await file.read()
        media = save_image(file.filename or "image", content)
        item = bind_media(
            product_id,
            media["media_id"],
            sku_id=sku_id,
            primary=primary,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"media": media, "product": item}


@router.delete("/media/{media_id}")
def admin_v5_media_unbind(
    media_id: str,
    product_id: str = Query(min_length=1),
    sku_id: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
):
    admin_auth(authorization)
    try:
        item = unbind_media(product_id, media_id, sku_id=sku_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return item
