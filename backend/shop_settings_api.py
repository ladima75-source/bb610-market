
from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.shop_settings import admin_data,save_settings,public_settings

router=APIRouter()
def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class SaveBody(BaseModel):
    settings:dict[str,Any]
    publish:bool=True

@router.get('/api/v1/admin/shop-settings')
def admin_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return admin_data()

@router.post('/api/v1/admin/shop-settings')
def save_route(body:SaveBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_settings(body.settings,body.publish)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/storefront/settings')
def public_route():
    return public_settings()
