#!/usr/bin/env python3
from __future__ import annotations
import html,json,re,urllib.request
from pathlib import Path
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
SITE='https://market.bb610.com.ua'
API_BASE='https://api.market.bb610.com.ua'
API=API_BASE+'/api/v1/catalog/v5'
SELLABLE={'in_stock','out_of_stock','preorder','backorder'}

def text(v): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',str(v or '')))).strip()
def esc(v): return html.escape(str(v or ''),quote=True)

def pack_token(v):
    s=text(v).lower().replace(',','.')
    for a,b in (('мл','ml'),('кг','kg'),('шт.','pcs'),('шт','pcs'),('л','l'),('г','g')):
        s=s.replace(a,b)
    s=re.sub(r'\s+','',s)
    s=re.sub(r'[^a-z0-9.]+','-',s).replace('.','-')
    return re.sub(r'-+','-',s).strip('-')

def price(s):
    v=s.get('sale_price')
    if v is None:v=s.get('price')
    try:v=float(v)
    except Exception:return None
    return v if v>0 else None

def is_saleable(s):
    return bool(s.get('commerce_enabled')) and price(s) is not None and text(s.get('availability')) in SELLABLE

def sku_group_id(p,s):
    attrs=s.get('attributes') if isinstance(s.get('attributes'),dict) else {}
    lowered={str(k).strip().casefold():v for k,v in attrs.items()}
    for key in ('item_group_id','related_group_id'):
        value=text(lowered.get(key))
        if value:return value
    return text(p.get('product_id'))

def grouped_saleable_variants(p,s):
    gid=sku_group_id(p,s)
    rows=[x for x in (p.get('skus') or []) if is_saleable(x) and sku_group_id(p,x)==gid]
    return gid,rows

def image_url(p,s):
    rows=(s.get('media') or [])+(p.get('media') or [])
    m=next((x for x in rows if x.get('is_primary') and x.get('path')),None) or next((x for x in rows if x.get('path')),None)
    path=text((m or {}).get('path'))
    if not path:return ''
    if path.startswith(('http://','https://')):return path
    if path.startswith(('/media/','media/')):return API_BASE+'/'+path.lstrip('/')
    return SITE+'/'+path.lstrip('/')

def route(p,s):
    slug=text(p.get('slug') or p.get('product_id'))
    pt=pack_token(s.get('package_label'))
    return f'/products/{slug}-{pt or text(s.get("sku_id"))[-12:].lower()}/'

def availability(v):
    return {'in_stock':'https://schema.org/InStock','out_of_stock':'https://schema.org/OutOfStock','preorder':'https://schema.org/PreOrder','backorder':'https://schema.org/BackOrder'}[v]

def stock(v):
    return {'in_stock':'В наявності','out_of_stock':'Немає в наявності','preorder':'Передзамовлення','backorder':'Під замовлення'}[v]

def money(v):
    return (f'{int(v):,}'.replace(',',' ') if float(v).is_integer() else f'{v:,.2f}'.replace(',',' ').replace('.',','))+' грн'

def replace_div(body,class_name,value):
    pat=re.compile(rf'(<div\s+class="{re.escape(class_name)}">).*?(</div>)',re.I|re.S)
    return pat.sub(lambda m:m.group(1)+value+m.group(2),body,count=1)

def patch_product_schema(body,mutator):
    pat=re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',re.I|re.S)
    found=False
    def repl(m):
        nonlocal found
        try:o=json.loads(m.group(1))
        except Exception:return m.group(0)
        if found or o.get('@type')!='Product':return m.group(0)
        found=True
        mutator(o)
        return '<script type="application/ld+json">'+json.dumps(o,ensure_ascii=False,separators=(',',':'))+'</script>'
    out=pat.sub(repl,body)
    if not found:raise RuntimeError('Product JSON-LD not found')
    return out

def family_patch(body,p):
    active=[s for s in (p.get('skus') or []) if is_saleable(s)]
    prices=[price(s) for s in active]
    if prices:
        low=min(prices); high=max(prices)
        label=money(low) if low==high else 'від '+money(low)
        body=replace_div(body,'price',esc(label))
        states={text(s.get('availability')) for s in active}
        if 'in_stock' in states:stock_label='В наявності'
        elif states & {'preorder','backorder'}:stock_label='Під замовлення'
        elif states=={'out_of_stock'}:stock_label='Немає в наявності'
        else:stock_label='Наявність уточнюється'
        body=replace_div(body,'stock',esc(stock_label))
    else:
        body=replace_div(body,'price','Ціна уточнюється')
        body=replace_div(body,'stock','Наявність уточнюється')

    def mutate(o):
        o['url']=SITE+'/products/'+text(p.get('slug') or p.get('product_id'))+'/'
        if prices:
            o['offers']={
                '@type':'AggregateOffer',
                'priceCurrency':text(active[0].get('currency') or 'UAH'),
                'lowPrice':f'{min(prices):g}',
                'highPrice':f'{max(prices):g}',
                'offerCount':len(active),
                'url':o['url'],
            }
        else:o.pop('offers',None)
    return patch_product_schema(body,mutate)

def family_assert(body,p):
    active=[s for s in (p.get('skus') or []) if is_saleable(s)]
    schemas=[]
    for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',body,re.I|re.S):
        try:schemas.append(json.loads(raw))
        except Exception:pass
    product=next((x for x in schemas if x.get('@type')=='Product'),None)
    if not product:raise RuntimeError('family Product JSON-LD missing')
    offer=product.get('offers')
    if active:
        if not offer or offer.get('@type')!='AggregateOffer':raise RuntimeError('family AggregateOffer missing')
        expected=[price(s) for s in active]
        if float(offer.get('lowPrice'))!=min(expected):raise RuntimeError('family lowPrice mismatch')
        if float(offer.get('highPrice'))!=max(expected):raise RuntimeError('family highPrice mismatch')
        if int(offer.get('offerCount'))!=len(active):raise RuntimeError('family offerCount mismatch')
        if 'Ціна уточнюється' in body:raise RuntimeError('family visible price stale')
    else:
        if offer:raise RuntimeError('lead-gen family must not expose Offer')

def fetch():
    req=urllib.request.Request(API,headers={'User-Agent':'BB610-AI-Sales/1.0'})
    with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)

def page(template,p,s):
    sid=text(s.get('sku_id')); pkg=text(s.get('package_label')); av=text(s.get('availability')); pr=price(s)
    url=SITE+route(p,s); img=image_url(p,s)
    name=text(p.get('name')); brand=text(p.get('brand')); manufacturer=text(p.get('manufacturer') or p.get('manufacturer_title'))
    desc=text(p.get('seo_description') or p.get('short_description') or p.get('description') or p.get('application'))
    title=f'{text(p.get("seo_title") or name)} {pkg} | BB610 Market'
    attrs=s.get('attributes') if isinstance(s.get('attributes'),dict) else {}
    schema={'@context':'https://schema.org','@type':'Product','name':f'{name} {pkg}'.strip(),'description':desc,'url':url,'sku':sid,'image':[img] if img else [],'brand':{'@type':'Brand','name':brand},'offers':{'@type':'Offer','url':url,'priceCurrency':'UAH','price':f'{pr:g}','availability':availability(av),'itemCondition':'https://schema.org/NewCondition'}}
    if manufacturer:schema['manufacturer']={'@type':'Organization','name':manufacturer}
    gid,group_rows=grouped_saleable_variants(p,s)
    group_schema=None
    if gid and len(group_rows)>1:
        slug=text(p.get('slug') or p.get('product_id'))
        group_anchor=f'{SITE}/products/{slug}/#product-group'
        schema['size']=pkg
        schema['inProductGroupWithID']=gid
        schema['isVariantOf']={'@type':'ProductGroup','@id':group_anchor}
        group_schema={
            '@context':'https://schema.org',
            '@type':'ProductGroup',
            '@id':group_anchor,
            'name':name,
            'description':desc,
            'brand':{'@type':'Brand','name':brand},
            'productGroupID':gid,
            'variesBy':['https://schema.org/size'],
            'hasVariant':[
                {'@type':'Product','url':SITE+route(p,row)}
                for row in group_rows
            ],
        }
        if manufacturer:
            group_schema['manufacturer']={'@type':'Organization','name':manufacturer}
    gtin=text(attrs.get('gtin_ean') or attrs.get('gtin') or attrs.get('ean') or attrs.get('barcode'))
    if gtin:schema['gtin']=gtin
    if s.get('manufacturer_sku'):schema['mpn']=text(s.get('manufacturer_sku'))

    t=template
    t=re.sub(r'<base href="[^"]*">','',t,count=1)
    t=t.replace('<head>','<head><base href="../../">',1)
    t=re.sub(r'<title>.*?</title>',f'<title>{esc(title)}</title>',t,count=1,flags=re.S|re.I)
    for pat in (r'<meta name="description"[^>]*>',r'<link rel="canonical"[^>]*>',r'<meta name="robots"[^>]*>',r'<meta property="og:[^"]+"[^>]*>',r'<script type="application/ld\+json">.*?</script>'):
        t=re.sub(pat,'',t,flags=re.S|re.I)
    schema_html='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False,separators=(',',':'))+'</script>'
    if group_schema:
        schema_html+='<script type="application/ld+json">'+json.dumps(group_schema,ensure_ascii=False,separators=(',',':'))+'</script>'
    meta=f'<meta name="description" content="{esc(desc[:300])}"><link rel="canonical" href="{esc(url)}"><meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:type" content="product"><meta property="og:title" content="{esc(title)}"><meta property="og:url" content="{esc(url)}">'+(f'<meta property="og:image" content="{esc(img)}">' if img else '')+schema_html
    t=t.replace('</title>','</title>'+meta,1)
    static=f'<div class="product-layout seo-static-product"><div class="product-gallery"><img src="{esc(img)}" alt="{esc(name)}" width="900" height="900"></div><div class="product-summary"><h1>{esc(name)}</h1><div class="brand">{esc(brand)}</div><div class="selected-variant">{esc(pkg)}</div><div class="price">{esc(money(pr))}</div><div class="stock">{esc(stock(av))}</div><div class="verified-line">✓ <b>BB610 VERIFIED</b><small>Product Master V5</small></div><p>{esc(desc)}</p></div></div>'
    t=t.replace('<div class="container" id="product-root"></div>',f'<div class="container" id="product-root">{static}</div>',1)
    t=re.sub(r'<script>window\.BB610_PRODUCT_ID=.*?</script>','',t,count=1,flags=re.S)
    globals=f'<script>window.BB610_PRODUCT_ID={json.dumps(p.get("product_id"),ensure_ascii=False)};window.BB610_SKU_ID={json.dumps(sid,ensure_ascii=False)};</script>'
    t=t.replace('<script src="data/catalog.runtime.js"></script>',globals+'<script src="data/catalog.runtime.js"></script>',1)
    return t,url

def main():
    data=fetch(); template=(ROOT/'product.html').read_text(encoding='utf-8')
    made=[]; changed_urls=set(); errors=[]
    for p in data.get('products') or []:
        for s in p.get('skus') or []:
            if not is_saleable(s):continue
            try:
                body,url=page(template,p,s); out=ROOT/route(p,s).lstrip('/')/'index.html'
                out.parent.mkdir(parents=True,exist_ok=True)
                previous=out.read_text(encoding='utf-8') if out.is_file() else None
                if previous!=body:
                    out.write_text(body,encoding='utf-8')
                    changed_urls.add(url)
                made.append({'sku_id':s.get('sku_id'),'url':url,'price':price(s),'availability':s.get('availability')})
            except Exception as e:errors.append({'sku_id':s.get('sku_id'),'error':str(e)})
    family_total=0; family_changed=0; family_errors=[]
    for p in data.get('products') or []:
        slug=text(p.get('slug') or p.get('product_id'))
        if not slug:continue
        fp=ROOT/'products'/slug/'index.html'
        if not fp.is_file():continue
        family_total+=1
        try:
            original=fp.read_text(encoding='utf-8')
            updated=family_patch(original,p)
            family_assert(updated,p)
            if updated!=original:
                fp.write_text(updated,encoding='utf-8')
                family_changed+=1
        except Exception as e:
            family_errors.append({'product_id':p.get('product_id'),'slug':slug,'error':str(e)})
    errors.extend(family_errors)

    sitemap=ROOT/'sitemap.xml'; sitemap_text=sitemap.read_text(encoding='utf-8')
    old_blocks=re.findall(r'<url>\s*<loc>(.*?)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?\s*</url>',sitemap_text,re.S)
    old=[u for u,_ in old_blocks]
    old_lastmod={u:lm.strip() for u,lm in old_blocks if lm.strip()}
    core=[SITE+'/',SITE+'/catalog.html',SITE+'/about.html',SITE+'/contacts.html',SITE+'/delivery.html',SITE+'/payment.html',SITE+'/returns.html',SITE+'/guides/master-13-40-13-vs-20-20-20/',SITE+'/guides/plantafol-20-20-20-vs-master-20-20-20/']
    urls=list(dict.fromkeys(core+old+[x['url'] for x in made]))
    today=date.today().isoformat()
    sitemap_rows=[]
    for u in urls:
        lm=today if u in changed_urls else old_lastmod.get(u,'')
        suffix=f'<lastmod>{esc(lm)}</lastmod>' if lm else ''
        sitemap_rows.append(f'  <url><loc>{esc(u)}</loc>{suffix}</url>\n')
    sitemap.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(sitemap_rows)+'</urlset>\n',encoding='utf-8')
    report={'status':'PASS' if not errors else 'FAIL','generated':len(made),'pages_changed':len(changed_urls),'family_pages_checked':family_total,'family_pages_changed':family_changed,'errors':errors,'items':made}
    rp=ROOT/'docs/ai_sales/AI_SALES_STAGE1_PDP_SYNC_REPORT.json';rp.parent.mkdir(parents=True,exist_ok=True);rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'generated':len(made),'pages_changed':len(changed_urls),'family_pages_checked':family_total,'family_pages_changed':family_changed,'errors':len(errors),'error_details':errors[:50]},ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
