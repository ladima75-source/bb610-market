from __future__ import annotations
import json, re, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from ..db import connect, BASE_DIR
from ..catalog_provider import load_catalog
from .product_commerce import commerce_map

MEDIA_DIR = BASE_DIR / 'runtime' / 'media' / 'products'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

def _now(): return datetime.now(timezone.utc).isoformat()
def _slug(s:str)->str:
    s=(s or '').strip().lower()
    s=re.sub(r'[^a-z0-9а-яіїєґ\-\s]+','',s,flags=re.I)
    s=re.sub(r'[\s_]+','-',s).strip('-')
    return s or ('product-'+uuid.uuid4().hex[:8])
def _split_lines(v):
    if isinstance(v,list): return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or '').split('\n') if x.strip()]

def _static():
    d=load_catalog(); return d, {p['id']:p for p in d.get('products',[])}, {s['id']:s for s in d.get('skus',[])}

def _rows():
    with connect() as con:
        return con.execute('SELECT product_id,slug,content_json,published,created_at,updated_at FROM product_content ORDER BY updated_at DESC').fetchall()

def _overrides():
    out={}
    for r in _rows():
        try: c=json.loads(r['content_json'])
        except Exception: c={}
        c.update({'id':r['product_id'],'slug':r['slug'],'cms_published':bool(r['published']),'cms_created_at':r['created_at'],'cms_updated_at':r['updated_at']})
        out[r['product_id']]=c
    return out

def _dynamic_skus(product_id:Optional[str]=None):
    q='SELECT sku,product_id,variant,volume_value,volume_unit,image,currency,created_at,updated_at FROM dynamic_skus'
    params=[]
    if product_id: q+=' WHERE product_id=?'; params=[product_id]
    q+=' ORDER BY created_at'
    with connect() as con: rows=con.execute(q,params).fetchall()
    cm=commerce_map(); out=[]
    for r in rows:
        c=cm.get(r['sku'],{})
        out.append({'id':r['sku'],'sku':r['sku'],'product_id':r['product_id'],'variant_id':r['product_id']+'--'+r['sku'].lower(),
                    'slug':r['sku'].lower(),'variant':r['variant'],'volume_weight':{'value':r['volume_value'],'unit':r['volume_unit']} if r['volume_value'] is not None else None,
                    'price':c.get('effective_price'),'base_price':c.get('price'),'sale_price':c.get('sale_price'),'currency':r['currency'],
                    'availability':c.get('availability','unknown'),'stock_qty':c.get('stock_qty'),'stock_label':_stock(c.get('availability','unknown')),
                    'offer_status':'active' if c.get('enabled') else 'draft','commercial_status':'active' if c.get('enabled') else 'paused',
                    'image':r['image'],'url':'/product.html?id='+r['product_id']+'&sku='+r['sku'],'runtime_dynamic':True})
    return out

def _stock(v): return {'in_stock':'В наявності','out_of_stock':'Немає в наявності','preorder':'Передзамовлення','backorder':'Під замовлення'}.get(v,'Наявність уточнюється')

def _normalize_content(body:dict, base:Optional[dict]=None):
    x=dict(base or {})
    allowed=['name','official_name','brand','manufacturer','country','category_id','product_type','form','npk','active_ingredient','concentration','manufacturer_use','application','rate','restrictions','target','waiting_period','hazard_class','registration','short_description']
    for k in allowed:
        if k in body: x[k]=body.get(k) or ''
    for k in ['composition','cultures','purposes','factory_packs','gallery']:
        if k in body: x[k]=_split_lines(body.get(k))
    if 'image' in body:
        im=body.get('image') or ''
        x['image']={'local':im,'status':'cms-upload'} if isinstance(im,str) else im
    if 'source_title' in body or 'source_url' in body:
        src=dict(x.get('source') or {}); src['title']=body.get('source_title',src.get('title','')); src['url']=body.get('source_url',src.get('url','')); x['source']=src
    if 'verified' in body:
        ver=dict(x.get('verification') or {}); ver['verified']=bool(body.get('verified')); ver['status']='verified-primary-source' if ver['verified'] else 'cms-unverified'; x['verification']=ver
    x.setdefault('name',x.get('official_name') or 'Новий товар'); x.setdefault('official_name',x['name'])
    x.setdefault('brand',''); x.setdefault('category_id','nutrition'); x.setdefault('composition',[]); x.setdefault('cultures',[]); x.setdefault('purposes',[]); x.setdefault('factory_packs',[]); x.setdefault('gallery',[])
    return x

def public_content():
    d, static_products, static_skus=_static(); ov=_overrides(); products=[]
    for pid,c in ov.items():
        if pid in static_products:
            if not c.get('cms_published'):
                products.append({'id':pid,'runtime_hidden':True,'runtime_override':True})
                continue
            merged=dict(static_products[pid]); merged.update({k:v for k,v in c.items() if not k.startswith('cms_')}); merged['runtime_override']=True; merged['runtime_hidden']=False
        else:
            if not c.get('cms_published'): continue
            merged={k:v for k,v in c.items() if not k.startswith('cms_')}; merged['id']=pid; merged['runtime_dynamic']=True; merged['runtime_hidden']=False; merged['selected_by_bb610']=True; merged['legacy_url']='product.html?id='+pid; merged['canonical_product_url']='product.html?id='+pid
        products.append(merged)
    return {'products':products,'skus':_dynamic_skus()}

def admin_list_products():
    d, static_products, static_skus=_static(); ov=_overrides(); ids=list(static_products)
    ids.extend([x for x in ov if x not in static_products]); out=[]
    for pid in ids:
        p=dict(static_products.get(pid,{})); c=ov.get(pid)
        if c: p.update({k:v for k,v in c.items() if not k.startswith('cms_')})
        skus=[s for s in static_skus.values() if s.get('product_id')==pid]+_dynamic_skus(pid)
        out.append({'id':pid,'slug':p.get('slug',pid),'name':p.get('name',pid),'brand':p.get('brand',''),'category_id':p.get('category_id',''),
                    'image':(p.get('image') or {}).get('local') if isinstance(p.get('image'),dict) else p.get('image'),'published':bool(c.get('cms_published')) if c else True,
                    'source':'cms' if pid not in static_products else ('override' if c else 'static'),'sku_count':len(skus),'updated_at':c.get('cms_updated_at') if c else None})
    return out

def admin_detail(product_id:str):
    d, static_products, static_skus=_static(); ov=_overrides();
    if product_id not in static_products and product_id not in ov: return None
    p=dict(static_products.get(product_id,{})); c=ov.get(product_id)
    if c: p.update({k:v for k,v in c.items() if not k.startswith('cms_')})
    p['id']=product_id; p['published']=bool(c.get('cms_published')) if c else True; p['cms_source']='cms' if product_id not in static_products else ('override' if c else 'static')
    p['skus']=[s for s in static_skus.values() if s.get('product_id')==product_id]+_dynamic_skus(product_id)
    return p

def save_product(product_id:str, body:dict, *, create=False):
    d, static_products,_=_static(); ov=_overrides(); existing=admin_detail(product_id)
    if create and existing: raise ValueError('Product ID already exists')
    if not create and not existing: return None
    base=existing or {}
    content=_normalize_content(body,base)
    slug=_slug(body.get('slug') or content.get('slug') or product_id); content['slug']=slug; content['id']=product_id
    published=1 if body.get('published',base.get('published',False)) else 0
    now=_now()
    with connect() as con:
        con.execute('INSERT INTO product_content(product_id,slug,content_json,published,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET slug=excluded.slug,content_json=excluded.content_json,published=excluded.published,updated_at=excluded.updated_at',
                    (product_id,slug,json.dumps(content,ensure_ascii=False),published,now,now)); con.commit()
    return admin_detail(product_id)

def create_product(body:dict):
    pid=_slug(body.get('id') or body.get('slug') or body.get('name'))
    p=save_product(pid,body,create=True)
    initial=body.get('initial_sku')
    if initial and initial.get('sku'): create_sku(pid,initial)
    return admin_detail(pid)

def create_sku(product_id:str, body:dict):
    if not admin_detail(product_id): raise ValueError('Product not found')
    sku=(body.get('sku') or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9._-]{3,128}',sku): raise ValueError('Invalid SKU')
    d,_,ss=_static()
    with connect() as con:
        if sku in ss or con.execute('SELECT 1 FROM dynamic_skus WHERE sku=?',(sku,)).fetchone(): raise ValueError('SKU already exists')
        con.execute('INSERT INTO dynamic_skus(sku,product_id,variant,volume_value,volume_unit,image,currency,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (sku,product_id,body.get('variant') or '1 шт',body.get('volume_value'),body.get('volume_unit') or 'pcs',body.get('image'),body.get('currency') or 'UAH',_now(),_now()))
        con.execute('INSERT INTO sku_commerce(sku,price,sale_price,availability,stock_qty,enabled,updated_at) VALUES(?,?,?,?,?,?,?)',
                    (sku,body.get('price'),body.get('sale_price'),body.get('availability') or 'unknown',body.get('stock_qty'),1 if body.get('enabled') else 0,_now())); con.commit()
    # First runtime SKU becomes the default SKU when the product has none.
    detail=admin_detail(product_id) or {}
    if not detail.get('default_sku_id'):
        save_product(product_id,{'name':detail.get('name') or product_id,'default_sku_id':sku,'published':detail.get('published',False)},create=False)
        # save_product only accepts curated fields, so persist default_sku_id explicitly below.
        with connect() as con:
            row=con.execute('SELECT content_json FROM product_content WHERE product_id=?',(product_id,)).fetchone()
            if row:
                c=json.loads(row['content_json']); c['default_sku_id']=sku
                con.execute('UPDATE product_content SET content_json=?,updated_at=? WHERE product_id=?',(json.dumps(c,ensure_ascii=False),_now(),product_id)); con.commit()
    return _dynamic_skus(product_id)[-1]

def save_upload(filename:str, content:bytes)->str:
    ext=Path(filename or '').suffix.lower()
    if ext not in {'.jpg','.jpeg','.png','.webp'}: raise ValueError('Only JPG, PNG and WEBP images are allowed')
    if len(content)>8*1024*1024: raise ValueError('Image is larger than 8 MB')
    name=uuid.uuid4().hex+ext; (MEDIA_DIR/name).write_bytes(content)
    return '/media/products/'+name
