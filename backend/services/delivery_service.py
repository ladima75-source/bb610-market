from __future__ import annotations
import json
from datetime import datetime, timezone
from ..db import connect
from .delivery import adapter,capabilities,DeliveryNotConfigured
from .automation import emit,audit

def now(): return datetime.now(timezone.utc).isoformat()
ALLOWED_PROVIDERS={'pickup_dnipro','delivery_dnipro','nova_poshta','ukrposhta'}
ALLOWED_SERVICES={'pickup_dnipro':{'pickup'},'delivery_dnipro':{'courier'},'nova_poshta':{'branch','locker'},'ukrposhta':{'branch'}}

def normalize_fulfillment(f:dict):
    provider=(f.get('provider') or f.get('method') or '').strip();service=(f.get('service') or '').strip()
    if provider=='shipping_ukraine':provider='nova_poshta'
    if provider not in ALLOWED_PROVIDERS:raise ValueError('UNSUPPORTED_DELIVERY_PROVIDER')
    if not service:service={'pickup_dnipro':'pickup','delivery_dnipro':'courier','nova_poshta':'branch','ukrposhta':'branch'}[provider]
    if service not in ALLOWED_SERVICES[provider]:raise ValueError('UNSUPPORTED_DELIVERY_SERVICE')
    city=(f.get('city') or '').strip() or None;city_ref=(f.get('city_ref') or '').strip() or None
    branch=(f.get('branch') or '').strip() or None;branch_ref=(f.get('branch_ref') or '').strip() or None
    address=(f.get('address_line') or f.get('destination') or '').strip() or None
    if provider in {'nova_poshta','ukrposhta'} and not city:raise ValueError('DELIVERY_CITY_REQUIRED')
    if provider in {'nova_poshta','ukrposhta'} and service in {'branch','locker'} and not branch:raise ValueError('DELIVERY_BRANCH_REQUIRED')
    # Stage 13B: Nova Poshta checkout must use carrier dictionary, not arbitrary text.
    if provider=='nova_poshta' and not city_ref:raise ValueError('NOVA_POSHTA_CITY_SELECTION_REQUIRED')
    if provider=='nova_poshta' and not branch_ref:raise ValueError('NOVA_POSHTA_WAREHOUSE_SELECTION_REQUIRED')
    if provider=='delivery_dnipro' and not address:raise ValueError('DELIVERY_ADDRESS_REQUIRED')
    destination=branch or address or city or ('Самовивіз, Дніпро' if provider=='pickup_dnipro' else None)
    return {'method':provider,'provider':provider,'service':service,'destination':destination,'city':city,'city_ref':city_ref,'branch':branch,'branch_ref':branch_ref,'postal_code':(f.get('postal_code') or '').strip() or None,'address_line':address}

def save_delivery(con,order_id,f,customer):
    d=normalize_fulfillment(f)
    con.execute('''INSERT OR REPLACE INTO order_delivery(order_id,provider,service,city,city_ref,branch,branch_ref,postal_code,address_line,recipient_name,recipient_phone,carrier_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(order_id,d['provider'],d['service'],d['city'],d['city_ref'],d['branch'],d['branch_ref'],d['postal_code'],d['address_line'],customer['name'],customer['phone'],'pending'))
    return d

def get_delivery(con,order_id):
    r=con.execute('SELECT * FROM order_delivery WHERE order_id=?',(order_id,)).fetchone();return dict(r) if r else None
def provider_capabilities():return capabilities()
def search_cities(provider,q,limit=20):
    a=adapter(provider)
    if not a:raise ValueError('UNSUPPORTED_DELIVERY_PROVIDER')
    return a.search_cities(q,limit)
def search_branches(provider,city_ref,q='',limit=100):
    a=adapter(provider)
    if not a:raise ValueError('UNSUPPORTED_DELIVERY_PROVIDER')
    return a.search_branches(city_ref,q,limit)
def set_manual_tracking(order_id,tracking_number,note=None):
    tracking_number=(tracking_number or '').strip()
    if len(tracking_number)<4:raise ValueError('INVALID_TRACKING_NUMBER')
    with connect() as con:
        row=con.execute('SELECT provider FROM order_delivery WHERE order_id=?',(order_id,)).fetchone()
        if not row:return None
        ts=now();con.execute('UPDATE order_delivery SET tracking_number=?,carrier_status=?,last_tracking_at=? WHERE order_id=?',(tracking_number,'created',ts,order_id));con.execute('UPDATE orders SET shipping_status=?,updated_at=?,version=version+1 WHERE id=?',('label_created',ts,order_id));con.execute('INSERT INTO delivery_events(order_id,provider,event_type,carrier_status,message,created_at) VALUES(?,?,?,?,?,?)',(order_id,row['provider'],'tracking_attached','created',note or 'Tracking number attached by admin',ts));con.commit();result=get_delivery(con,order_id)
    emit('shipment.tracking_attached','order',order_id,{'provider':row['provider'],'tracking_number':tracking_number},source='admin');audit('shipment.tracking_attached','order',order_id,{'provider':row['provider'],'tracking_number':tracking_number,'note':note},actor_type='admin');return result
def refresh_tracking(order_id):
    with connect() as con:
        d=get_delivery(con,order_id)
        if not d or not d.get('tracking_number'):raise ValueError('TRACKING_NOT_SET')
        a=adapter(d['provider'])
        if not a:raise ValueError('UNSUPPORTED_DELIVERY_PROVIDER')
        result=a.track(d['tracking_number']);ts=now();con.execute('UPDATE order_delivery SET carrier_status=?,carrier_status_text=?,last_tracking_at=?,raw_json=? WHERE order_id=?',(result.get('status'),result.get('status_text'),ts,json.dumps(result,ensure_ascii=False),order_id));con.execute('INSERT INTO delivery_events(order_id,provider,event_type,carrier_status,message,payload_json,created_at) VALUES(?,?,?,?,?,?,?)',(order_id,d['provider'],'tracking_refresh',result.get('status'),result.get('status_text'),json.dumps(result,ensure_ascii=False),ts));con.commit();current=get_delivery(con,order_id)
    emit('shipment.tracking_updated','order',order_id,{'provider':d['provider'],'carrier_status':result.get('status'),'status_text':result.get('status_text')},source='delivery');return current
