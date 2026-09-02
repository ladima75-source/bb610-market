from __future__ import annotations
import os
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field
from .services.delivery.base import DeliveryNotConfigured, DeliveryUpstreamError
from .services.integrations import nova_poshta_status, save_nova_poshta_settings, test_nova_poshta, nova_poshta_sender_options, nova_poshta_sender_cities
from .services.payment_settings import payment_settings_status, save_payment_settings

router=APIRouter(prefix='/api/v1/admin/integrations',tags=['admin-integrations'])
class PaymentSettingsPatch(BaseModel):
    cod_enabled:Optional[bool]=None
    bank_transfer_enabled:Optional[bool]=None
    bank_recipient:Optional[str]=Field(default=None,max_length=200)
    bank_iban:Optional[str]=Field(default=None,max_length=64)
    bank_purpose:Optional[str]=Field(default=None,max_length=200)

class NovaPoshtaSettingsPatch(BaseModel):
    api_key:Optional[str]=Field(default=None,min_length=8,max_length=512)
    api_url:Optional[str]=Field(default=None,min_length=8,max_length=500)
    sender_ref:Optional[str]=Field(default=None,max_length=200)
    sender_contact_ref:Optional[str]=Field(default=None,max_length=200)
    sender_city_ref:Optional[str]=Field(default=None,max_length=200)
    sender_address_ref:Optional[str]=Field(default=None,max_length=200)
    shipment_weight:Optional[float]=Field(default=None,gt=0,le=1000)
    shipment_description:Optional[str]=Field(default=None,max_length=120)
    payer_type:Optional[str]=Field(default=None,max_length=20)
    payment_method:Optional[str]=Field(default=None,max_length=20)
def _admin_auth(authorization:Optional[str]):
    expected=os.getenv('BB610_ADMIN_TOKEN')
    if not expected:raise HTTPException(503,'Admin API is disabled until BB610_ADMIN_TOKEN is configured')
    if not authorization or authorization!='Bearer '+expected:raise HTTPException(401,'Unauthorized')
@router.get('')
def list_integrations(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return {'integrations':[nova_poshta_status(),payment_settings_status()]}
@router.get('/payments')
def get_payments(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return payment_settings_status()
@router.patch('/payments')
def patch_payments(body:PaymentSettingsPatch,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return save_payment_settings(**body.model_dump(exclude_unset=True))
    except ValueError as e:raise HTTPException(422,str(e))
    except RuntimeError as e:raise HTTPException(500,str(e))
@router.get('/nova-poshta')
def get_np(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return nova_poshta_status()
@router.patch('/nova-poshta')
def patch_np(body:NovaPoshtaSettingsPatch,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return save_nova_poshta_settings(**body.model_dump(exclude_unset=True))
    except ValueError as e:raise HTTPException(422,str(e))
    except RuntimeError as e:raise HTTPException(500,str(e))
@router.post('/nova-poshta/test')
def test_np(authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return test_nova_poshta()
    except DeliveryNotConfigured as e:raise HTTPException(503,str(e))
    except DeliveryUpstreamError as e:raise HTTPException(502,str(e))
@router.get('/nova-poshta/senders')
def np_senders(authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return nova_poshta_sender_options()
    except (DeliveryNotConfigured,DeliveryUpstreamError) as e:raise HTTPException(502,str(e))
@router.get('/nova-poshta/sender-options')
def np_sender_options(sender_ref:str=Query(min_length=2,max_length=200),city_ref:Optional[str]=Query(default=None,max_length=200),authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return nova_poshta_sender_options(sender_ref,city_ref)
    except (DeliveryNotConfigured,DeliveryUpstreamError) as e:raise HTTPException(502,str(e))

@router.get('/nova-poshta/cities')
def np_sender_cities(q:Optional[str]=Query(default=None,max_length=100),city_ref:Optional[str]=Query(default=None,max_length=200),authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return nova_poshta_sender_cities(q,city_ref)
    except (DeliveryNotConfigured,DeliveryUpstreamError) as e:raise HTTPException(502,str(e))
