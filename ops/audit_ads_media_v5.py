#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, urllib.request
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
API='https://api.market.bb610.com.ua/api/v1/catalog/v5'
SITE='https://market.bb610.com.ua'
OUT=ROOT/'ops'/'reports'/'ads-media-audit.json'
PRODUCTS=[
 'kendal','plantafol-npk-10-54-10','plantafol-npk-5-15-45','brexil-mix',
 'pekacid-npk-0-60-20','master-npk-20-20-20','viva','master-npk-13-40-13',
 'plantafol-npk-20-20-20','megafol','radifarm','kendal-te'
]

def fetch_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'BB610-Ads-Media-Audit/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)

def abs_url(v):
    v=str(v or '').strip()
    if not v:return ''
    if v.startswith(('http://','https://')):return v
    return SITE+'/'+v.lstrip('/')

def package_label(s):
    for k in ('variant','package','package_label','label','display_name'):
        if s.get(k):return str(s[k]).strip()
    vw=s.get('volume_weight')
    if isinstance(vw,dict) and vw.get('value') is not None:
        return (str(vw.get('value'))+' '+str(vw.get('unit') or '')).strip()
    if s.get('package_value') is not None:
        return (str(s.get('package_value'))+' '+str(s.get('package_unit') or '')).strip()
    return ''

def media_url(m):
    return abs_url(m.get('path') or m.get('url') or m.get('src'))

def inspect_image(url):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'BB610-Ads-Media-Audit/1.0'})
        with urllib.request.urlopen(req,timeout=30) as r:
            body=r.read(20*1024*1024)
            ctype=r.headers.get('Content-Type','')
        with Image.open(io.BytesIO(body)) as im:
            width,height=im.size
            fmt=im.format
        return {
            'ok':True,'width':width,'height':height,'bytes':len(body),
            'format':fmt,'content_type':ctype,'sha256':hashlib.sha256(body).hexdigest()
        }
    except Exception as e:
        return {'ok':False,'error':str(e)}

def compact_media(m,scope,sku_id=None,package=None):
    url=media_url(m)
    return {
        'scope':scope,'sku_id':sku_id,'package':package,'url':url,
        'alt':m.get('alt'),'kind':m.get('kind'),'source_kind':m.get('source_kind'),
        'binding_kind':m.get('binding_kind'),'role':m.get('role'),
        'is_primary':m.get('is_primary')
    }

def main():
    data=fetch_json(API)
    by_id={p.get('product_id'):p for p in (data.get('products') or [])}
    result={'generated_from':API,'products':[]}
    for pid in PRODUCTS:
        p=by_id.get(pid)
        if not p:
            result['products'].append({'product_id':pid,'error':'missing product'})
            continue
        rows=[]
        for m in p.get('media') or []:
            rows.append(compact_media(m,'product'))
        sku_coverage=[]
        for s in p.get('skus') or []:
            sid=str(s.get('sku_id') or s.get('id') or s.get('sku') or '')
            pack=package_label(s)
            sm=s.get('media') or []
            sku_coverage.append({
                'sku_id':sid,'package':pack,'commerce_enabled':s.get('commerce_enabled'),
                'availability':s.get('availability'),'price':s.get('price'),'media_count':len(sm)
            })
            for m in sm:
                rows.append(compact_media(m,'sku',sid,pack))
        unique={}
        for m in rows:
            if not m['url']:continue
            unique.setdefault(m['url'],m)
        for m in unique.values():
            m['image']=inspect_image(m['url'])
        hashes={}
        for m in unique.values():
            h=(m.get('image') or {}).get('sha256')
            if h:hashes.setdefault(h,[]).append(m['url'])
        duplicate_groups=[urls for urls in hashes.values() if len(urls)>1]
        sources=p.get('sources') or []
        videos=[s for s in sources if 'youtu' in str(s.get('source_url') or '').lower() or 'video' in str(s.get('source_type') or '').lower()]
        small=[]
        broken=[]
        for m in unique.values():
            im=m.get('image') or {}
            if not im.get('ok'):broken.append(m['url']);continue
            if min(im.get('width',0),im.get('height',0))<600:
                small.append({'url':m['url'],'width':im.get('width'),'height':im.get('height')})
        result['products'].append({
            'product_id':pid,'name':p.get('name'),'brand':p.get('brand'),
            'product_media_count':len(p.get('media') or []),
            'unique_media_count':len(unique),
            'media':list(unique.values()),
            'sku_media_coverage':sku_coverage,
            'sources':sources,
            'video_sources':videos,
            'duplicate_content_groups':duplicate_groups,
            'small_under_600px':small,
            'broken_media':broken
        })
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({
        'status':'PASS',
        'products':[
            {
                'id':p.get('product_id'),
                'media':p.get('unique_media_count'),
                'small':len(p.get('small_under_600px') or []),
                'broken':len(p.get('broken_media') or []),
                'videos':len(p.get('video_sources') or [])
            } for p in result['products']
        ]
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
