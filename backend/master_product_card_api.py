from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.master_product_card import schema,save_schema

router=APIRouter()
def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token: raise HTTPException(401,'Unauthorized')

class Body(BaseModel):
    data:dict[str,Any]

@router.get('/api/v1/storefront/product-card/{slug}')
def public_card(slug:str):
    s=schema(slug)
    if not s or not s.get('enabled'): raise HTTPException(404,'Master product card not enabled')
    return s

@router.get('/api/v1/admin/product-card-v1/{slug}')
def admin_get(slug:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    s=schema(slug)
    if not s: raise HTTPException(404,'Товар не знайдено')
    return s

@router.put('/api/v1/admin/product-card-v1/{slug}')
def admin_save(slug:str,body:Body,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_schema(slug,body.data)
    except KeyError as e: raise HTTPException(404,str(e))
    except Exception as e: raise HTTPException(422,str(e))
