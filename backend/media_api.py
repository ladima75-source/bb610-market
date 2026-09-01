from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException,UploadFile,File,Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .services.media_library import *
router=APIRouter()
def auth(a):
 if not os.getenv('BB610_ADMIN_TOKEN') or a!='Bearer '+os.getenv('BB610_ADMIN_TOKEN'):raise HTTPException(401,'Unauthorized')
class MP(BaseModel):title:Optional[str]=None;alt_text:Optional[str]=None;tags:Optional[str]=None;category:Optional[str]=None;active:Optional[bool]=None;sort_order:Optional[int]=None
class BB(BaseModel):media_id:str;title:str='';subtitle:str='';cta_label:str='';target_url:str='';placement:str;sort_order:int=0;active:bool=True;start_at:Optional[str]=None;end_at:Optional[str]=None
class BP(BaseModel):media_id:Optional[str]=None;title:Optional[str]=None;subtitle:Optional[str]=None;cta_label:Optional[str]=None;target_url:Optional[str]=None;placement:Optional[str]=None;sort_order:Optional[int]=None;active:Optional[bool]=None;start_at:Optional[str]=None;end_at:Optional[str]=None
@router.get('/media/{name}')
def file_get(name:str):
 p=media_path(name)
 if not p:raise HTTPException(404,'Media not found')
 return FileResponse(p)
@router.get('/api/v1/banners')
def banners_public(placement:Optional[str]=None):return {'items':list_banners(False,placement)}
@router.get('/api/v1/admin/media')
def media_admin(authorization:Optional[str]=Header(None)):auth(authorization);return {'items':list_media()}
@router.post('/api/v1/admin/media',status_code=201)
async def media_add(file:UploadFile=File(...),title:str=Form(''),alt_text:str=Form(''),tags:str=Form(''),category:str=Form(''),authorization:Optional[str]=Header(None)):
 auth(authorization)
 try:return save_media(file.filename or 'media',file.content_type or '',await file.read(),title,alt_text,tags,category)
 except ValueError as e:raise HTTPException(422,str(e))
@router.patch('/api/v1/admin/media/{mid}')
def media_update(mid:str,body:MP,authorization:Optional[str]=Header(None)):auth(authorization);return patch_media(mid,body.model_dump(exclude_none=True))
@router.delete('/api/v1/admin/media/{mid}')
def media_del(mid:str,authorization:Optional[str]=Header(None)):
 auth(authorization)
 try:ok=delete_media(mid)
 except ValueError as e:raise HTTPException(409,str(e))
 if not ok:raise HTTPException(404,'Media not found')
 return {'ok':True}
@router.get('/api/v1/admin/banners')
def banners_admin(authorization:Optional[str]=Header(None)):auth(authorization);return {'items':list_banners(True)}
@router.post('/api/v1/admin/banners',status_code=201)
def banner_add(body:BB,authorization:Optional[str]=Header(None)):
 auth(authorization)
 try:return create_banner(body.model_dump())
 except ValueError as e:raise HTTPException(422,str(e))
@router.patch('/api/v1/admin/banners/{bid}')
def banner_update(bid:str,body:BP,authorization:Optional[str]=Header(None)):
 auth(authorization)
 try:return patch_banner(bid,body.model_dump(exclude_none=True))
 except ValueError as e:raise HTTPException(422,str(e))
@router.delete('/api/v1/admin/banners/{bid}')
def banner_del(bid:str,authorization:Optional[str]=Header(None)):auth(authorization);return {'ok':delete_banner(bid)}
