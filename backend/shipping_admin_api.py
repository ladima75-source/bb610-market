from __future__ import annotations
import json, os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from .db import connect
from .services.delivery import adapter, DeliveryNotConfigured, DeliveryUpstreamError
from .services.delivery_service import get_delivery

router=APIRouter(prefix='/api/v1/admin/orders',tags=['admin-shipping'])

def _admin_auth(authorization:Optional[str]):
    expected=os.getenv('BB610_ADMIN_TOKEN')
    if not expected: raise HTTPException(503,'Admin API is disabled until BB610_ADMIN_TOKEN is configured')
    if not authorization or authorization!='Bearer '+expected: raise HTTPException(401,'Unauthorized')

def _now(): return datetime.now(timezone.utc).isoformat()


@router.post('/{order_id}/delivery/validate-shipment')
def validate_shipment(order_id:str,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    with connect() as con:
        order=con.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
        if not order: raise HTTPException(404,'Order not found')
        d=get_delivery(con,order_id)
        if not d: raise HTTPException(422,'Delivery data missing')
        if d.get('provider')!='nova_poshta': raise HTTPException(422,'TTN validation is supported only for Nova Poshta')
        a=adapter('nova_poshta')
        if not a: raise HTTPException(503,'Nova Poshta adapter unavailable')
        payload={**dict(order),'delivery':d,'customer':{'name':order['customer_name'],'phone':order['customer_phone'],'email':order['customer_email']},'payment':{'method':order['payment_method'],'status':order['payment_status']}}
        try:return a.validate_shipment(payload)
        except DeliveryNotConfigured as e: raise HTTPException(503,str(e))
        except DeliveryUpstreamError as e: raise HTTPException(502,str(e))
        except ValueError as e: raise HTTPException(422,str(e))

@router.post('/{order_id}/delivery/create-shipment')
def create_shipment(order_id:str,authorization:Optional[str]=Header(default=None)):
    _admin_auth(authorization)
    with connect() as con:
        order=con.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
        if not order: raise HTTPException(404,'Order not found')
        d=get_delivery(con,order_id)
        if not d: raise HTTPException(422,'Delivery data missing')
        if d.get('provider')!='nova_poshta': raise HTTPException(422,'Automatic TTN is supported only for Nova Poshta')
        if d.get('tracking_number'):
            return {'ok':True,'duplicate':True,'tracking_number':d['tracking_number'],'shipment_ref':d.get('carrier_shipment_ref'),'delivery':d}
        a=adapter('nova_poshta')
        if not a: raise HTTPException(503,'Nova Poshta adapter unavailable')
        payload={**dict(order),'delivery':d,'customer':{'name':order['customer_name'],'phone':order['customer_phone'],'email':order['customer_email']},'payment':{'method':order['payment_method'],'status':order['payment_status']}}
        try: result=a.create_shipment(payload)
        except DeliveryNotConfigured as e: raise HTTPException(503,str(e))
        except DeliveryUpstreamError as e: raise HTTPException(502,str(e))
        except ValueError as e: raise HTTPException(422,str(e))
        ts=_now()
        con.execute('''UPDATE order_delivery SET tracking_number=?,carrier_shipment_ref=?,carrier_status=?,carrier_status_text=?,last_tracking_at=?,raw_json=? WHERE order_id=?''',(
            result.get('tracking_number'),result.get('shipment_ref'),result.get('status'),result.get('status_text'),ts,json.dumps(result,ensure_ascii=False),order_id))
        con.execute('UPDATE orders SET shipping_status=?,updated_at=?,version=version+1 WHERE id=?',('label_created',ts,order_id))
        con.execute('''INSERT INTO delivery_events(order_id,provider,event_type,carrier_status,message,payload_json,created_at) VALUES(?,?,?,?,?,?,?)''',(
            order_id,'nova_poshta','shipment_created',result.get('status'),result.get('status_text'),json.dumps(result,ensure_ascii=False),ts))
        con.commit()
        return {'ok':True,'duplicate':False,**result,'delivery':get_delivery(con,order_id)}
