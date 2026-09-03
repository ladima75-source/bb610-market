
from typing import Optional,Any
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
from .services.admin_product_cards import list_cards,get_card,save_card,create_card,duplicate_card,archive_card,delete_card
from .services.admin_commerce_editor import update_rows

router=APIRouter()

def auth(a):
    token=os.getenv("BB610_ADMIN_TOKEN")
    if not token or a!="Bearer "+token: raise HTTPException(401,"Unauthorized")

class CardBody(BaseModel):
    card:dict[str,Any]

class CommerceBody(BaseModel):
    changes:list[dict[str,Any]]

@router.get("/api/v1/admin/product-cards")
def cards(authorization:Optional[str]=Header(None)):
    auth(authorization); return {"items":list_cards()}

@router.get("/api/v1/admin/product-cards/{card_id}")
def card(card_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization); x=get_card(card_id)
    if not x: raise HTTPException(404,"Товар не знайдено")
    return x

@router.post("/api/v1/admin/product-cards")
def create(body:CardBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return create_card(body.card)
    except Exception as e: raise HTTPException(422,str(e))

@router.put("/api/v1/admin/product-cards/{card_id}")
def save(card_id:str,body:CardBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return save_card(card_id,body.card)
    except KeyError as e: raise HTTPException(404,str(e))
    except Exception as e: raise HTTPException(422,str(e))

@router.post("/api/v1/admin/product-cards/{card_id}/duplicate")
def duplicate(card_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return duplicate_card(card_id)
    except Exception as e: raise HTTPException(422,str(e))

@router.post("/api/v1/admin/product-cards/{card_id}/archive")
def archive(card_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return archive_card(card_id,True)
    except Exception as e: raise HTTPException(422,str(e))

@router.delete("/api/v1/admin/product-cards/{card_id}")
def delete(card_id:str,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return delete_card(card_id)
    except Exception as e: raise HTTPException(422,str(e))

@router.post("/api/v1/admin/commerce-editor")
def commerce(body:CommerceBody,authorization:Optional[str]=Header(None)):
    auth(authorization)
    try:return {"ok":True,"results":update_rows(body.changes)}
    except Exception as e: raise HTTPException(422,str(e))
