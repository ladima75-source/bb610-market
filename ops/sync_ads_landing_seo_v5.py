#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE='https://market.bb610.com.ua'
API='https://api.market.bb610.com.ua/api/v1/catalog/v5'
ROUTES={
 'kendal':'kendal',
 'plantafol-npk-10-54-10':'plantafol-10-54-10',
 'plantafol-npk-5-15-45':'plantafol-5-15-45',
 'brexil-mix':'brexil-mix',
 'pekacid-npk-0-60-20':'pekacid-0-60-20',
 'master-npk-20-20-20':'master-20-20-20',
 'viva':'viva',
 'master-npk-13-40-13':'master-13-40-13',
 'plantafol-npk-20-20-20':'plantafol-20-20-20',
 'megafol':'megafol',
 'radifarm':'radifarm',
 'kendal-te':'kendal-te',
}

def fetch():
    req=urllib.request.Request(API,headers={'User-Agent':'BB610-SEO-Sync/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)

def plain(v):
    s=re.sub(r'<[^>]+>',' ',str(v or ''))
    return re.sub(r'\s+',' ',html.unescape(s)).strip()

def trim_words(text,limit):
    text=plain(text)
    if len(text)<=limit:return text
    cut=text[:limit+1]
    if ' ' in cut:cut=cut.rsplit(' ',1)[0]
    return cut.rstrip(' ,;:—–-|')

def compact_name(p):
    raw=plain(p.get('seo_title') or p.get('name'))
    core=re.split(r'\s+[—–]\s+|,\s*',raw,maxsplit=1)[0].strip()
    brand=plain(p.get('brand'))
    if brand and brand.casefold() not in core.casefold():
        candidate=f'{core} {brand}'
        if len(candidate)<=46:core=candidate
    return trim_words(core,46)

def title_for(p):
    return f'{compact_name(p)} | BB610 Market'

def desc_for(p):
    d=plain(p.get('seo_description') or p.get('short_description') or p.get('description') or p.get('manufacturer_use'))
    if not d:
        d=f'{compact_name(p)}. Характеристики, фасування, актуальна ціна та доставка по Україні у BB610 Market.'
    elif compact_name(p).casefold() not in d[:80].casefold():
        d=f'{compact_name(p)}. {d}'
    return trim_words(d,160)

def abs_url(path):
    path=str(path or '').strip()
    if not path:return ''
    if path.startswith(('http://','https://')):return path
    return SITE+'/'+path.lstrip('/')

def product_images(p):
    out=[]
    for m in p.get('media') or []:
        u=abs_url(m.get('path') or m.get('url'))
        if u and u not in out:out.append(u)
    if not out:
        for s in p.get('skus') or []:
            for m in s.get('media') or []:
                u=abs_url(m.get('path') or m.get('url'))
                if u and u not in out:out.append(u)
    return out[:8]

def active_skus(p):
    return [s for s in (p.get('skus') or [])
            if s.get('commerce_enabled') in (1,True)
            and s.get('price') is not None
            and s.get('availability') not in (None,'unknown')]

def aggregate_offer(p,url):
    rows=active_skus(p)
    if not rows:return None
    prices=[float(s['price']) for s in rows]
    currencies=[str(s.get('currency') or 'UAH') for s in rows]
    currency=currencies[0] if len(set(currencies))==1 else 'UAH'
    return {'@type':'AggregateOffer','priceCurrency':currency,
            'lowPrice':f'{min(prices):g}','highPrice':f'{max(prices):g}',
            'offerCount':len(prices),'url':url}

def replace_meta(text,selector,value,attr='name'):
    patt=rf'<meta(?=[^>]*\b{attr}=["\']{re.escape(selector)}["\'])[^>]*>'
    tag=f'<meta {attr}="{html.escape(selector,quote=True)}" content="{html.escape(value,quote=True)}">'
    if re.search(patt,text,re.I):
        return re.sub(patt,tag,text,count=1,flags=re.I)
    return text.replace('</head>',tag+'</head>',1)

def patch_product_schema(text,p,url,desc,images):
    pat=re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',re.I|re.S)
    found=False
    def repl(m):
        nonlocal found
        raw=m.group(1)
        try:obj=json.loads(raw)
        except Exception:return m.group(0)
        if found or obj.get('@type')!='Product':return m.group(0)
        found=True
        obj.update({
          '@context':'https://schema.org','@type':'Product',
          'name':plain(p.get('name')),'description':desc,'url':url,
          'image':images or obj.get('image') or [],
          'brand':{'@type':'Brand','name':plain(p.get('brand'))} if p.get('brand') else obj.get('brand'),
          'manufacturer':{'@type':'Organization','name':plain(p.get('manufacturer'))} if p.get('manufacturer') else obj.get('manufacturer'),
        })
        offer=aggregate_offer(p,url)
        if offer:obj['offers']=offer
        elif 'offers' in obj:obj.pop('offers',None)
        return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'</script>'
    text=pat.sub(repl,text)
    if not found:raise RuntimeError('Product JSON-LD not found')
    return text

def main():
    data=fetch()
    products={p.get('product_id'):p for p in data.get('products') or []}
    report=[]
    for pid,slug in ROUTES.items():
        p=products.get(pid)
        if not p:raise RuntimeError(f'missing V5 product: {pid}')
        path=ROOT/'products'/slug/'index.html'
        text=path.read_text(encoding='utf-8')
        title=title_for(p);desc=desc_for(p);url=f'{SITE}/products/{slug}/';images=product_images(p)
        text=re.sub(r'<title>.*?</title>',f'<title>{html.escape(title)}</title>',text,count=1,flags=re.I|re.S)
        text=replace_meta(text,'description',desc)
        text=replace_meta(text,'og:title',title,'property')
        text=replace_meta(text,'og:description',desc,'property')
        text=replace_meta(text,'og:url',url,'property')
        if images:text=replace_meta(text,'og:image',images[0],'property')
        text=replace_meta(text,'twitter:title',title)
        text=replace_meta(text,'twitter:description',desc)
        if images:text=replace_meta(text,'twitter:image',images[0])
        text=patch_product_schema(text,p,url,desc,images)
        path.write_text(text,encoding='utf-8')
        report.append({'id':pid,'slug':slug,'title_len':len(title),'description_len':len(desc),
                       'images':len(images),'active_skus':len(active_skus(p)),
                       'has_aggregate_offer':bool(aggregate_offer(p,url))})
    print(json.dumps({'status':'PASS','products':report},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
