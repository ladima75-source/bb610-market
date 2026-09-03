
from __future__ import annotations
import json, os, shutil, sqlite3, subprocess, time, uuid, hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DB=ROOT/'var'/'commerce-control'/'commerce_control.db'
DB.parent.mkdir(parents=True,exist_ok=True)
CATALOG=ROOT/'data'/'catalog.master.json'
CATEGORIES=ROOT/'data'/'categories.master.json'
SHOWCASE=ROOT/'data'/'homepage.showcase.json'

OPEN_STATUSES={'new','confirmed','processing','ready'}
FINAL_STATUSES={'completed','cancelled','canceled','returned'}

def _conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    c.executescript("""
    CREATE TABLE IF NOT EXISTS drafts(
      id TEXT PRIMARY KEY,
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      base_hash TEXT,
      payload_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'draft',
      created_at REAL NOT NULL,
      updated_at REAL NOT NULL,
      published_at REAL,
      note TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_drafts_entity ON drafts(entity_type,entity_id,status);

    CREATE TABLE IF NOT EXISTS stock_items(
      sku_id TEXT PRIMARY KEY,
      physical REAL NOT NULL DEFAULT 0,
      reserved REAL NOT NULL DEFAULT 0,
      updated_at REAL NOT NULL,
      source TEXT NOT NULL DEFAULT 'manual'
    );
    CREATE TABLE IF NOT EXISTS stock_movements(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      time REAL NOT NULL,
      sku_id TEXT NOT NULL,
      movement_type TEXT NOT NULL,
      qty REAL NOT NULL,
      before_qty REAL,
      after_qty REAL,
      order_id TEXT,
      return_id TEXT,
      note TEXT
    );
    CREATE TABLE IF NOT EXISTS reservations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id TEXT NOT NULL,
      sku_id TEXT NOT NULL,
      qty REAL NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      created_at REAL NOT NULL,
      released_at REAL,
      UNIQUE(order_id,sku_id,status)
    );
    CREATE TABLE IF NOT EXISTS returns(
      id TEXT PRIMARY KEY,
      order_id TEXT NOT NULL,
      status TEXT NOT NULL,
      reason TEXT,
      refund_amount REAL NOT NULL DEFAULT 0,
      restock INTEGER NOT NULL DEFAULT 0,
      created_at REAL NOT NULL,
      updated_at REAL NOT NULL,
      completed_at REAL
    );
    CREATE TABLE IF NOT EXISTS return_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      return_id TEXT NOT NULL,
      sku_id TEXT NOT NULL,
      qty REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS customer_notes(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_key TEXT NOT NULL,
      note TEXT NOT NULL,
      created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      time REAL NOT NULL,
      module TEXT NOT NULL,
      action TEXT NOT NULL,
      object_id TEXT,
      detail_json TEXT
    );
    """)
    return c

def _event(module,action,obj='',detail=None):
    c=_conn()
    c.execute("INSERT INTO events(time,module,action,object_id,detail_json) VALUES(?,?,?,?,?)",
              (time.time(),module,action,obj,json.dumps(detail or {},ensure_ascii=False)))
    c.commit();c.close()

def _load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _save_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(p)

def _hash(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]

def _git_publish(message):
    subprocess.run(['git','add','data'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
        subprocess.run(['git','commit','-m',message],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return commit

def _backup_file(p):
    if not p.exists():return None
    b=ROOT/'var'/'commerce-control'/'backups'/time.strftime('%Y%m%d-%H%M%S')
    b.mkdir(parents=True,exist_ok=True)
    dst=b/p.name
    shutil.copy2(p,dst)
    return str(dst)

def _entity_source(entity_type):
    if entity_type=='product':return CATALOG
    if entity_type=='category':return CATEGORIES
    if entity_type=='showcase':return SHOWCASE
    raise ValueError('Unsupported entity type')

def _find_entity(entity_type,entity_id):
    p=_entity_source(entity_type);data=_load_json(p,{})
    if entity_type=='product':
        products=data.get('products',[])
        for x in products:
            if str(x.get('id'))==str(entity_id):return x
    elif entity_type=='category':
        arr=data.get('categories',data if isinstance(data,list) else [])
        for x in arr:
            if str(x.get('id'))==str(entity_id):return x
    elif entity_type=='showcase':
        if str(entity_id) in ('homepage','main','default'):return data
    return None

def list_entities(entity_type,q=''):
    q=(q or '').lower().strip()
    if entity_type=='product':
        data=_load_json(CATALOG,{'products':[]})
        out=[]
        for p in data.get('products',[]):
            title=p.get('official_name') or p.get('name') or ''
            if q and q not in (str(p.get('id',''))+' '+title+' '+str(p.get('brand',''))).lower():continue
            out.append({'id':p.get('id'),'title':title,'subtitle':p.get('brand','')})
        return out[:200]
    if entity_type=='category':
        data=_load_json(CATEGORIES,{'categories':[]})
        arr=data.get('categories',data if isinstance(data,list) else [])
        out=[]
        for x in arr:
            title=x.get('name') or x.get('title') or x.get('id')
            if q and q not in (str(x.get('id',''))+' '+str(title)).lower():continue
            out.append({'id':x.get('id'),'title':title,'subtitle':''})
        return out[:200]
    if entity_type=='showcase':
        return [{'id':'homepage','title':'Головна / Вітрина','subtitle':'homepage.showcase.json'}]
    return []

def create_draft(entity_type,entity_id,note=''):
    current=_find_entity(entity_type,entity_id)
    if current is None:raise ValueError('Entity not found')
    now=time.time();did=uuid.uuid4().hex[:12]
    c=_conn()
    c.execute("""INSERT INTO drafts(id,entity_type,entity_id,base_hash,payload_json,status,created_at,updated_at,note)
                 VALUES(?,?,?,?,?,'draft',?,?,?)""",
              (did,entity_type,str(entity_id),_hash(current),json.dumps(current,ensure_ascii=False),now,now,note))
    c.commit();c.close()
    _event('drafts','create',did,{'entity_type':entity_type,'entity_id':entity_id})
    return get_draft(did)

def update_draft(draft_id,payload,note=None):
    c=_conn();row=c.execute("SELECT * FROM drafts WHERE id=?",(draft_id,)).fetchone()
    if not row:raise ValueError('Draft not found')
    if row['status']!='draft':raise ValueError('Only draft can be edited')
    c.execute("UPDATE drafts SET payload_json=?,updated_at=?,note=COALESCE(?,note) WHERE id=?",
              (json.dumps(payload,ensure_ascii=False),time.time(),note,draft_id))
    c.commit();c.close()
    _event('drafts','update',draft_id)
    return get_draft(draft_id)

def get_draft(draft_id):
    c=_conn();r=c.execute("SELECT * FROM drafts WHERE id=?",(draft_id,)).fetchone();c.close()
    if not r:return None
    x=dict(r);x['payload']=json.loads(x.pop('payload_json'))
    current=_find_entity(x['entity_type'],x['entity_id'])
    x['base_changed']=current is not None and _hash(current)!=x.get('base_hash')
    return x

def list_drafts():
    c=_conn();rows=[dict(r) for r in c.execute("SELECT * FROM drafts ORDER BY updated_at DESC LIMIT 500")];c.close()
    for x in rows:x.pop('payload_json',None)
    return rows

def publish_draft(draft_id,force=False,publish_git=True):
    d=get_draft(draft_id)
    if not d:raise ValueError('Draft not found')
    if d['status']!='draft':raise ValueError('Draft already published/discarded')
    if d['base_changed'] and not force:raise ValueError('Published source changed after draft creation. Review or force publish.')

    p=_entity_source(d['entity_type']);data=_load_json(p,{})
    _backup_file(p)
    payload=d['payload']
    if d['entity_type']=='product':
        arr=data.get('products',[]);found=False
        for i,x in enumerate(arr):
            if str(x.get('id'))==str(d['entity_id']):arr[i]=payload;found=True;break
        if not found:raise ValueError('Product no longer exists')
    elif d['entity_type']=='category':
        arr=data.get('categories',data if isinstance(data,list) else [])
        found=False
        for i,x in enumerate(arr):
            if str(x.get('id'))==str(d['entity_id']):arr[i]=payload;found=True;break
        if not found:raise ValueError('Category no longer exists')
        if isinstance(data,dict):data['categories']=arr
        else:data=arr
    elif d['entity_type']=='showcase':
        data=payload
    _save_json(p,data)
    commit=None
    if publish_git:commit=_git_publish(f'Publish {d["entity_type"]} draft {draft_id}')
    c=_conn()
    c.execute("UPDATE drafts SET status='published',published_at=?,updated_at=? WHERE id=?",(time.time(),time.time(),draft_id))
    c.commit();c.close()
    _event('drafts','publish',draft_id,{'commit':commit,'entity_type':d['entity_type'],'entity_id':d['entity_id']})
    return {'ok':True,'commit':commit}

def discard_draft(draft_id):
    c=_conn();c.execute("UPDATE drafts SET status='discarded',updated_at=? WHERE id=? AND status='draft'",(time.time(),draft_id));c.commit();c.close()
    _event('drafts','discard',draft_id)
    return {'ok':True}

def _commerce_map():
    try:
        from .product_commerce import commerce_map
        return commerce_map()
    except:return {}

def _sku_rows():
    d=_load_json(CATALOG,{'products':[],'skus':[]})
    prod={str(p.get('id')):p for p in d.get('products',[])}
    cm=_commerce_map()
    out=[]
    for s in d.get('skus',[]):
        sid=str(s.get('id') or s.get('sku') or '')
        p=prod.get(str(s.get('product_id')), {})
        c=cm.get(sid,{})
        stock=c.get('stock',0)
        try:stock=float(stock or 0)
        except:stock=0.0
        out.append({'sku_id':sid,'product_id':s.get('product_id'),'title':p.get('official_name') or p.get('name') or sid,'source_stock':stock})
    return out

def sync_stock_from_catalog(only_missing=True):
    now=time.time();c=_conn();added=updated=0
    for r in _sku_rows():
        old=c.execute("SELECT * FROM stock_items WHERE sku_id=?",(r['sku_id'],)).fetchone()
        if old and only_missing:continue
        if old:
            c.execute("UPDATE stock_items SET physical=?,updated_at=?,source='catalog_sync' WHERE sku_id=?",(r['source_stock'],now,r['sku_id']));updated+=1
        else:
            c.execute("INSERT INTO stock_items(sku_id,physical,reserved,updated_at,source) VALUES(?,?,0,?,'catalog_sync')",(r['sku_id'],r['source_stock'],now));added+=1
    c.commit();c.close()
    _event('stock','sync','',{'added':added,'updated':updated})
    return {'added':added,'updated':updated}

def stock_data(q=''):
    q=(q or '').lower().strip()
    rows0={r['sku_id']:r for r in _sku_rows()}
    c=_conn()
    rows=[]
    for r in c.execute("SELECT * FROM stock_items ORDER BY sku_id"):
        x=dict(r);meta=rows0.get(x['sku_id'],{})
        x.update({'title':meta.get('title',x['sku_id']),'product_id':meta.get('product_id')})
        x['available']=x['physical']-x['reserved']
        if q and q not in (x['sku_id']+' '+str(x['title'])+' '+str(x.get('product_id',''))).lower():continue
        rows.append(x)
    moves=[dict(r) for r in c.execute("SELECT * FROM stock_movements ORDER BY time DESC LIMIT 300")]
    c.close()
    return {'rows':rows,'movements':moves}

def set_physical_stock(sku_id,qty,note='Manual correction'):
    qty=float(qty)
    c=_conn();r=c.execute("SELECT * FROM stock_items WHERE sku_id=?",(sku_id,)).fetchone()
    before=float(r['physical']) if r else 0.0
    reserved=float(r['reserved']) if r else 0.0
    now=time.time()
    if r:c.execute("UPDATE stock_items SET physical=?,updated_at=?,source='manual' WHERE sku_id=?",(qty,now,sku_id))
    else:c.execute("INSERT INTO stock_items(sku_id,physical,reserved,updated_at,source) VALUES(?,?,?,?,?)",(sku_id,qty,0,now,'manual'))
    c.execute("""INSERT INTO stock_movements(time,sku_id,movement_type,qty,before_qty,after_qty,note)
                 VALUES(?,?,?,?,?,?,?)""",(now,sku_id,'correction',qty-before,before,qty,note))
    c.commit();c.close()
    _event('stock','set_physical',sku_id,{'before':before,'after':qty,'reserved':reserved})
    return {'ok':True}

def _order_db_candidates():
    return [
      ROOT/'var'/'order-center'/'order_center.db',
      ROOT/'orders.db',
      ROOT/'var'/'orders.db',
      ROOT/'data'/'orders.db',
    ]

def _discover_orders():
    # First try the Order Center metadata DB and then conservative SQLite discovery.
    results=[]
    seen=set()
    for db in _order_db_candidates():
        if not db.exists():continue
        try:
            con=sqlite3.connect(db);con.row_factory=sqlite3.Row
            tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for t in tables:
                cols=[r[1] for r in con.execute(f"PRAGMA table_info('{t}')")]
                low={c.lower():c for c in cols}
                idc=next((low[k] for k in ('id','order_id','order_key','number') if k in low),None)
                statusc=next((low[k] for k in ('status','state') if k in low),None)
                if not idc or not statusc:continue
                # Need some customer-ish columns or likely order table name.
                if 'order' not in t.lower() and not any(k in low for k in ('phone','customer_phone','email','customer_email')):continue
                try:rows=con.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 2000').fetchall()
                except:continue
                for rr in rows:
                    r=dict(rr);oid=str(r.get(idc,''))
                    if not oid or oid in seen:continue
                    seen.add(oid)
                    results.append({'order_id':oid,'status':str(r.get(statusc,'')).lower(),'row':r,'db':str(db),'table':t})
            con.close()
        except:continue
    return results

def _extract_items(order):
    r=order.get('row',{})
    candidates=['items_json','items','cart_json','cart','products_json','products']
    for k in candidates:
        if k not in r or r[k] in (None,''):continue
        val=r[k]
        if isinstance(val,str):
            try:val=json.loads(val)
            except:continue
        if isinstance(val,dict):val=val.get('items',val.get('products',[]))
        if not isinstance(val,list):continue
        out=[]
        for x in val:
            if not isinstance(x,dict):continue
            sku=x.get('sku_id') or x.get('sku') or x.get('id')
            qty=x.get('qty') or x.get('quantity') or x.get('count') or 1
            try:qty=float(qty)
            except:qty=1
            if sku:out.append({'sku_id':str(sku),'qty':qty})
        if out:return out
    return []

def rebuild_reservations():
    orders=_discover_orders();c=_conn();now=time.time()
    active={(str(r['order_id']),str(r['sku_id'])):float(r['qty']) for r in c.execute("SELECT * FROM reservations WHERE status='active'")}
    desired={}
    unresolved=[]
    for o in orders:
        if o['status'] not in OPEN_STATUSES:continue
        items=_extract_items(o)
        if not items:
            unresolved.append(o['order_id']);continue
        for it in items:
            key=(o['order_id'],it['sku_id'])
            desired[key]=desired.get(key,0)+it['qty']

    # Release obsolete active reservations.
    for key,qty in active.items():
        if key in desired:continue
        oid,sku=key
        c.execute("UPDATE reservations SET status='released',released_at=? WHERE order_id=? AND sku_id=? AND status='active'",(now,oid,sku))

    # Recreate desired reservations deterministically.
    for key,qty in desired.items():
        oid,sku=key
        old=c.execute("SELECT * FROM reservations WHERE order_id=? AND sku_id=? AND status='active'",(oid,sku)).fetchone()
        if old and float(old['qty'])==qty:continue
        if old:c.execute("UPDATE reservations SET status='released',released_at=? WHERE id=?",(now,old['id']))
        c.execute("INSERT INTO reservations(order_id,sku_id,qty,status,created_at) VALUES(?,?,?,'active',?)",(oid,sku,qty,now))

    # Recompute reserved totals.
    c.execute("UPDATE stock_items SET reserved=0")
    sums=c.execute("SELECT sku_id,SUM(qty) q FROM reservations WHERE status='active' GROUP BY sku_id").fetchall()
    for s in sums:
        row=c.execute("SELECT 1 FROM stock_items WHERE sku_id=?",(s['sku_id'],)).fetchone()
        if not row:c.execute("INSERT INTO stock_items(sku_id,physical,reserved,updated_at,source) VALUES(?,0,?,?,?)",(s['sku_id'],s['q'],now,'reservation'))
        else:c.execute("UPDATE stock_items SET reserved=?,updated_at=? WHERE sku_id=?",(s['q'],now,s['sku_id']))
    c.commit();c.close()
    _event('stock','rebuild_reservations','',{'active_orders':len(desired),'unresolved_orders':unresolved[:50]})
    return {'orders_found':len(orders),'reservations':len(desired),'unresolved_orders':unresolved}

def create_return(order_id,items,reason='',refund_amount=0,restock=False):
    rid='RET-'+time.strftime('%Y%m%d')+'-'+uuid.uuid4().hex[:6].upper()
    now=time.time();c=_conn()
    c.execute("INSERT INTO returns(id,order_id,status,reason,refund_amount,restock,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
              (rid,str(order_id),'requested',reason,float(refund_amount or 0),1 if restock else 0,now,now))
    for x in items:
        sku=str(x.get('sku_id',''));qty=float(x.get('qty') or 0)
        if sku and qty>0:c.execute("INSERT INTO return_items(return_id,sku_id,qty) VALUES(?,?,?)",(rid,sku,qty))
    c.commit();c.close()
    _event('returns','create',rid,{'order_id':order_id,'restock':restock})
    return {'ok':True,'return_id':rid}

def set_return_status(return_id,status):
    allowed={'requested','approved','received','refunded','completed','rejected'}
    if status not in allowed:raise ValueError('Invalid return status')
    c=_conn();r=c.execute("SELECT * FROM returns WHERE id=?",(return_id,)).fetchone()
    if not r:raise ValueError('Return not found')
    old=r['status'];now=time.time()
    if old=='completed' and status!='completed':raise ValueError('Completed return is terminal')
    c.execute("UPDATE returns SET status=?,updated_at=?,completed_at=? WHERE id=?",(status,now,now if status=='completed' else None,return_id))
    if status=='completed' and old!='completed' and int(r['restock']):
        items=c.execute("SELECT * FROM return_items WHERE return_id=?",(return_id,)).fetchall()
        for it in items:
            st=c.execute("SELECT * FROM stock_items WHERE sku_id=?",(it['sku_id'],)).fetchone()
            before=float(st['physical']) if st else 0
            after=before+float(it['qty'])
            if st:c.execute("UPDATE stock_items SET physical=?,updated_at=?,source='return' WHERE sku_id=?",(after,now,it['sku_id']))
            else:c.execute("INSERT INTO stock_items(sku_id,physical,reserved,updated_at,source) VALUES(?,?,0,?,'return')",(it['sku_id'],after,now))
            c.execute("""INSERT INTO stock_movements(time,sku_id,movement_type,qty,before_qty,after_qty,order_id,return_id,note)
                         VALUES(?,?,?,?,?,?,?,?,?)""",(now,it['sku_id'],'return_restock',it['qty'],before,after,r['order_id'],return_id,'Return completed'))
    c.commit();c.close()
    _event('returns','status',return_id,{'from':old,'to':status})
    return {'ok':True}

def returns_data():
    c=_conn();rows=[]
    for r in c.execute("SELECT * FROM returns ORDER BY created_at DESC"):
        x=dict(r);x['items']=[dict(i) for i in c.execute("SELECT sku_id,qty FROM return_items WHERE return_id=?",(x['id'],))]
        rows.append(x)
    c.close();return rows

def _customer_key(row):
    email=str(row.get('email') or row.get('customer_email') or '').strip().lower()
    phone=''.join(ch for ch in str(row.get('phone') or row.get('customer_phone') or '') if ch.isdigit())
    name=str(row.get('name') or row.get('customer_name') or row.get('full_name') or '').strip()
    return email or phone or name.lower() or ''

def customers_data(q=''):
    q=(q or '').lower().strip()
    orders=_discover_orders()
    groups={}
    for o in orders:
        r=o['row'];key=_customer_key(r)
        if not key:continue
        g=groups.setdefault(key,{'customer_key':key,'name':r.get('name') or r.get('customer_name') or r.get('full_name') or '',
                                'phone':r.get('phone') or r.get('customer_phone') or '',
                                'email':r.get('email') or r.get('customer_email') or '',
                                'orders':[],'order_count':0,'total_amount':0.0})
        amt=r.get('total') or r.get('amount') or r.get('total_amount') or 0
        try:amt=float(amt or 0)
        except:amt=0
        g['orders'].append({'order_id':o['order_id'],'status':o['status'],'amount':amt})
        g['order_count']+=1;g['total_amount']+=amt
    c=_conn()
    for key,g in groups.items():
        g['notes']=[dict(n) for n in c.execute("SELECT id,note,created_at FROM customer_notes WHERE customer_key=? ORDER BY created_at DESC",(key,))]
    c.close()
    arr=list(groups.values())
    if q:arr=[g for g in arr if q in (g['customer_key']+' '+str(g['name'])+' '+str(g['phone'])+' '+str(g['email'])).lower()]
    arr.sort(key=lambda x:(-x['order_count'],-x['total_amount']))
    return arr[:500]

def add_customer_note(customer_key,note):
    note=(note or '').strip()
    if not note:raise ValueError('Empty note')
    c=_conn();c.execute("INSERT INTO customer_notes(customer_key,note,created_at) VALUES(?,?,?)",(customer_key,note,time.time()));c.commit();c.close()
    _event('customers','note',customer_key)
    return {'ok':True}

def alerts_data():
    out=[]
    # Stock alerts.
    c=_conn()
    for r in c.execute("SELECT * FROM stock_items"):
        avail=float(r['physical'])-float(r['reserved'])
        if avail<0:
            out.append({'severity':'critical','module':'stock','code':'oversold','object':r['sku_id'],'message':f'Резерв перевищує фізичний залишок: доступно {avail:g}'})
        elif avail==0 and float(r['physical'])>0:
            out.append({'severity':'warning','module':'stock','code':'fully_reserved','object':r['sku_id'],'message':'Увесь фізичний залишок зарезервовано'})
    c.close()

    # Catalog health integration if Stage 18J exists.
    try:
        from .catalog_health import scan_health
        h=scan_health()
        for x in h.get('issues',[])[:500]:
            if x.get('severity') in ('critical','warning'):
                out.append({'severity':x['severity'],'module':'catalog','code':x.get('code'),'object':x.get('sku_id') or x.get('product_id'),'message':x.get('label')})
    except:pass

    # Sales channel integration if Stage 18H exists.
    try:
        from .sales_channels import channels_status
        s=channels_status()
        audit=s.get('audit') or {}
        blocked=audit.get('blocked') or audit.get('blocked_count') or 0
        review=audit.get('review_required') or audit.get('review_required_count') or 0
        if blocked:out.append({'severity':'warning','module':'channels','code':'feed_blocked','object':'feeds','message':f'Feed blocked: {blocked}'})
        if review:out.append({'severity':'warning','module':'channels','code':'feed_review','object':'feeds','message':f'Review required: {review}'})
    except:pass

    # Backups.
    try:
        from .backup_center import list_backups
        b=list_backups()
        if not b:out.append({'severity':'critical','module':'backup','code':'no_backup','object':'backup','message':'Резервні копії не знайдено'})
        elif time.time()-float(b[0]['created_at'])>7*86400:
            out.append({'severity':'warning','module':'backup','code':'stale_backup','object':b[0]['id'],'message':'Останній backup старіший за 7 днів'})
    except:pass

    rank={'critical':0,'warning':1,'info':2}
    out.sort(key=lambda x:(rank.get(x['severity'],9),x['module'],x['code']))
    return out

def dashboard():
    sync_stock_from_catalog(True)
    c=_conn()
    counts={
      'drafts':c.execute("SELECT COUNT(*) FROM drafts WHERE status='draft'").fetchone()[0],
      'returns_open':c.execute("SELECT COUNT(*) FROM returns WHERE status NOT IN ('completed','rejected')").fetchone()[0],
      'stock_skus':c.execute("SELECT COUNT(*) FROM stock_items").fetchone()[0],
      'negative_available':c.execute("SELECT COUNT(*) FROM stock_items WHERE physical-reserved<0").fetchone()[0]
    }
    c.close()
    alerts=alerts_data()
    counts['alerts']=len(alerts);counts['critical_alerts']=sum(1 for a in alerts if a['severity']=='critical')
    return {'counts':counts,'alerts':alerts[:100]}
