from __future__ import annotations
import os
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field
from .services.delivery.base import DeliveryNotConfigured, DeliveryUpstreamError
from .services.integrations import nova_poshta_status, save_nova_poshta_settings, test_nova_poshta, nova_poshta_sender_options, nova_poshta_sender_cities
from .services.telegram_notifications import telegram_status, save_telegram_settings, test_telegram, discover_telegram_chats
from .services.payment_settings import payment_settings_status, save_payment_settings
from .services.integration_secrets import set_values
from .services.payment.mono import MonoPaymentAdapter
from .services.checkbox_prro import status as checkbox_status, test as test_checkbox
from .services.meta_capi import status as meta_capi_status

router=APIRouter(prefix='/api/v1/admin/integrations',tags=['admin-integrations'])
class PaymentSettingsPatch(BaseModel):
    cod_enabled:Optional[bool]=None
    bank_transfer_enabled:Optional[bool]=None
    bank_recipient:Optional[str]=Field(default=None,max_length=200)
    bank_iban:Optional[str]=Field(default=None,max_length=64)
    bank_purpose:Optional[str]=Field(default=None,max_length=200)
    mono_token:Optional[str]=Field(default=None,min_length=8,max_length=1024)

class CheckboxSettingsPatch(BaseModel):
    cashier_login:Optional[str]=Field(default=None,min_length=2,max_length=200)
    cashier_password:Optional[str]=Field(default=None,min_length=2,max_length=512)

class MetaCapiSettingsPatch(BaseModel):
    access_token:Optional[str]=Field(default=None,min_length=20,max_length=4096)

class TelegramSettingsPatch(BaseModel):
    bot_token:Optional[str]=Field(default=None,min_length=8,max_length=512)
    chat_id:Optional[str]=Field(default=None,max_length=128)

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
def list_integrations(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return {'integrations':[nova_poshta_status(),payment_settings_status(),telegram_status()]}
@router.get('/payments')
def get_payments(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return payment_settings_status()
@router.patch('/payments')
def patch_payments(body:PaymentSettingsPatch,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:
        data=body.model_dump(exclude_unset=True)
        mono_token=data.pop('mono_token',None)
        if mono_token is not None:set_values({'payments.mono_token':mono_token})
        return save_payment_settings(**data)
    except ValueError as e:raise HTTPException(422,str(e))
    except RuntimeError as e:raise HTTPException(500,str(e))
@router.post('/payments/mono/test')
def test_mono(authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return MonoPaymentAdapter().test()
    except Exception as e:raise HTTPException(502,str(e))

@router.get('/checkbox')
def get_checkbox(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return checkbox_status()
@router.patch('/checkbox')
def patch_checkbox(body:CheckboxSettingsPatch,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    data=body.model_dump(exclude_unset=True);values={}
    if 'cashier_login' in data:values['checkbox.cashier_login']=data['cashier_login']
    if 'cashier_password' in data:values['checkbox.cashier_password']=data['cashier_password']
    if values:set_values(values)
    return checkbox_status()
@router.post('/checkbox/test')
def checkbox_test(authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return test_checkbox()
    except RuntimeError as e:raise HTTPException(502,str(e))

@router.get('/meta-capi')
def get_meta_capi(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return meta_capi_status()
@router.patch('/meta-capi')
def patch_meta_capi(body:MetaCapiSettingsPatch,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    data=body.model_dump(exclude_unset=True)
    token=data.get('access_token')
    if token is not None:set_values({'meta.access_token':token})
    return meta_capi_status()

@router.get('/telegram')
def get_telegram(authorization:Optional[str]=Header(default=None)):_admin_auth(authorization);return telegram_status()

@router.patch('/telegram')
def patch_telegram(body:TelegramSettingsPatch,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return save_telegram_settings(**body.model_dump(exclude_unset=True))
    except ValueError as e:raise HTTPException(422,str(e))
    except RuntimeError as e:raise HTTPException(500,str(e))

@router.post('/telegram/test')
def telegram_test(authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return test_telegram()
    except RuntimeError as e:raise HTTPException(502,str(e))

@router.get('/telegram/chats')
def telegram_chats(authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    try:return discover_telegram_chats()
    except RuntimeError as e:raise HTTPException(502,str(e))

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
