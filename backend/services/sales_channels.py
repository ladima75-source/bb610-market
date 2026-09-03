
from __future__ import annotations
import csv, json, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
GOOGLE=ROOT/'feeds'/'google-merchant.csv'
META=ROOT/'feeds'/'meta-catalog.csv'
STATUS=ROOT/'feeds'/'feed-status.json'

def _load_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except:return default

def _catalog():
    return _load_json(MASTER,{'products':[],'skus':[]})

def _commerce():
    try:
        from .product_commerce import commerce_map
        return commerce_map()
    except:
        return {}

def _image_value(x):
    if isinstance(x,dict):
        return x.get('local') or x.get('url') or ''
    return x or ''

def _valid_image(path):
    p=str(path or '')
    return ('/real/' in p) or ('/media/products/' in p) or p.startswith('https://') or p.startswith('assets/media/') or p.startswith('assets/img/real/')

def _product_title(p):
    return p.get('official_name') or p.get('name') or p.get('id') or ''

def audit():
    d=_catalog(); cm=_commerce()
    pmap={p.get('id'):p for p in d.get('products',[])}
    rows=[]
    counts={'eligible':0,'blocked':0,'review_required':0,'warnings':0,'total':0}
    reasons_count={}
    for s in d.get('skus',[]):
        sid=s.get('id') or s.get('sku')
        p=pmap.get(s.get('product_id'),{})
        c=cm.get(sid,{})
        reasons=[];warnings=[]
        policy=s.get('feed_policy') or p.get('feed_policy') or ''
        title=_product_title(p)
        image=_image_value(s.get('image') or p.get('image'))
        brand=s.get('brand') or p.get('brand') or ''
        gtin=s.get('gtin') or p.get('gtin') or ''
        mpn=s.get('mpn') or p.get('mpn') or ''
        price=c.get('effective_price') if c.get('effective_price') is not None else c.get('price')
        availability=c.get('availability') or 'unknown'
        enabled=bool(c.get('enabled'))

        if not enabled: reasons.append('Продаж вимкнено')
        try:
            if price is None or float(price)<=0: reasons.append('Немає коректної ціни')
        except:
            reasons.append('Немає коректної ціни')
        if availability not in ('in_stock','out_of_stock','preorder','backorder'):
            reasons.append('Некоректний availability')
        if not title: reasons.append('Немає назви')
        if not brand: reasons.append('Немає бренду')
        if not _valid_image(image): reasons.append('Немає придатного зображення')
        if policy=='blocked': reasons.append('Feed policy: blocked')
        if policy=='review-required': reasons.append('Потрібна ручна перевірка')
        if policy not in ('allowed','blocked','review-required'):
            reasons.append('Feed policy не визначено')
        if not gtin and not mpn:
            warnings.append('GTIN/MPN не вказано')

        state='eligible'
        if policy=='review-required':
            state='review_required'
        elif reasons:
            state='blocked'
        counts['total']+=1;counts[state]+=1
        if warnings: counts['warnings']+=1
        for r in reasons: reasons_count[r]=reasons_count.get(r,0)+1
        rows.append({
          'sku_id':sid,'product_id':s.get('product_id'),'title':title,'brand':brand,
          'price':price,'availability':availability,'sale_enabled':enabled,
          'feed_policy':policy,'image':image,'gtin':gtin,'mpn':mpn,
          'state':state,'reasons':reasons,'warnings':warnings
        })
    return {'generated_at':time.time(),'counts':counts,'reasons':reasons_count,'rows':rows}

def _feed_meta(path):
    if not path.exists():
        return {'exists':False,'size':0,'updated_at':None,'rows':0}
    st=path.stat();n=0
    try:
        with path.open('r',encoding='utf-8-sig',newline='') as f:
            n=max(0,sum(1 for _ in f)-1)
    except: pass
    return {'exists':True,'size':st.st_size,'updated_at':st.st_mtime,'rows':n}

def channels_status():
    a=audit()
    static_status=_load_json(STATUS,{})
    return {
      'audit':a,
      'channels':{
        'google':{
          'name':'Google Merchant',
          'feed_url':'/api/v1/catalog/feeds/google-merchant.csv',
          'static_path':'feeds/google-merchant.csv',
          'file':_feed_meta(GOOGLE)
        },
        'meta':{
          'name':'Meta Catalog',
          'feed_url':'/api/v1/catalog/feeds/meta-catalog.csv',
          'static_path':'feeds/meta-catalog.csv',
          'file':_feed_meta(META)
        }
      },
      'feed_status':static_status
    }
