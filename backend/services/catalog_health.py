
from __future__ import annotations
import json, re, time, hashlib
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
OVERRIDES=ROOT/'data'/'catalog-health.overrides.json'

def _load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _save_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def _catalog():
    return _load_json(MASTER,{'products':[],'skus':[]})

def _commerce():
    try:
        from .product_commerce import commerce_map
        return commerce_map()
    except:
        return {}

def _norm(s):
    s=str(s or '').lower()
    s=s.replace('™',' ').replace('®',' ')
    s=re.sub(r'\([^)]*\)',' ',s)
    s=re.sub(r'[^a-zа-яіїєґ0-9]+',' ',s,flags=re.I)
    s=' '.join(s.split())
    return s

def _image(x):
    if isinstance(x,dict):return x.get('local') or x.get('url') or ''
    return str(x or '')

def _desc(p):
    return (p.get('description_uk') or p.get('description') or p.get('short_description_uk') or p.get('short_description') or '').strip()

def _severity_rank(x):
    return {'critical':0,'warning':1,'info':2}.get(x,9)

def _overrides():
    x=_load_json(OVERRIDES,{'ignored_duplicate_keys':[]})
    if not isinstance(x.get('ignored_duplicate_keys'),list):x['ignored_duplicate_keys']=[]
    return x

def _dup_key(kind,ids):
    raw=kind+'|'+'|'.join(sorted(str(x) for x in ids))
    return hashlib.sha1(raw.encode()).hexdigest()[:16]

def scan_health():
    d=_catalog();cm=_commerce()
    products=d.get('products',[]);skus=d.get('skus',[])
    by_product={}
    for s in skus:by_product.setdefault(s.get('product_id'),[]).append(s)

    issues=[]
    def add(pid,sku,code,label,severity='warning',detail=''):
        issues.append({'product_id':pid or '','sku_id':sku or '','code':code,'label':label,'severity':severity,'detail':detail})

    # Duplicate SKU IDs in master.
    seen={}
    for s in skus:
        sid=s.get('id') or s.get('sku') or ''
        if not sid:continue
        seen.setdefault(sid,[]).append(s)
    for sid,arr in seen.items():
        if len(arr)>1:
            for s in arr:add(s.get('product_id'),sid,'duplicate_sku','Дубль SKU ID','critical',f'SKU {sid} зустрічається {len(arr)} рази')

    for p in products:
        pid=p.get('id');title=p.get('official_name') or p.get('name') or ''
        brand=(p.get('brand') or '').strip()
        category=(p.get('category') or '').strip()
        image=_image(p.get('image'))
        ps=by_product.get(pid,[])

        if not title:add(pid,'','missing_title','Немає назви','critical')
        if not brand:add(pid,'','missing_brand','Немає бренду','warning')
        if not category:add(pid,'','missing_category','Немає категорії','warning')
        if not image:add(pid,'','missing_image','Немає фото','warning')
        if not _desc(p):add(pid,'','missing_description','Немає опису','info')
        if not ps:add(pid,'','zero_sku','Товар без SKU','warning')

        low=(' '+title+' '+str(pid)+' ').lower()
        if any(x in low for x in (' demo ',' test ',' legacy ',' override ')):
            add(pid,'','legacy_demo','Legacy / DEMO / TEST','warning','Назва або ID містить службову ознаку')

        for s in ps:
            sid=s.get('id') or s.get('sku') or ''
            c=cm.get(sid,{})
            price=c.get('effective_price') if c.get('effective_price') is not None else c.get('price')
            enabled=bool(c.get('enabled'))
            avail=str(c.get('availability') or 'unknown')
            stock=c.get('stock')
            simg=_image(s.get('image') or image)
            policy=s.get('feed_policy') or p.get('feed_policy') or ''

            try:good_price=price is not None and float(price)>0
            except:good_price=False
            if not good_price:add(pid,sid,'missing_price','SKU без ціни','critical' if enabled else 'warning')
            if enabled and not good_price:add(pid,sid,'sale_without_price','Продаж увімкнено без ціни','critical')
            if enabled and avail=='unknown':add(pid,sid,'sale_unknown_availability','Продаж ON, availability невідомий','warning')
            if avail=='in_stock' and stock is not None:
                try:
                    if float(stock)<=0:add(pid,sid,'stock_conflict','В наявності, але залишок 0','warning')
                except:pass
            if avail=='out_of_stock' and stock is not None:
                try:
                    if float(stock)>0:add(pid,sid,'stock_conflict','Немає в наявності, але залишок > 0','warning')
                except:pass
            if not simg:add(pid,sid,'missing_image','SKU без фото','warning')
            if policy not in ('allowed','blocked','review-required'):
                add(pid,sid,'missing_feed_policy','Feed policy не визначено','info')

    counts={'critical':0,'warning':0,'info':0}
    for i in issues:counts[i['severity']]=counts.get(i['severity'],0)+1
    issues.sort(key=lambda x:(_severity_rank(x['severity']),x['label'],x['product_id'],x['sku_id']))
    return {'generated_at':time.time(),'products':len(products),'skus':len(skus),'counts':counts,'issues':issues}

def scan_duplicates():
    d=_catalog();products=d.get('products',[])
    ignored=set(_overrides().get('ignored_duplicate_keys',[]))
    groups=[]

    rows=[]
    for p in products:
        pid=p.get('id');title=p.get('official_name') or p.get('name') or ''
        rows.append({
          'product_id':pid,'title':title,'brand':(p.get('brand') or '').strip(),
          'category':(p.get('category') or '').strip(),'image':_image(p.get('image')),
          'norm_title':_norm(title),'norm_brand':_norm(p.get('brand'))
        })

    emitted=set()
    def emit(kind,confidence,reason,items):
        ids=[x['product_id'] for x in items]
        key=_dup_key(kind,ids)
        if key in emitted or key in ignored:return
        emitted.add(key)
        groups.append({'key':key,'kind':kind,'confidence':confidence,'reason':reason,'items':items})

    # Exact title + brand.
    buckets={}
    for r in rows:
        if r['norm_title']:
            buckets.setdefault((r['norm_title'],r['norm_brand']),[]).append(r)
    for (nt,nb),arr in buckets.items():
        if len(arr)>1:emit('exact_title_brand',1.0,'Однакова нормалізована назва та бренд',arr)

    # Same image across different products.
    ib={}
    for r in rows:
        if r['image']:ib.setdefault(r['image'],[]).append(r)
    for image,arr in ib.items():
        if len(arr)>1:emit('same_image',0.93,'Однакове основне зображення у різних товарів',arr)

    # Fuzzy title pairs, preferably same brand.
    n=len(rows)
    for i in range(n):
        a=rows[i]
        if len(a['norm_title'])<5:continue
        for j in range(i+1,n):
            b=rows[j]
            if len(b['norm_title'])<5:continue
            same_brand=bool(a['norm_brand'] and a['norm_brand']==b['norm_brand'])
            ratio=SequenceMatcher(None,a['norm_title'],b['norm_title']).ratio()
            # Avoid treating clearly different formula variants as duplicates unless extremely close.
            threshold=0.92 if same_brand else 0.96
            if ratio>=threshold:
                emit('similar_title',round(ratio,3),f'Схожість назв {ratio:.0%}'+(' · той самий бренд' if same_brand else ''),[a,b])

    groups.sort(key=lambda g:(-g['confidence'],g['kind']))
    return {'generated_at':time.time(),'groups':groups,'count':len(groups),'ignored_count':len(ignored)}

def dashboard():
    return {'health':scan_health(),'duplicates':scan_duplicates()}

def ignore_duplicate(key):
    x=_overrides()
    if key not in x['ignored_duplicate_keys']:x['ignored_duplicate_keys'].append(key)
    _save_json(OVERRIDES,x)
    return {'ok':True,'key':key}

def restore_duplicate(key):
    x=_overrides()
    x['ignored_duplicate_keys']=[k for k in x['ignored_duplicate_keys'] if k!=key]
    _save_json(OVERRIDES,x)
    return {'ok':True,'key':key}

def overrides_data():
    return _overrides()
