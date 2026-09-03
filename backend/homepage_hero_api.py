
from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.homepage_hero import admin_data,public_data,save_hero

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:
        raise HTTPException(401,'Unauthorized')

class HeroBody(BaseModel):
    hero:dict[str,Any]
    publish_git:bool=True

@router.get('/api/v1/admin/homepage-hero')
def admin_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return admin_data()

@router.post('/api/v1/admin/homepage-hero')
def save_route(body:HeroBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_hero(body.hero,body.publish_git)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/storefront/homepage-hero')
def public_route():
    return public_data()
