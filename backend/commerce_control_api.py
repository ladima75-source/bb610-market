
from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.commerce_control import (
 dashboard,list_entities,list_drafts,get_draft,create_draft,update_draft,publish_draft,discard_draft,
 stock_data,set_physical_stock,sync_stock_from_catalog,rebuild_reservations,
 returns_data,create_return,set_return_status,customers_data,add_customer_note,alerts_data
)

router=APIRouter()

def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class DraftCreate(BaseModel):
    entity_type:str
    entity_id:str
    note:str=''

class DraftUpdate(BaseModel):
    payload:dict[str,Any]
    note:Optional[str]=None

class PublishBody(BaseModel):
    force:bool=False
    publish_git:bool=True

class StockBody(BaseModel):
    sku_id:str
    qty:float
    note:str='Manual correction'

class ReturnBody(BaseModel):
    order_id:str
    items:list[dict[str,Any]]
    reason:str=''
    refund_amount:float=0
    restock:bool=False

class StatusBody(BaseModel):
    status:str

class NoteBody(BaseModel):
    customer_key:str
    note:str

@router.get('/api/v1/admin/commerce-control')
def dashboard_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return dashboard()

@router.get('/api/v1/admin/commerce-control/entities')
def entities_route(entity_type:str,q:str='',authorization:Optional[str]=Header(None)):
    auth(authorization);return {'items':list_entities(entity_type,q)}

@router.get('/api/v1/admin/commerce-control/drafts')
def drafts_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return {'drafts':list_drafts()}

@router.post('/api/v1/admin/commerce-control/drafts')
def create_draft_route(body:DraftCreate,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return create_draft(body.entity_type,body.entity_id,body.note)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/admin/commerce-control/drafts/{draft_id}')
def get_draft_route(draft_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    x=get_draft(draft_id)
    if not x:raise HTTPException(404,'Draft not found')
    return x

@router.put('/api/v1/admin/commerce-control/drafts/{draft_id}')
def update_draft_route(draft_id:str,body:DraftUpdate,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return update_draft(draft_id,body.payload,body.note)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/commerce-control/drafts/{draft_id}/publish')
def publish_draft_route(draft_id:str,body:PublishBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return publish_draft(draft_id,body.force,body.publish_git)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/commerce-control/drafts/{draft_id}/discard')
def discard_draft_route(draft_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization);return discard_draft(draft_id)

@router.get('/api/v1/admin/commerce-control/stock')
def stock_route(q:str='',authorization:Optional[str]=Header(None)):
    auth(authorization);return stock_data(q)

@router.post('/api/v1/admin/commerce-control/stock/set')
def stock_set_route(body:StockBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return set_physical_stock(body.sku_id,body.qty,body.note)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/commerce-control/stock/sync')
def stock_sync_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return sync_stock_from_catalog(False)

@router.post('/api/v1/admin/commerce-control/reservations/rebuild')
def reservations_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return rebuild_reservations()

@router.get('/api/v1/admin/commerce-control/returns')
def returns_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return {'returns':returns_data()}

@router.post('/api/v1/admin/commerce-control/returns')
def create_return_route(body:ReturnBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return create_return(body.order_id,body.items,body.reason,body.refund_amount,body.restock)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/commerce-control/returns/{return_id}/status')
def status_return_route(return_id:str,body:StatusBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return set_return_status(return_id,body.status)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/admin/commerce-control/customers')
def customers_route(q:str='',authorization:Optional[str]=Header(None)):
    auth(authorization);return {'customers':customers_data(q)}

@router.post('/api/v1/admin/commerce-control/customers/note')
def note_route(body:NoteBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return add_customer_note(body.customer_key,body.note)
    except Exception as e:raise HTTPException(422,str(e))

@router.get('/api/v1/admin/commerce-control/alerts')
def alerts_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return {'alerts':alerts_data()}
