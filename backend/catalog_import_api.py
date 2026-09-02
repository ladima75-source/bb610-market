from typing import Optional
import os
from fastapi import APIRouter,UploadFile,File,Header,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from .services.catalog_import import preview,apply,rollback,history,export_csv,export_xlsx,template_csv
router=APIRouter()
def auth(a):
    if not os.getenv('BB610_ADMIN_TOKEN') or a!='Bearer '+os.getenv('BB610_ADMIN_TOKEN'):raise HTTPException(401,'Unauthorized')
class ApplyBody(BaseModel):token:str;mode:str='content';rebuild:bool=True
class RollbackBody(BaseModel):backup_id:Optional[str]=None
@router.get('/api/v1/admin/catalog-import/template.csv')
def template(authorization:Optional[str]=Header(None)):auth(authorization);return Response(template_csv(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=bb610-catalog-template.csv'})
@router.get('/api/v1/admin/catalog-import/export.csv')
def csvx(authorization:Optional[str]=Header(None)):auth(authorization);return Response(export_csv(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=bb610-catalog-export.csv'})
@router.get('/api/v1/admin/catalog-import/export.xlsx')
def xlsx(authorization:Optional[str]=Header(None)):auth(authorization);return Response(export_xlsx(),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename=bb610-catalog-export.xlsx'})
@router.post('/api/v1/admin/catalog-import/preview')
async def prev(file:UploadFile=File(...),authorization:Optional[str]=Header(None)):
    auth(authorization);raw=await file.read()
    if len(raw)>80*1024*1024:raise HTTPException(413,'max 80 MB')
    try:return preview(file.filename or 'catalog.csv',raw)
    except Exception as e:raise HTTPException(422,str(e))
@router.post('/api/v1/admin/catalog-import/apply')
def app(body:ApplyBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    if body.mode not in ('content','commerce','all'):raise HTTPException(422,'mode')
    try:return apply(body.token,body.mode,body.rebuild)
    except Exception as e:raise HTTPException(422,str(e))
@router.post('/api/v1/admin/catalog-import/rollback')
def rb(body:RollbackBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return rollback(body.backup_id)
    except Exception as e:raise HTTPException(422,str(e))
@router.get('/api/v1/admin/catalog-import/history')
def hist(authorization:Optional[str]=Header(None)):auth(authorization);return {'items':history()}
