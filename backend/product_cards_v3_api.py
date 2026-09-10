from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .services import product_cards_v3 as svc
from .services.product_cards_v3_media import list_existing_media
from .services.product_cards_v3_runtime import storefront_runtime

router = APIRouter()


class CardBody(BaseModel):
    data: dict


def _admin(auth: Optional[str]) -> None:
    token = os.getenv('BB610_ADMIN_TOKEN', '')
    if not token:
        raise HTTPException(status_code=503, detail='Admin API is disabled until BB610_ADMIN_TOKEN is configured')
    if not auth or auth != f'Bearer {token}':
        raise HTTPException(status_code=401, detail='Unauthorized')


@router.get('/api/v1/storefront/product-card-v3-count')
def storefront_count():
    items = svc.list_cards()
    return {'count': len(items)}


@router.get('/api/v1/storefront/product-card-v3/{slug}')
def storefront_get(slug: str):
    data = storefront_runtime(slug)
    if not data:
        raise HTTPException(status_code=404, detail='Product card v3 not found')
    return data


@router.get('/api/v1/admin/product-card-v3')
def admin_list(authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    return {'items': svc.list_cards()}


@router.post('/api/v1/admin/product-card-v3', status_code=201)
def admin_create(body: CardBody, authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    try:
        return svc.create(body.data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get('/api/v1/admin/product-card-v3/media')
def admin_media(authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    return list_existing_media()


@router.get('/api/v1/admin/product-card-v3/{product_id}')
def admin_get(product_id: str, authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    card = svc.get(product_id)
    if not card:
        raise HTTPException(status_code=404, detail='Product card v3 not found')
    return card


@router.put('/api/v1/admin/product-card-v3/{product_id}')
def admin_put(product_id: str, body: CardBody, authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    try:
        return svc.put(product_id, body.data)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get('/api/v1/admin/product-card-v3/{product_id}/commerce')
def admin_commerce(product_id: str, authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    if not svc.get(product_id):
        raise HTTPException(status_code=404, detail='Product card v3 not found')
    return svc.commerce_view(product_id)
