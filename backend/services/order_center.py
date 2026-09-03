
from __future__ import annotations
import sqlite3, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VAR=ROOT/'var'/'order-center'
DB=VAR/'order_center.db'
VAR.mkdir(parents=True,exist_ok=True)

STATUS_CHAIN=['new','confirmed','processing','ready','shipped','completed']
STATUS_LABELS={
 'new':'Нове','confirmed':'Підтверджено','processing':'Комплектується',
 'ready':'Готове до відправлення','shipped':'Відправлено',
 'completed':'Виконано','cancelled':'Скасовано'
}
ALIASES={
 'pending':'new','created':'new','new':'new',
 'confirmed':'confirmed','approved':'confirmed',
 'processing':'processing','packing':'processing','assembling':'processing',
 'ready':'ready','ready_to_ship':'ready',
 'shipped':'shipped','sent':'shipped',
 'completed':'completed','done':'completed',
 'cancelled':'cancelled','canceled':'cancelled'
}

def _meta_db():
    con=sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS order_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, order_key TEXT NOT NULL, note TEXT NOT NULL, created_at REAL NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS order_events (id INTEGER PRIMARY KEY AUTOINCREMENT, order_key TEXT NOT NULL, event_type TEXT NOT NULL, from_status TEXT, to_status TEXT, reason TEXT, created_at REAL NOT NULL)")
    con.commit()
    return con

def _db_candidates():
    out=[]
    for p in ROOT.rglob('*.db'):
        if '.venv' in p.parts or '.git' in p.parts or p==DB:
            continue
        try:
            if p.stat().st_size < 1000*1024*1024: out.append(p)
        except: pass
    return out

def _find_orders():
    preferred=('orders','shop_orders','commerce_orders')
    for db in _db_candidates():
        try:
            con=sqlite3.connect(db)
            tables=[x[0] for x in con.execute("select name from sqlite_master where type='table'")]
            ranked=sorted(tables,key=lambda t:(t.lower() not in preferred,'order' not in t.lower(),t))
            for t in ranked:
                cols=[x[1] for x in con.execute(f'pragma table_info("{t}")')]
                low={c.lower():c for c in cols}
                id_col=next((low[k] for k in ('order_id','number','id') if k in low),None)
                status_col=next((low[k] for k in ('status','order_status','state') if k in low),None)
                time_col=next((low[k] for k in ('created_at','created','date','timestamp') if k in low),None)
                if id_col and status_col and time_col:
                    con.close(); return db,t,low
            con.close()
        except: pass
    return None

def _parse_dt(v):
    if v is None:return None
    if isinstance(v,(int,float)):
        x=float(v)
        if x>10_000_000_000:x/=1000
        try:return time.strftime('%Y-%m-%dT%H:%M:%S',time.localtime(x))
        except:return str(v)
    s=str(v)
    return s.replace(' ','T',1) if ' ' in s else s

def _canon(v):
    s=str(v or 'new').strip().lower()
    return ALIASES.get(s,s)

def _col(low,*names):
    return next((low[n] for n in names if n in low),None)

def _read_orders(limit=2000):
    loc=_find_orders()
    if not loc:return {'source':'not_found','orders':[]}
    db,table,low=loc
    con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    try: rows=[dict(r) for r in con.execute(f'SELECT * FROM "{table}" ORDER BY rowid DESC LIMIT ?', (limit,))]
    finally: con.close()

    idc=_col(low,'order_id','number','id'); statusc=_col(low,'status','order_status','state')
    createdc=_col(low,'created_at','created','date','timestamp'); totalc=_col(low,'total','amount','total_amount','grand_total')
    payc=_col(low,'payment_method','payment','pay_method'); paystatusc=_col(low,'payment_status','pay_status')
    deliveryc=_col(low,'delivery_method','shipping_method','delivery','shipping'); ttnc=_col(low,'ttn','tracking_number','tracking','np_ttn')
    namec=_col(low,'customer_name','name','client_name','customer'); phonec=_col(low,'customer_phone','phone','client_phone')
    emailc=_col(low,'customer_email','email'); cityc=_col(low,'city','delivery_city','shipping_city')
    branchc=_col(low,'branch','warehouse','delivery_branch','np_branch'); commentc=_col(low,'comment','customer_comment','notes')

    orders=[]
    for r in rows:
        key=str(r.get(idc) or '')
        raw_status=str(r.get(statusc) or 'new')
        orders.append({
          'id':key,'status':_canon(raw_status),'status_raw':raw_status,'created_at':_parse_dt(r.get(createdc)),
          'total':r.get(totalc) if totalc else None,
          'payment_method':str(r.get(payc) or '') if payc else '',
          'payment_status':str(r.get(paystatusc) or '') if paystatusc else '',
          'delivery_method':str(r.get(deliveryc) or '') if deliveryc else '',
          'ttn':str(r.get(ttnc) or '') if ttnc else '',
          'customer_name':str(r.get(namec) or '') if namec else '',
          'phone':str(r.get(phonec) or '') if phonec else '',
          'email':str(r.get(emailc) or '') if emailc else '',
          'city':str(r.get(cityc) or '') if cityc else '',
          'branch':str(r.get(branchc) or '') if branchc else '',
          'comment':str(r.get(commentc) or '') if commentc else '',
        })
    return {'source':f'{db.name}:{table}','orders':orders}

def _notes_map():
    con=_meta_db(); con.row_factory=sqlite3.Row
    notes={}
    for r in con.execute('SELECT * FROM order_notes ORDER BY id DESC'):
        notes.setdefault(r['order_key'],[]).append(dict(r))
    con.close(); return notes

def _events_map():
    con=_meta_db(); con.row_factory=sqlite3.Row
    ev={}
    for r in con.execute('SELECT * FROM order_events ORDER BY id DESC'):
        ev.setdefault(r['order_key'],[]).append(dict(r))
    con.close(); return ev

def list_orders():
    x=_read_orders(); notes=_notes_map(); events=_events_map()
    for o in x['orders']:
        o['notes']=notes.get(o['id'],[])[:5]
        o['events']=events.get(o['id'],[])[:10]
    counts={}
    for o in x['orders']: counts[o['status']]=counts.get(o['status'],0)+1
    return {'source':x['source'],'orders':x['orders'],'counts':counts,'status_chain':STATUS_CHAIN,'status_labels':STATUS_LABELS}

def _find_order_row(order_id):
    loc=_find_orders()
    if not loc: raise ValueError('Таблицю замовлень не знайдено')
    db,table,low=loc
    idc=_col(low,'order_id','number','id'); statusc=_col(low,'status','order_status','state')
    con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    row=con.execute(f'SELECT rowid,* FROM "{table}" WHERE CAST("{idc}" AS TEXT)=? LIMIT 1',(str(order_id),)).fetchone()
    con.close()
    if not row: raise ValueError('Замовлення не знайдено')
    return db,table,dict(row),idc,statusc

def _log(order_id,event_type,from_status=None,to_status=None,reason=''):
    con=_meta_db()
    con.execute('INSERT INTO order_events(order_key,event_type,from_status,to_status,reason,created_at) VALUES(?,?,?,?,?,?)',
                (str(order_id),event_type,from_status,to_status,reason,time.time()))
    con.commit(); con.close()

def transition(order_id,direction):
    db,table,row,idc,statusc=_find_order_row(order_id)
    current=_canon(row.get(statusc))
    if current=='cancelled': raise ValueError('Скасоване замовлення не можна повернути у робочий статус')
    if current not in STATUS_CHAIN: raise ValueError(f'Невідомий статус: {current}')
    i=STATUS_CHAIN.index(current)
    if direction=='forward':
        if i>=len(STATUS_CHAIN)-1: raise ValueError('Це останній робочий статус')
        target=STATUS_CHAIN[i+1]
    elif direction=='back':
        if i<=0: raise ValueError('Відкотити статус назад неможливо')
        target=STATUS_CHAIN[i-1]
    else: raise ValueError('direction має бути forward або back')
    con=sqlite3.connect(db)
    con.execute(f'UPDATE "{table}" SET "{statusc}"=? WHERE CAST("{idc}" AS TEXT)=?',(target,str(order_id)))
    con.commit(); con.close()
    _log(order_id,'status_change',current,target,'')
    return {'ok':True,'order_id':str(order_id),'from':current,'to':target}

def cancel(order_id,reason=''):
    db,table,row,idc,statusc=_find_order_row(order_id)
    current=_canon(row.get(statusc))
    if current=='cancelled': raise ValueError('Замовлення вже скасовано')
    con=sqlite3.connect(db)
    con.execute(f'UPDATE "{table}" SET "{statusc}"=? WHERE CAST("{idc}" AS TEXT)=?',('cancelled',str(order_id)))
    con.commit(); con.close()
    _log(order_id,'cancel',current,'cancelled',str(reason or '').strip())
    return {'ok':True,'order_id':str(order_id),'from':current,'to':'cancelled'}

def add_note(order_id,note):
    note=str(note or '').strip()
    if not note: raise ValueError('Коментар порожній')
    _find_order_row(order_id)
    con=_meta_db()
    con.execute('INSERT INTO order_notes(order_key,note,created_at) VALUES(?,?,?)',(str(order_id),note,time.time()))
    con.commit(); con.close()
    _log(order_id,'note',None,None,note)
    return {'ok':True}

def order_detail(order_id):
    x=list_orders()
    o=next((r for r in x['orders'] if str(r['id'])==str(order_id)),None)
    if not o: raise ValueError('Замовлення не знайдено')
    return {'order':o,'status_chain':STATUS_CHAIN,'status_labels':STATUS_LABELS}
