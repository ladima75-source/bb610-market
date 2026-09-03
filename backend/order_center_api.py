
from typing import Optional
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.order_center import list_orders,order_detail,transition,cancel,add_note

router=APIRouter()
def auth(a):
    token=os.getenv('BB610_ADMIN_TOKEN')
    if not token or a!='Bearer '+token:raise HTTPException(401,'Unauthorized')

class TransitionBody(BaseModel):
    order_id:str
    direction:str
class CancelBody(BaseModel):
    order_id:str
    reason:str=''
class NoteBody(BaseModel):
    order_id:str
    note:str

@router.get('/api/v1/admin/order-center')
def list_route(authorization:Optional[str]=Header(None)):
    auth(authorization);return list_orders()

@router.get('/api/v1/admin/order-center/{order_id}')
def detail_route(order_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return order_detail(order_id)
    except Exception as e:raise HTTPException(404,str(e))

@router.post('/api/v1/admin/order-center/transition')
def transition_route(body:TransitionBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return transition(body.order_id,body.direction)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/order-center/cancel')
def cancel_route(body:CancelBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return cancel(body.order_id,body.reason)
    except Exception as e:raise HTTPException(422,str(e))

@router.post('/api/v1/admin/order-center/note')
def note_route(body:NoteBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return add_note(body.order_id,body.note)
    except Exception as e:raise HTTPException(422,str(e))
