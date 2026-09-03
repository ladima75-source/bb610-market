
from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException,UploadFile,File,Form
from pydantic import BaseModel
from .services.media_manager import list_media,save_upload,update_meta,delete_media,assign_product,assign_category,reference_data
router=APIRouter()
def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')
class MetaBody(BaseModel): media_id:str; fields:dict[str,Any]
class DeleteBody(BaseModel): media_id:str
class AssignProduct(BaseModel): media_id:str; product_id:str
class AssignCategory(BaseModel): media_id:str; category_id:str
@router.get('/api/v1/admin/media-manager')
def list_route(authorization:Optional[str]=Header(None)): auth(authorization);return list_media()
@router.get('/api/v1/admin/media-manager/references')
def refs_route(authorization:Optional[str]=Header(None)): auth(authorization);return reference_data()
@router.post('/api/v1/admin/media-manager/upload')
async def upload_route(file:UploadFile=File(...),kind:str=Form('other'),title:str=Form(''),description:str=Form(''),authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_upload(file.filename or 'media',await file.read(),kind,title,description)
    except Exception as e:raise HTTPException(422,str(e))
@router.post('/api/v1/admin/media-manager/meta')
def meta_route(body:MetaBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return update_meta(body.media_id,body.fields)
    except Exception as e:raise HTTPException(422,str(e))
@router.post('/api/v1/admin/media-manager/delete')
def delete_route(body:DeleteBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return delete_media(body.media_id)
    except Exception as e:raise HTTPException(422,str(e))
@router.post('/api/v1/admin/media-manager/assign-product')
def ap_route(body:AssignProduct,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return assign_product(body.media_id,body.product_id)
    except Exception as e:raise HTTPException(422,str(e))
@router.post('/api/v1/admin/media-manager/assign-category')
def ac_route(body:AssignCategory,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return assign_category(body.media_id,body.category_id)
    except Exception as e:raise HTTPException(422,str(e))
