from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.homepage_showcase import admin_data,save_config,public_data

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class SaveBody(BaseModel):
    config:dict[str,Any]
    publish:bool=True

@router.get('/api/v1/admin/homepage-showcase')
def admin_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return admin_data()

@router.post('/api/v1/admin/homepage-showcase')
def save_route(body:SaveBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_config(body.config,body.publish)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/storefront/homepage')
def public_route():
    return public_data()
