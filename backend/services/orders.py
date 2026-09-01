from __future__ import annotations
import base64, hashlib, hmac, json, os, secrets, uuid
from datetime import datetime, timezone
from ..db import connect
from ..catalog_provider import resolve_order_items, CatalogError
from .notifications import notify_new_order
from .delivery_service import save_delivery,get_delivery
from .payment_service import initialize_payment,get_payment,validate_method
from .automation import emit,audit

ORDER_STATUSES=('new','confirmed','preparing','shipped','completed','cancelled')
TRANSITIONS={
 'new':{'confirmed','cancelled'},
 'confirmed':{'new','preparing','cancelled'},
 'preparing':{'confirmed','shipped','cancelled'},
 'shipped':{'preparing','completed'},
 'completed':set(), 'cancelled':set()
}

def now(): return datetime.now(timezone.utc).isoformat()
def token_hash(v): return hashlib.sha256(v.encode()).hexdigest()
def public_token_for_order(order_id):
    secret=os.getenv('BB610_PUBLIC_TOKEN_SECRET') or os.getenv('BB610_ADMIN_TOKEN') or 'BB610-DEV-ONLY-CHANGE-ME'
    sig=hmac.new(secret.encode(),order_id.encode(),hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip('=')
def req_hash(payload): return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def order_number():
    d=datetime.now(timezone.utc).strftime('%y%m%d')
    return f'BB610-{d}-{secrets.randbelow(9000)+1000}'

def _public_order(con, row, include_token=None):
    items=[dict(x) for x in con.execute('SELECT sku,quantity,name,brand,category,variant,unit_price,line_total FROM order_items WHERE order_id=? ORDER BY id',(row['id'],))]
    result={
      'order_id':row['id'],'order_number':row['order_number'],'status':row['status'],'currency':row['currency'],
      'subtotal':row['subtotal'],'delivery_total':row['delivery_total'],'total':row['total'],'items':items,
      'payment':get_payment(con,row['id']),
      'transaction_id':row['order_number'] if bool(row['purchase_ready']) else None,
      'confirmation_url':f"/order/success/?order={row['id']}"+(f"&token={include_token}" if include_token else ''),
      'analytics':{'purchase_ready':bool(row['purchase_ready']),'event_id':row['analytics_event_id']},
      'clear_cart':bool(row['clear_cart']),
      'customer_message':'Замовлення прийнято. Ми зв’яжемося для підтвердження.',
      'delivery':get_delivery(con,row['id'])
    }
    if include_token is not None: result['public_token']=include_token
    return result

def create_order(payload, idem_key):
    items=resolve_order_items(payload['items'])
    payment_method=((payload.get('payment') or {}).get('method') or '').strip()
    validate_method(payment_method)
    h=req_hash(payload)
    with connect() as con:
        old=con.execute('SELECT request_hash,order_id FROM idempotency_keys WHERE key=?',(idem_key,)).fetchone()
        if old:
            if old['request_hash']!=h: raise ValueError('IDEMPOTENCY_CONFLICT')
            row=con.execute('SELECT * FROM orders WHERE id=?',(old['order_id'],)).fetchone()
            return _public_order(con,row,public_token_for_order(row['id']))
        oid=str(uuid.uuid4()); token=public_token_for_order(oid); created=now(); subtotal=round(sum(x['line_total'] for x in items),2); delivery=0.0; total=subtotal
        number=order_number()
        while con.execute('SELECT 1 FROM orders WHERE order_number=?',(number,)).fetchone(): number=order_number()
        event_id=f'purchase_{uuid.uuid4()}'
        c=payload['customer']; f=payload['fulfillment']; source=payload.get('source') or {}
        # Validate structured delivery before any order rows are committed.
        from .delivery_service import normalize_fulfillment
        nf=normalize_fulfillment(f)
        con.execute('''INSERT INTO orders(id,order_number,public_token_hash,created_at,updated_at,status,currency,subtotal,delivery_total,total,customer_name,customer_phone,customer_email,fulfillment_method,fulfillment_destination,comment,payment_method,payment_status,shipping_status,source_channel,source_site,analytics_event_id,purchase_ready,clear_cart)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(oid,number,token_hash(token),created,created,'new','UAH',subtotal,delivery,total,c['name'],c['phone'],c.get('email'),nf['method'],nf.get('destination'),payload.get('comment'),payment_method,'not_required','pending',source.get('channel','web'),source.get('site','market.bb610.com.ua'),event_id,0,0))
        save_delivery(con,oid,f,c)
        payment=initialize_payment(con,oid,payment_method,total,'UAH',number,c,token)
        for x in items:
            con.execute('''INSERT INTO order_items(order_id,sku,product_id,name,brand,category,variant,unit_price,quantity,line_total,currency,snapshot_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(oid,x['sku'],x['product_id'],x['name'],x['brand'],x['category'],x['variant'],x['unit_price'],x['quantity'],x['line_total'],'UAH',json.dumps(x['snapshot'],ensure_ascii=False)))
        con.execute('INSERT INTO order_status_history(order_id,from_status,to_status,note,actor,created_at) VALUES(?,?,?,?,?,?)',(oid,None,'new','Order created','system',created))
        con.execute('INSERT INTO idempotency_keys(key,request_hash,order_id,created_at) VALUES(?,?,?,?)',(idem_key,h,oid,created))
        con.commit(); row=con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone(); result=_public_order(con,row,token)
    notify_new_order({**result,'customer':c})
    emit('order.created','order',oid,{'order_number':number,'total':total,'currency':'UAH','item_count':sum(x['quantity'] for x in items),'payment_method':payment_method,'delivery_provider':nf.get('provider'),'delivery_service':nf.get('service')},source='orders')
    return result

def get_public_order(order_id, token):
    if not token: return None
    with connect() as con:
        row=con.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
        if not row or not secrets.compare_digest(row['public_token_hash'],token_hash(token)): return None
        return _public_order(con,row)

def admin_list(status=None, limit=100):
    with connect() as con:
        sql='SELECT * FROM orders'; args=[]
        if status: sql+=' WHERE status=?'; args.append(status)
        sql+=' ORDER BY created_at DESC LIMIT ?'; args.append(limit)
        rows=con.execute(sql,args).fetchall()
        return [admin_detail(r['id'],con) for r in rows]

def admin_detail(order_id, con=None):
    own=con is None; con=con or connect()
    try:
        row=con.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
        if not row:return None
        items=[dict(x) for x in con.execute('SELECT sku,product_id,name,brand,category,variant,unit_price,quantity,line_total,currency FROM order_items WHERE order_id=? ORDER BY id',(order_id,))]
        hist=[dict(x) for x in con.execute('SELECT from_status,to_status,note,actor,created_at FROM order_status_history WHERE order_id=? ORDER BY id DESC',(order_id,))]
        notices=[dict(x) for x in con.execute('SELECT channel,status,attempted_at,error FROM notification_log WHERE order_id=? ORDER BY id DESC',(order_id,))]
        return {**dict(row),'items':items,'history':hist,'notifications':notices,'admin_notes':[dict(x) for x in con.execute('SELECT id,note,actor,created_at FROM order_admin_notes WHERE order_id=? ORDER BY id DESC',(order_id,))],'delivery':get_delivery(con,order_id),'payment':get_payment(con,order_id),'delivery_events':[dict(x) for x in con.execute('SELECT provider,event_type,carrier_status,message,created_at FROM delivery_events WHERE order_id=? ORDER BY id DESC',(order_id,))]}
    finally:
        if own: con.close()

def update_status(order_id,new_status,note,actor='admin'):
    if new_status not in ORDER_STATUSES: raise ValueError('INVALID_STATUS')
    with connect() as con:
        row=con.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
        if not row:return None
        old=row['status']
        if new_status==old:return admin_detail(order_id,con)
        if new_status not in TRANSITIONS.get(old,set()): raise ValueError('INVALID_TRANSITION')
        ts=now()
        # Stage 7 never unlocks purchase analytics from an operational status change.
        # Stage 9 payment/order-finalization policy will own purchase_ready.
        con.execute('UPDATE orders SET status=?,updated_at=?,version=version+1 WHERE id=?',(new_status,ts,order_id))
        con.execute('INSERT INTO order_status_history(order_id,from_status,to_status,note,actor,created_at) VALUES(?,?,?,?,?,?)',(order_id,old,new_status,note,actor,ts)); con.commit()
        result=admin_detail(order_id,con)
    emit('order.status_changed','order',order_id,{'from_status':old,'to_status':new_status},source=actor)
    audit('order.status_changed','order',order_id,{'from_status':old,'to_status':new_status,'note':note},actor_type=actor)
    return result


def add_admin_note(order_id,note,actor='admin'):
    note=(note or '').strip()
    if not note: raise ValueError('EMPTY_NOTE')
    with connect() as con:
        if not con.execute('SELECT 1 FROM orders WHERE id=?',(order_id,)).fetchone(): return None
        con.execute('INSERT INTO order_admin_notes(order_id,note,actor,created_at) VALUES(?,?,?,?)',(order_id,note,actor,now())); con.commit()
        return admin_detail(order_id,con)
