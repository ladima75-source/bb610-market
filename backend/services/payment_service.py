from __future__ import annotations
import json, os
from datetime import datetime, timezone
from ..db import connect
from .payment import PaymentNotConfigured, PaymentSignatureError
from .payment.unconfigured import UnconfiguredPaymentAdapter
from .automation import emit,audit

PAYMENT_STATUSES=('not_required','pending','requires_action','paid','failed','cancelled','refunded','partially_refunded')

def now(): return datetime.now(timezone.utc).isoformat()
def env_bool(name,default=False): return os.getenv(name,'1' if default else '0').strip().lower() in ('1','true','yes','on')

def adapter():
    # Stage 9 intentionally ships no live acquiring credentials/provider implementation.
    # A future LiqPay/WayForPay/etc adapter plugs into this single factory.
    return UnconfiguredPaymentAdapter()

def methods():
    a=adapter(); cod=env_bool('BB610_PAYMENT_COD_ENABLED',False)
    return [
      {'id':'cod','label':'Післяплата','enabled':cod,'provider':'carrier','requires_redirect':False},
      {'id':'online_card','label':'Оплата карткою онлайн','enabled':a.configured(),'provider':a.provider if a.configured() else None,'requires_redirect':True}
    ]

def validate_method(method:str):
    m={x['id']:x for x in methods()}.get(method)
    if not m: raise ValueError('UNSUPPORTED_PAYMENT_METHOD')
    if not m['enabled']:
        if method=='online_card': raise PaymentNotConfigured('Online payment provider is not configured')
        raise PaymentNotConfigured('Cash on delivery is disabled')
    return m

def initialize_payment(con,order_id:str,method:str,amount:float,currency:str,order_number:str,customer:dict,public_token:str):
    m=validate_method(method); ts=now()
    if method=='cod':
        # A valid server-created COD order is a completed ecommerce checkout.
        # Payment itself remains pending until carrier/administrator confirms collection.
        con.execute('INSERT INTO order_payments(order_id,method,provider,status,amount,currency,last_event_at) VALUES(?,?,?,?,?,?,?)',(order_id,'cod','carrier','pending',amount,currency,ts))
        con.execute('UPDATE orders SET payment_method=?,payment_status=?,purchase_ready=1,clear_cart=1 WHERE id=?',('cod','pending',order_id))
        con.execute('INSERT INTO payment_events(order_id,provider,event_type,from_status,to_status,payload_json,created_at) VALUES(?,?,?,?,?,?,?)',(order_id,'carrier','payment_initialized',None,'pending','{}',ts))
        return {'required':True,'method':'cod','provider':'carrier','status':'pending','redirect_url':None}
    a=adapter()
    return_url=(os.getenv('BB610_PUBLIC_SITE_URL','https://market.bb610.com.ua').rstrip('/')+f'/order/success/?order={order_id}&token={public_token}')
    s=a.create_session(order_id=order_id,order_number=order_number,amount=amount,currency=currency,return_url=return_url,customer=customer)
    con.execute('INSERT INTO order_payments(order_id,method,provider,status,amount,currency,provider_payment_id,checkout_url,last_event_at,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?)',(order_id,'online_card',s.provider,s.status,amount,currency,s.provider_payment_id,s.redirect_url,ts,json.dumps(s.raw or {},ensure_ascii=False)))
    con.execute('UPDATE orders SET payment_method=?,payment_status=?,purchase_ready=0,clear_cart=0 WHERE id=?',('online_card',s.status,order_id))
    con.execute('INSERT INTO payment_events(order_id,provider,event_type,from_status,to_status,payload_json,created_at) VALUES(?,?,?,?,?,?,?)',(order_id,s.provider,'payment_initialized',None,s.status,json.dumps(s.raw or {},ensure_ascii=False),ts))
    return {'required':True,'method':'online_card','provider':s.provider,'status':s.status,'redirect_url':s.redirect_url}

def get_payment(con,order_id:str):
    r=con.execute('SELECT * FROM order_payments WHERE order_id=?',(order_id,)).fetchone()
    if not r:return {'required':False,'method':None,'provider':None,'status':'not_required','redirect_url':None}
    return {'required':True,'method':r['method'],'provider':r['provider'],'status':r['status'],'amount':r['amount'],'currency':r['currency'],'redirect_url':r['checkout_url'],'provider_payment_id':r['provider_payment_id'],'paid_at':r['paid_at'],'refunded_at':r['refunded_at']}

def _apply_status(con,order_id,new_status,event_type,provider='system',provider_event_id=None,payload=None,actor='system'):
    if new_status not in PAYMENT_STATUSES: raise ValueError('INVALID_PAYMENT_STATUS')
    p=con.execute('SELECT * FROM order_payments WHERE order_id=?',(order_id,)).fetchone()
    if not p:return None
    old=p['status']; ts=now()
    if old==new_status:return get_payment(con,order_id)
    allowed={
      'pending':{'paid','failed','cancelled'},
      'requires_action':{'paid','failed','cancelled'},
      'failed':set(),'cancelled':set(),
      'paid':{'refunded','partially_refunded'},
      'partially_refunded':{'refunded'},'refunded':set(),'not_required':set()
    }
    if new_status not in allowed.get(old,set()): raise ValueError('INVALID_PAYMENT_TRANSITION')
    paid_at=ts if new_status=='paid' else p['paid_at']; refunded_at=ts if new_status=='refunded' else p['refunded_at']
    con.execute('UPDATE order_payments SET status=?,paid_at=?,refunded_at=?,last_event_at=?,raw_json=COALESCE(?,raw_json) WHERE order_id=?',(new_status,paid_at,refunded_at,ts,json.dumps(payload,ensure_ascii=False) if payload is not None else None,order_id))
    # Online payment unlocks ecommerce purchase only after server-confirmed paid.
    # COD purchase is unlocked at accepted order creation; marking collection does not emit a second purchase.
    method=p['method']
    ready=1 if (method=='cod' or new_status=='paid') else 0
    clear=1 if (method=='cod' or new_status=='paid') else 0
    con.execute('UPDATE orders SET payment_status=?,purchase_ready=?,clear_cart=?,updated_at=? WHERE id=?',(new_status,ready,clear,ts,order_id))
    con.execute('INSERT OR IGNORE INTO payment_events(order_id,provider,provider_event_id,event_type,from_status,to_status,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)',(order_id,provider,provider_event_id,event_type,old,new_status,json.dumps(payload or {},ensure_ascii=False),ts))
    return get_payment(con,order_id)

def admin_update_cod(order_id,status:str,note:str|None=None):
    with connect() as con:
        p=con.execute('SELECT * FROM order_payments WHERE order_id=?',(order_id,)).fetchone()
        if not p:return None
        if p['method']!='cod': raise ValueError('ONLINE_PAYMENT_STATUS_IS_WEBHOOK_OWNED')
        if status not in ('paid','cancelled'): raise ValueError('INVALID_COD_PAYMENT_STATUS')
        r=_apply_status(con,order_id,status,'admin_cod_update','carrier',payload={'note':note},actor='admin'); con.commit()
    emit('payment.'+status,'order',order_id,{'method':'cod','status':status},source='admin')
    audit('payment.status_changed','order',order_id,{'method':'cod','status':status,'note':note},actor_type='admin')
    return r

def process_webhook(provider:str,headers:dict[str,str],body:bytes):
    a=adapter()
    if not a.configured() or a.provider!=provider: raise PaymentNotConfigured('Payment provider is not configured')
    ev=a.parse_webhook(headers,body)
    with connect() as con:
        if con.execute('SELECT 1 FROM payment_events WHERE provider=? AND provider_event_id=?',(provider,ev.provider_event_id)).fetchone():
            return {'ok':True,'duplicate':True}
        order_id=ev.order_id
        if not order_id and ev.provider_payment_id:
            r=con.execute('SELECT order_id FROM order_payments WHERE provider=? AND provider_payment_id=?',(provider,ev.provider_payment_id)).fetchone(); order_id=r['order_id'] if r else None
        if not order_id: raise ValueError('PAYMENT_ORDER_NOT_FOUND')
        _apply_status(con,order_id,ev.status,ev.event_type,provider,ev.provider_event_id,ev.raw); con.commit()
    emit('payment.'+ev.status,'order',order_id,{'provider':provider,'status':ev.status,'provider_event_id':ev.provider_event_id},source='payment_webhook',event_id='evt_payment_'+str(ev.provider_event_id))
    return {'ok':True,'duplicate':False,'order_id':order_id,'status':ev.status}
