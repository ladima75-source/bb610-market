from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.catalog_workbench import list_items,update_sku,update_product,bulk_skus

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class SkuUpdate(BaseModel):
    sku_id:str
    fields:dict[str,Any]
    publish:bool=True

class ProductUpdate(BaseModel):
    product_id:str
    fields:dict[str,Any]
    publish:bool=True

class BulkUpdate(BaseModel):
    sku_ids:list[str]
    fields:dict[str,Any]
    publish:bool=True

@router.get('/api/v1/admin/catalog-workbench')
def list_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return list_items()

@router.post('/api/v1/admin/catalog-workbench/sku')
def sku_route(body:SkuUpdate,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return update_sku(body.sku_id,body.fields,body.publish)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/catalog-workbench/product')
def product_route(body:ProductUpdate,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return update_product(body.product_id,body.fields,body.publish)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/catalog-workbench/bulk')
def bulk_route(body:BulkUpdate,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return bulk_skus(body.sku_ids,body.fields,body.publish)
    except Exception as e:raise HTTPException(422,str(e))
