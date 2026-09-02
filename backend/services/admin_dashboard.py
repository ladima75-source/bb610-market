from __future__ import annotations
import json, os, sqlite3, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'

def _load_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return default

def _catalog():
    return _load_json(MASTER, {'products':[],'skus':[]})

def _commerce():
    try:
        from .product_commerce import commerce_map
        return commerce_map()
    except:
        return {}

def _order_db_candidates():
    out=[]
    for p in ROOT.rglob('*.db'):
        if '.venv' in p.parts or '.git' in p.parts:
            continue
        try:
            if p.stat().st_size < 500*1024*1024:
                out.append(p)
        except:
            pass
    return out

def _find_order_table():
    """
    Best-effort discovery of an order table without binding Stage 18A
    to one concrete DB schema.
    """
    preferred=('orders','shop_orders','commerce_orders')
    for db in _order_db_candidates():
        try:
            con=sqlite3.connect(db)
            con.row_factory=sqlite3.Row
            tables=[x[0] for x in con.execute("select name from sqlite_master where type='table'")]
            ordered=sorted(tables,key=lambda x:(x.lower() not in preferred,'order' not in x.lower(),x))
            for t in ordered:
                cols=[x[1] for x in con.execute(f'pragma table_info("{t}")')]
                low={c.lower():c for c in cols}
                if not any(k in low for k in ('id','order_id','number')):
                    continue
                has_time=any(k in low for k in ('created_at','created','date','created_ts','timestamp'))
                has_order_signal=('order' in t.lower()) or any(k in low for k in ('status','total','amount','customer_phone'))
                if has_time and has_order_signal:
                    con.close()
                    return db,t,low
            con.close()
        except:
            pass
    return None

def _parse_dt(v):
    if v is None:return None
    if isinstance(v,(int,float)):
        # seconds or milliseconds
        x=float(v)
        if x>10_000_000_000:x/=1000
        try:return datetime.fromtimestamp(x,timezone.utc)
        except:return None
    s=str(v).strip()
    if not s:return None
    # common sqlite / ISO variants
    for candidate in (s,s.replace('Z','+00:00')):
        try:
            dt=datetime.fromisoformat(candidate)
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            pass
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%d.%m.%Y %H:%M:%S','%d.%m.%Y'):
        try:return datetime.strptime(s,fmt).replace(tzinfo=timezone.utc)
        except:pass
    return None

def _orders_metrics():
    result={
      'source':'not_found',
      'today':0,'last7':0,'last30':0,
      'revenue_today':0.0,'revenue_7':0.0,'revenue_30':0.0,
      'avg_check_30':0.0,
      'statuses':{},
      'recent':[]
    }
    loc=_find_order_table()
    if not loc:return result
    db,table,low=loc
    result['source']=f'{db.name}:{table}'
    try:
        con=sqlite3.connect(db);con.row_factory=sqlite3.Row
        rows=[dict(r) for r in con.execute(f'SELECT * FROM "{table}" ORDER BY rowid DESC LIMIT 3000')]
        con.close()
    except:
        return result

    time_col=next((low[k] for k in ('created_at','created','date','created_ts','timestamp') if k in low),None)
    total_col=next((low[k] for k in ('total','amount','total_amount','grand_total','price') if k in low),None)
    status_col=next((low[k] for k in ('status','order_status','state') if k in low),None)
    id_col=next((low[k] for k in ('order_id','number','id') if k in low),None)
    customer_col=next((low[k] for k in ('customer_name','name','customer','client_name') if k in low),None)
    phone_col=next((low[k] for k in ('customer_phone','phone','client_phone') if k in low),None)

    now=datetime.now(timezone.utc)
    d1=now-timedelta(days=1); d7=now-timedelta(days=7); d30=now-timedelta(days=30)
    rev30=[]
    recent=[]
    for r in rows:
        dt=_parse_dt(r.get(time_col)) if time_col else None
        try:
            total=float(r.get(total_col) or 0) if total_col else 0.0
        except:
            total=0.0
        status=str(r.get(status_col) or 'unknown') if status_col else 'unknown'
        result['statuses'][status]=result['statuses'].get(status,0)+1
        if dt:
            if dt>=d1:
                result['today']+=1;result['revenue_today']+=total
            if dt>=d7:
                result['last7']+=1;result['revenue_7']+=total
            if dt>=d30:
                result['last30']+=1;result['revenue_30']+=total
                rev30.append(total)
        if len(recent)<8:
            recent.append({
              'id':str(r.get(id_col) or '') if id_col else '',
              'created_at':dt.isoformat() if dt else str(r.get(time_col) or ''),
              'status':status,
              'total':total,
              'customer':str(r.get(customer_col) or '') if customer_col else '',
              'phone':str(r.get(phone_col) or '') if phone_col else ''
            })
    result['avg_check_30']=round(sum(rev30)/len(rev30),2) if rev30 else 0.0
    result['revenue_today']=round(result['revenue_today'],2)
    result['revenue_7']=round(result['revenue_7'],2)
    result['revenue_30']=round(result['revenue_30'],2)
    result['recent']=recent
    return result

def _catalog_metrics():
    d=_catalog();products=d.get('products',[]);skus=d.get('skus',[]);cm=_commerce()
    product_by={p.get('id'):p for p in products}
    published=0; no_photo=0; review=0; categories={}
    for p in products:
        title=p.get('official_name') or p.get('name')
        if title:published+=1
        im=p.get('image')
        if isinstance(im,dict):im=im.get('local') or im.get('url')
        if not im:no_photo+=1
        fp=p.get('feed_policy')
        if fp=='review-required':review+=1
        cat=p.get('category') or 'Без категорії'
        categories[cat]=categories.get(cat,0)+1

    priced=0; in_stock=0; sale_enabled=0; no_price=0; out_stock=0
    feed_allowed=0; feed_blocked=0
    sku_no_photo=0
    for s in skus:
        sid=s.get('id') or s.get('sku')
        c=cm.get(sid,{})
        price=c.get('effective_price')
        if price not in (None,'',0,0.0):priced+=1
        else:no_price+=1
        av=str(c.get('availability') or 'unknown')
        if av=='in_stock':in_stock+=1
        if av=='out_of_stock':out_stock+=1
        if c.get('enabled'):sale_enabled+=1
        fp=s.get('feed_policy') or product_by.get(s.get('product_id'),{}).get('feed_policy')
        if fp=='allowed':feed_allowed+=1
        elif fp in ('blocked','review-required'):feed_blocked+=1
        im=s.get('image') or product_by.get(s.get('product_id'),{}).get('image')
        if isinstance(im,dict):im=im.get('local') or im.get('url')
        if not im:sku_no_photo+=1

    alerts=[]
    if no_price:alerts.append({'level':'warn','label':'SKU без ціни','count':no_price,'href':'products.html'})
    if sku_no_photo:alerts.append({'level':'warn','label':'SKU без фото','count':sku_no_photo,'href':'catalog.html'})
    if out_stock:alerts.append({'level':'info','label':'Немає в наявності','count':out_stock,'href':'products.html'})
    if review:alerts.append({'level':'warn','label':'Картки на перевірці','count':review,'href':'catalog.html'})
    if feed_blocked:alerts.append({'level':'info','label':'Не допущено у фіди','count':feed_blocked,'href':'catalog-import.html'})

    return {
      'products':len(products),'skus':len(skus),'published_products':published,
      'priced_skus':priced,'no_price_skus':no_price,'in_stock_skus':in_stock,
      'out_stock_skus':out_stock,'sale_enabled_skus':sale_enabled,
      'no_photo_products':no_photo,'no_photo_skus':sku_no_photo,
      'review_products':review,'feed_allowed_skus':feed_allowed,'feed_blocked_skus':feed_blocked,
      'categories':categories,'alerts':alerts
    }

def _integrations():
    env=os.environ
    def present(*names):
        return any(bool(env.get(n)) for n in names)
    return {
      'nova_poshta':{'configured':present('NOVA_POSHTA_API_KEY','NP_API_KEY'),'label':'Нова пошта'},
      'telegram':{'configured':present('TELEGRAM_BOT_TOKEN','BB610_TELEGRAM_BOT_TOKEN'),'label':'Telegram'},
      'google_feed':{'configured':True,'label':'Google Merchant feed','path':'/api/v1/catalog/feeds/google-merchant.csv'},
      'meta_feed':{'configured':True,'label':'Meta Catalog feed','path':'/api/v1/catalog/feeds/meta-catalog.csv'},
      'online_payment':{'configured':present('MONOBANK_TOKEN','MONO_TOKEN','WAYFORPAY_MERCHANT_ACCOUNT'),'label':'Онлайн-оплата'},
    }

def _recent_activity():
    imports=_load_json(ROOT/'var'/'catalog-import'/'history.json',[])
    maintenance=_load_json(ROOT/'var'/'product-maintenance'/'history.json',[])
    rows=[]
    for x in imports[:10]:
        rows.append({
          'time':x.get('time',0),'type':'import','title':x.get('filename') or 'Імпорт каталогу',
          'detail':f"mode={x.get('mode','')} · content={x.get('content_rows',0)} · commerce={x.get('commerce_rows',0)}",
          'ok':bool((x.get('publish') or {}).get('published',True))
        })
    for x in maintenance[:10]:
        rows.append({
          'time':x.get('time',0),'type':x.get('action','maintenance'),
          'title':x.get('title') or x.get('product_id') or 'Зміна каталогу',
          'detail':f"{x.get('action','')} · {x.get('reason','')}",
          'ok':bool((x.get('publish') or {}).get('published',True))
        })
    rows.sort(key=lambda x:x.get('time',0),reverse=True)
    return rows[:12]

def dashboard():
    orders=_orders_metrics()
    catalog=_catalog_metrics()
    return {
      'generated_at':time.time(),
      'orders':orders,
      'catalog':catalog,
      'integrations':_integrations(),
      'activity':_recent_activity()
    }
