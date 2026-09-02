from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.category_manager import get_data,save_categories,delete_category,move_products

router=APIRouter()
def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class SaveBody(BaseModel):
    categories:list[dict[str,Any]]
    publish:bool=True
class DeleteBody(BaseModel):
    category_id:str
    publish:bool=True
class MoveBody(BaseModel):
    product_ids:list[str]
    category_name:str
    publish:bool=True

@router.get('/api/v1/admin/categories-manager')
def get_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return get_data()

@router.post('/api/v1/admin/categories-manager')
def save_route(body:SaveBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_categories(body.categories,body.publish)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/categories-manager/delete')
def delete_route(body:DeleteBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return delete_category(body.category_id,body.publish)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/categories-manager/move-products')
def move_route(body:MoveBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return move_products(body.product_ids,body.category_name,body.publish)
    except Exception as e:raise HTTPException(422,str(e))
