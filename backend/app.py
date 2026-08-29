from __future__ import annotations
import os
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .db import migrate
from .services.orders import create_order,get_public_order,admin_list,admin_detail,update_status,CatalogError
from .services.delivery_service import provider_capabilities,search_cities,search_branches,set_manual_tracking,refresh_tracking
from .services.delivery import DeliveryNotConfigured,DeliveryUpstreamError
from .services.payment_service import methods as payment_methods,admin_update_cod,process_webhook
from .services.payment import PaymentNotConfigured,PaymentSignatureError
from .services.automation import emit,list_rules,set_rule_enabled,list_jobs,list_approvals,decide_approval,list_audit,summary as automation_summary,approval_for_source
import json

app=FastAPI(title='BB610 Market Commerce API',version='Stage 12')
origins=[x.strip() for x in os.getenv('BB610_CORS_ORIGINS','https://market.bb610.com.ua').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST','PATCH','OPTIONS'],allow_headers=['Content-Type','Idempotency-Key','Authorization'])

@app.on_event('startup')
def startup(): migrate()

class Customer(BaseModel):
    name:str=Field(min_length=2,max_length=120); phone:str=Field(min_length=7,max_length=40); email:Optional[str]=None
class Fulfillment(BaseModel):
    method:str; destination:Optional[str]=Field(default=None,max_length=300)
    provider:Optional[str]=None; service:Optional[str]=None; city:Optional[str]=Field(default=None,max_length=160); city_ref:Optional[str]=Field(default=None,max_length=160)
    branch:Optional[str]=Field(default=None,max_length=240); branch_ref:Optional[str]=Field(default=None,max_length=160); postal_code:Optional[str]=Field(default=None,max_length=20); address_line:Optional[str]=Field(default=None,max_length=300)
class Item(BaseModel):
    sku:str=Field(min_length=3,max_length=128); quantity:int=Field(ge=1,le=999)
class Source(BaseModel): channel:str='web'; site:str='market.bb610.com.ua'
class PaymentSelection(BaseModel): method:str
class CreateOrder(BaseModel):
    client_request_id:str=Field(min_length=8,max_length=128); customer:Customer; fulfillment:Fulfillment; payment:PaymentSelection; comment:Optional[str]=Field(default=None,max_length=1000); currency:str='UAH'; items:list[Item]; source:Source
class StatusUpdate(BaseModel): status:str; note:Optional[str]=Field(default=None,max_length=500)
class TrackingAttach(BaseModel): tracking_number:str=Field(min_length=4,max_length=100); note:Optional[str]=Field(default=None,max_length=500)
class PaymentAdminUpdate(BaseModel): status:str; note:Optional[str]=Field(default=None,max_length=500)

def admin_auth(authorization:Optional[str]):
    expected=os.getenv('BB610_ADMIN_TOKEN')
    if not expected: raise HTTPException(503,'Admin API is disabled until BB610_ADMIN_TOKEN is configured')
    if not authorization or authorization!='Bearer '+expected: raise HTTPException(401,'Unauthorized')

def delivery_error(e):
    if isinstance(e,DeliveryNotConfigured): raise HTTPException(503,str(e))
    if isinstance(e,DeliveryUpstreamError): raise HTTPException(502,str(e))
    raise e

@app.get('/api/v1/health')
def health(): return {'ok':True,'service':'bb610-commerce','stage':12}

@app.get('/api/v1/delivery/providers')
def delivery_providers(): return {'providers':provider_capabilities()}

@app.get('/api/v1/delivery/{provider}/cities')
def delivery_cities(provider:str,q:str=Query(min_length=2,max_length=120),limit:int=Query(default=20,ge=1,le=50)):
    try:return {'items':search_cities(provider,q,limit)}
    except (DeliveryNotConfigured,DeliveryUpstreamError) as e: delivery_error(e)
    except ValueError as e: raise HTTPException(422,str(e))

@app.get('/api/v1/delivery/{provider}/branches')
def delivery_branches(provider:str,city_ref:str=Query(min_length=2,max_length=180),q:str='',limit:int=Query(default=30,ge=1,le=100)):
    try:return {'items':search_branches(provider,city_ref,q,limit)}
    except (DeliveryNotConfigured,DeliveryUpstreamError) as e: delivery_error(e)
    except ValueError as e: raise HTTPException(422,str(e))

@app.post('/api/v1/orders',status_code=201)
def orders_create(body:CreateOrder,idempotency_key:str=Header(alias='Idempotency-Key')):
    p=body.model_dump()
    if p['currency']!='UAH' or p['source']['channel']!='web' or p['source']['site']!='market.bb610.com.ua': raise HTTPException(422,'Unsupported order source/currency')
    try:return create_order(p,idempotency_key)
    except CatalogError as e: raise HTTPException(409,str(e))
    except PaymentNotConfigured as e: raise HTTPException(503,str(e))
    except ValueError as e:
        if str(e)=='IDEMPOTENCY_CONFLICT':raise HTTPException(409,'Idempotency key was already used for a different request')
        raise HTTPException(422,str(e))

@app.get('/api/v1/orders/{order_id}')
def orders_get(order_id:str,token:Optional[str]=Query(default=None)):
    r=get_public_order(order_id,token)
    if not r:raise HTTPException(404,'Order not found')
    return r

@app.get('/api/v1/payments/methods')
def payments_methods(): return {'methods':payment_methods()}

@app.post('/api/v1/payments/webhooks/{provider}')
async def payments_webhook(provider:str,request:Request):
    body=await request.body(); headers={k.lower():v for k,v in request.headers.items()}
    try:return process_webhook(provider,headers,body)
    except PaymentNotConfigured as e: raise HTTPException(503,str(e))
    except PaymentSignatureError as e: raise HTTPException(401,str(e))
    except ValueError as e: raise HTTPException(422,str(e))


class RuleToggle(BaseModel): enabled:bool
class ApprovalDecision(BaseModel): decision:str; note:Optional[str]=Field(default=None,max_length=500)

@app.get('/api/v1/admin/automation/summary')
def admin_automation_summary(authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); return automation_summary()

@app.get('/api/v1/admin/automation/rules')
def admin_automation_rules(authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); return {'rules':list_rules()}

@app.patch('/api/v1/admin/automation/rules/{rule_id}')
def admin_automation_rule_toggle(rule_id:str,body:RuleToggle,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); r=set_rule_enabled(rule_id,body.enabled)
    if not r: raise HTTPException(404,'Automation rule not found')
    return r

@app.get('/api/v1/admin/automation/jobs')
def admin_automation_jobs(status:Optional[str]=None,limit:int=Query(default=100,ge=1,le=500),authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); return {'jobs':list_jobs(status,limit)}

@app.get('/api/v1/admin/automation/approvals')
def admin_automation_approvals(status:Optional[str]='pending',limit:int=Query(default=100,ge=1,le=500),authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); return {'approvals':list_approvals(status,limit)}

@app.patch('/api/v1/admin/automation/approvals/{approval_id}')
def admin_automation_approval_decision(approval_id:str,body:ApprovalDecision,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization)
    try:r=decide_approval(approval_id,body.decision,body.note)
    except ValueError as e: raise HTTPException(409,str(e))
    if not r: raise HTTPException(404,'Approval not found')
    if body.decision=='approved' and r.get('action_type')=='order_cancel':
        payload=json.loads(r.get('payload_json') or '{}'); oid=payload.get('aggregate_id')
        if oid:
            try:update_status(oid,'cancelled',body.note or 'Approved via approval queue',actor='approval')
            except ValueError as e: raise HTTPException(409,'Approval recorded but action failed: '+str(e))
    return r

@app.get('/api/v1/admin/automation/audit')
def admin_automation_audit(limit:int=Query(default=200,ge=1,le=1000),authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); return {'entries':list_audit(limit)}

@app.post('/api/v1/admin/orders/{order_id}/cancel-request')
def admin_order_cancel_request(order_id:str,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization)
    r=admin_detail(order_id)
    if not r: raise HTTPException(404,'Order not found')
    if r['status'] in ('completed','cancelled'): raise HTTPException(409,'Order is already final')
    eid=emit('order.cancel_requested','order',order_id,{'order_number':r['order_number'],'current_status':r['status']},source='admin')
    return {'approval_required':True,'event_id':eid,'approval':approval_for_source(eid)}

@app.patch('/api/v1/admin/orders/{order_id}/payment')
def admin_order_payment(order_id:str,body:PaymentAdminUpdate,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization)
    try:r=admin_update_cod(order_id,body.status,body.note)
    except ValueError as e: raise HTTPException(409,str(e))
    if not r: raise HTTPException(404,'Order/payment not found')
    return r

@app.get('/api/v1/admin/orders')
def admin_orders(status:Optional[str]=None,limit:int=Query(default=100,ge=1,le=500),authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); return {'orders':admin_list(status,limit)}
@app.get('/api/v1/admin/orders/{order_id}')
def admin_order(order_id:str,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization); r=admin_detail(order_id)
    if not r:raise HTTPException(404,'Order not found')
    return r
@app.patch('/api/v1/admin/orders/{order_id}/status')
def admin_order_status(order_id:str,body:StatusUpdate,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization)
    try:r=update_status(order_id,body.status,body.note)
    except ValueError as e:raise HTTPException(409,str(e))
    if not r:raise HTTPException(404,'Order not found')
    return r
@app.post('/api/v1/admin/orders/{order_id}/delivery/tracking')
def admin_attach_tracking(order_id:str,body:TrackingAttach,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization)
    try:r=set_manual_tracking(order_id,body.tracking_number,body.note)
    except ValueError as e:raise HTTPException(422,str(e))
    if not r:raise HTTPException(404,'Order/delivery not found')
    return r
@app.post('/api/v1/admin/orders/{order_id}/delivery/refresh')
def admin_refresh_tracking(order_id:str,authorization:Optional[str]=Header(default=None)):
    admin_auth(authorization)
    try:return refresh_tracking(order_id)
    except (DeliveryNotConfigured,DeliveryUpstreamError) as e: delivery_error(e)
    except ValueError as e:raise HTTPException(422,str(e))
