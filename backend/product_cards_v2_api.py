from __future__ import annotations
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from .services import product_cards_v2 as svc

router=APIRouter()

class Payload(BaseModel):
    data: dict

def _admin(auth:Optional[str]):
    token=os.getenv("BB610_ADMIN_TOKEN","")
    if token:
        if not auth or auth != f"Bearer {token}":
            raise HTTPException(status_code=401,detail="Unauthorized")

@router.get("/api/v1/storefront/product-card-v2/{product_id}")
def public_get(product_id:str):
    x=svc.get(product_id)
    if not x or not x.get("enabled",True): raise HTTPException(status_code=404,detail="Not found")
    return x

@router.get("/api/v1/admin/product-card-v2")
def admin_list(authorization: Optional[str] = Header(default=None)):
    _admin(authorization); return {"items":svc.list_cards()}

@router.get("/api/v1/admin/product-card-v2/{product_id}")
def admin_get(product_id:str, authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    x=svc.get(product_id)
    if not x: return {"id":product_id,"version":"2.0","enabled":True,"variants":[]}
    return x

@router.put("/api/v1/admin/product-card-v2/{product_id}")
def admin_put(product_id:str, payload:Payload, authorization: Optional[str] = Header(default=None)):
    _admin(authorization)
    return svc.put(product_id,payload.data)
