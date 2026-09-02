from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.product_maintenance import check,archive,hard_delete,history

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:
        raise HTTPException(401,'Unauthorized')

class ProductAction(BaseModel):
    product_id:str
    reason:str=''

@router.get('/api/v1/admin/products/maintenance/check')
def check_route(product_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return check(product_id)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/products/maintenance/archive')
def archive_route(body:ProductAction,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return archive(body.product_id,body.reason)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/products/maintenance/delete')
def delete_route(body:ProductAction,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return hard_delete(body.product_id,body.reason)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/admin/products/maintenance/history')
def history_route(authorization:Optional[str]=Header(None)):
    auth(authorization)
    return {'items':history()}
