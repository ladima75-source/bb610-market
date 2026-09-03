
from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.catalog_health import dashboard,ignore_duplicate,restore_duplicate,overrides_data

router=APIRouter()
def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class KeyBody(BaseModel):
    key:str

@router.get('/api/v1/admin/catalog-health')
def health_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return dashboard()

@router.get('/api/v1/admin/catalog-health/overrides')
def overrides_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return overrides_data()

@router.post('/api/v1/admin/catalog-health/ignore-duplicate')
def ignore_route(body:KeyBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return ignore_duplicate(body.key)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/catalog-health/restore-duplicate')
def restore_route(body:KeyBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return restore_duplicate(body.key)
    except Exception as e:raise HTTPException(422,str(e))
