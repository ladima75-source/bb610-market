
from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.homepage_blocks import admin_data,public_data,save_config

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class BlocksBody(BaseModel):
    config:dict[str,Any]
    publish_git:bool=True

@router.get('/api/v1/admin/homepage-blocks')
def admin_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return admin_data()

@router.post('/api/v1/admin/homepage-blocks')
def save_route(body:BlocksBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_config(body.config,body.publish_git)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/storefront/homepage-blocks')
def public_route():
    return public_data()
