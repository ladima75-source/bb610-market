from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.catalog_order import get_order,update_one,bulk_update

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class OneBody(BaseModel):
    product_id:str
    fields:dict[str,Any]
    publish:bool=True

class BulkBody(BaseModel):
    items:list[dict[str,Any]]
    publish:bool=True

@router.get('/api/v1/admin/catalog-order')
def list_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return get_order()

@router.post('/api/v1/admin/catalog-order/product')
def one_route(body:OneBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return update_one(body.product_id,body.fields,body.publish)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/catalog-order/bulk')
def bulk_route(body:BulkBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return bulk_update(body.items,body.publish)
    except Exception as e:raise HTTPException(422,str(e))
