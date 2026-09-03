
from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .services.backup_center import center_data,backup_detail,create_backup,restore_backup,create_zip

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:
        raise HTTPException(401,'Unauthorized')

class CreateBody(BaseModel):
    label:str='Manual backup'

class RestoreBody(BaseModel):
    backup_id:str
    confirm_text:str
    publish_git:bool=False

@router.get('/api/v1/admin/backups')
def list_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return center_data()

@router.get('/api/v1/admin/backups/{backup_id}')
def detail_route(backup_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return backup_detail(backup_id)
    except Exception as e:raise HTTPException(404,str(e))

@router.post('/api/v1/admin/backups')
def create_route(body:CreateBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return create_backup(body.label)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/backups/restore')
def restore_route(body:RestoreBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return restore_backup(body.backup_id,body.confirm_text,body.publish_git)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/admin/backups/{backup_id}/download')
def download_route(backup_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:
        p=create_zip(backup_id)
        return FileResponse(path=p,filename=p.name,media_type='application/zip')
    except Exception as e:
        raise HTTPException(404,str(e))
