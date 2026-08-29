#!/usr/bin/env python3
import json, pathlib, csv, io, html, shutil
from urllib.parse import urljoin

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
master=json.loads((DATA/'catalog.master.json').read_text(encoding='utf-8'))
SITE=master.get('site',{}).get('base_url','https://market.bb610.com.ua').rstrip('/')

# ---------- validation ----------
def unique(rows,key,label):
    vals=[r.get(key) for r in rows]
    if None in vals or '' in vals: raise SystemExit(f'{label}: empty {key}')
    dup={x for x in vals if vals.count(x)>1}
    if dup: raise SystemExit(f'{label}: duplicate {key}: {sorted(dup)}')

unique(master['products'],'id','products')
unique(master['variants'],'id','variants')
unique(master['skus'],'id','skus')
unique(master['categories'],'id','categories')

pids={p['id'] for p in master['products']}; vids={v['id'] for v in master['variants']}; sids={s['id'] for s in master['skus']}; cids={c['id'] for c in master['categories']}
prod={p['id']:p for p in master['products']}; cats={c['id']:c for c in master['categories']}
for p in master['products']:
    if p['category_id'] not in cids: raise SystemExit(f"product {p['id']}: unknown category {p['category_id']}")
    if p.get('default_sku_id') and p['default_sku_id'] not in sids: raise SystemExit(f"product {p['id']}: unknown default_sku_id")
for v in master['variants']:
    if v['product_id'] not in pids: raise SystemExit(f"variant {v['id']}: unknown product_id")
for sku in master['skus']:
    if sku['product_id'] not in pids: raise SystemExit(f"sku {sku['id']}: unknown product_id")
    if sku['variant_id'] not in vids: raise SystemExit(f"sku {sku['id']}: unknown variant_id")
    variant=next(v for v in master['variants'] if v['id']==sku['variant_id'])
    if variant['product_id'] != sku['product_id']: raise SystemExit(f"sku {sku['id']}: variant belongs to another product")
    if sku.get('commercial_status') not in ('not-configured','configured','active','paused'): raise SystemExit(f"sku {sku['id']}: invalid commercial_status")
    if sku.get('sku') != sku['id']: raise SystemExit(f"sku {sku['id']}: sku/id mismatch; item identity must be stable")
    if not sku.get('url','').startswith('/products/') or not sku['url'].endswith('/'):
        raise SystemExit(f"sku {sku['id']}: permanent URL must be /products/<slug>/")
for b in master.get('bundles',[]):
    for item in b.get('items',[]):
        if item['sku_id'] not in sids: raise SystemExit(f"bundle {b.get('id')}: unknown sku {item['sku_id']}")

# ---------- runtime snapshot ----------
(DATA/'catalog.runtime.js').write_text('window.BB610_CATALOG = '+json.dumps(master,ensure_ascii=False,separators=(",",":"))+';',encoding='utf-8')
(DATA/'catalog.generated.json').write_text(json.dumps(master,ensure_ascii=False,indent=2),encoding='utf-8')

# ---------- helpers ----------
def abs_url(path):
    if not path: return ''
    if path.startswith('http://') or path.startswith('https://'): return path
    return SITE + '/' + path.lstrip('/')

def esc(x): return html.escape(str(x or ''), quote=True)

def description_for(p, sku=None):
    base=p.get('manufacturer_use') or p.get('product_type') or p.get('form') or ''
    text=f"{p['name']} — {base}".strip(' —')
    if sku: text=f"{p['name']} {sku.get('variant','')} — {base}".strip(' —')
    return text[:300]

def title_for(p,sku=None):
    return f"{p['name']} {sku.get('variant','')} · BB610 Market" if sku else f"{p['name']} · BB610 Market"

def product_image(p,sku=None):
    return (sku or {}).get('image') or p.get('image',{}).get('local') or ''

def sku_indexable(s):
    return s.get('commercial_status')=='active' and s.get('offer_status')=='active' and s.get('price') is not None and s.get('availability') not in (None,'unknown')

def feed_eligible(s):
    return sku_indexable(s) and bool(s.get('feed_eligible'))

def availability_schema(v):
    m={'in_stock':'https://schema.org/InStock','out_of_stock':'https://schema.org/OutOfStock','preorder':'https://schema.org/PreOrder','backorder':'https://schema.org/BackOrder'}
    return m.get(v)

def availability_feed(v):
    m={'in_stock':'in_stock','out_of_stock':'out_of_stock','preorder':'preorder','backorder':'backorder'}
    return m.get(v,'')

def product_schema(p, page_url, sku=None):
    obj={
        '@context':'https://schema.org',
        '@type':'Product',
        'name': p['name'] + (f" {sku.get('variant','')}" if sku else ''),
        'description': description_for(p,sku),
        'image':[abs_url(product_image(p,sku))],
        'brand':{'@type':'Brand','name':p.get('brand','')},
        'manufacturer':{'@type':'Organization','name':p.get('manufacturer','')},
        'category':cats[p['category_id']]['name'],
        'url':page_url,
    }
    if sku:
        obj['sku']=sku['id']
        if sku.get('gtin_ean'): obj['gtin']=sku['gtin_ean']
        if sku.get('mpn'): obj['mpn']=sku['mpn']
        if sku_indexable(sku):
            av=availability_schema(sku.get('availability'))
            offer={'@type':'Offer','url':page_url,'priceCurrency':sku.get('currency','UAH'),'price':str(sku['price']),'itemCondition':'https://schema.org/NewCondition'}
            if av: offer['availability']=av
            obj['offers']=offer
    return obj

def breadcrumb_schema(p,page_url,sku=None):
    cat=cats[p['category_id']]
    items=[
      {'@type':'ListItem','position':1,'name':'BB610 Market','item':SITE+'/'},
      {'@type':'ListItem','position':2,'name':cat['name'],'item':SITE+'/categories/'+cat['slug']+'/'},
      {'@type':'ListItem','position':3,'name':p['name'],'item':SITE+'/products/'+p['slug']+'/'},
    ]
    if sku:
        items.append({'@type':'ListItem','position':4,'name':sku.get('variant') or sku['id'],'item':page_url})
    return {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':items}

def seo_head(p,page_url,sku=None,indexable=True):
    title=title_for(p,sku); desc=description_for(p,sku); img=abs_url(product_image(p,sku))
    robots='index,follow,max-image-preview:large' if indexable else 'noindex,follow'
    scripts=[product_schema(p,page_url,sku),breadcrumb_schema(p,page_url,sku)]
    return ''.join([
      f'<meta name="description" content="{esc(desc)}">',
      f'<link rel="canonical" href="{esc(page_url)}">',
      f'<meta name="robots" content="{robots}">',
      '<meta property="og:type" content="product">',
      f'<meta property="og:site_name" content="BB610 Market">',
      f'<meta property="og:title" content="{esc(title)}">',
      f'<meta property="og:description" content="{esc(desc)}">',
      f'<meta property="og:url" content="{esc(page_url)}">',
      f'<meta property="og:image" content="{esc(img)}">' if img else '',
      '<meta name="twitter:card" content="summary_large_image">',
      ''.join(f'<script type="application/ld+json">{json.dumps(s,ensure_ascii=False,separators=(",",":"))}</script>' for s in scripts)
    ])

# ---------- static product/SKU pages ----------
template=(ROOT/'product.html').read_text(encoding='utf-8')
# Strip legacy dynamic-page SEO tags before using product.html as a generator template.
template=template.replace('<meta name="robots" content="noindex,follow"><link rel="canonical" href="https://market.bb610.com.ua/catalog.html">','')
products_dir=ROOT/'products'
if products_dir.exists(): shutil.rmtree(products_dir)
products_dir.mkdir()


def static_product_html(p, sku=None):
    img = product_image(p, sku)
    variant = (sku or {}).get('variant', '')
    price = 'Ціна уточнюється' if (not sku or sku.get('price') is None) else f"{sku['price']} {sku.get('currency','UAH')}"
    stock = (sku or {}).get('stock_label') or 'Наявність уточнюється'
    verified = p.get('verification', {}).get('verified')
    verified_html = '<div class="verified-line">✓ <b>BB610 VERIFIED</b><small>Дані продукту звірено з первинним джерелом виробника</small></div>' if verified else ''
    return (
        f'<div class="breadcrumbs">BB610 MARKET / {esc(cats[p["category_id"]]["name"].upper())} / {esc(p["name"])}</div>'
        f'<div class="product-layout seo-static-product">'
        f'<div class="product-gallery"><img src="{esc(img)}" alt="{esc(p["name"])}" width="900" height="900"></div>'
        f'<div class="product-summary"><div class="eyebrow">{esc(cats[p["category_id"]]["name"])}</div>'
        f'<h1>{esc(p["name"])}</h1><div class="brand">{esc(p.get("brand",""))}</div>'
        f'<div class="selected-variant">{esc(variant)}</div><div class="price">{esc(price)}</div>'
        f'<div class="stock">{esc(stock)}</div>{verified_html}<p>{esc(p.get("manufacturer_use",""))}</p></div></div>'
    )

def render_product_page(p,sku=None):
    if sku:
        page_path=sku['url']
        page_url=SITE+page_path
        slug=page_path.strip('/').split('/')[-1]
        indexable=sku_indexable(sku)
    else:
        page_path=f"/products/{p['slug']}/"
        page_url=SITE+page_path
        slug=p['slug']
        indexable=True
    content=template
    content=content.replace('<head>','<head><base href="../../">',1)
    content=content.replace('<title>Товар · BB610 Market</title>',f'<title>{esc(title_for(p,sku))}</title>'+seo_head(p,page_url,sku,indexable),1)
    globals_js=f'<script>window.BB610_PRODUCT_ID={json.dumps(p["id"],ensure_ascii=False)};window.BB610_SKU_ID={json.dumps(sku["id"] if sku else None,ensure_ascii=False)};</script>'
    content=content.replace('<div class="container" id="product-root"></div>',f'<div class="container" id="product-root">{static_product_html(p,sku)}</div>',1)
    content=content.replace('<script src="data/catalog.runtime.js"></script>',globals_js+'<script src="data/catalog.runtime.js"></script>',1)
    out=products_dir/slug/'index.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(content,encoding='utf-8')

for p in master['products']:
    if p.get('internal_only'): continue
    render_product_page(p,None)
for s in master['skus']:
    if s.get('internal_only') or prod[s['product_id']].get('internal_only'): continue
    render_product_page(prod[s['product_id']],s)

# legacy dynamic product endpoint should never be indexed
legacy=ROOT/'product.html'
legacy_text=legacy.read_text(encoding='utf-8')
if 'name="robots"' not in legacy_text:
    legacy_text=legacy_text.replace('<title>Товар · BB610 Market</title>','<title>Товар · BB610 Market</title><meta name="robots" content="noindex,follow"><link rel="canonical" href="https://market.bb610.com.ua/catalog.html">',1)
legacy.write_text(legacy_text,encoding='utf-8')

# ---------- category pages ----------
cat_template=(ROOT/'catalog.html').read_text(encoding='utf-8')
# Category pages get their own canonical/meta; remove generic catalog SEO from template first.
cat_template=cat_template.replace('<meta name="description" content="Каталог BB610 Market: професійне живлення, біостимуляція, захист рослин та контейнери."><link rel="canonical" href="https://market.bb610.com.ua/catalog.html"><meta name="robots" content="index,follow,max-image-preview:large">','')
categories_dir=ROOT/'categories'
if categories_dir.exists(): shutil.rmtree(categories_dir)
categories_dir.mkdir()
for c in master['categories']:
    if not c.get('enabled'): continue
    url=SITE+'/categories/'+c['slug']+'/'
    title=c.get('seo',{}).get('title') or f"{c['name']} · BB610 Market"
    desc=c.get('seo',{}).get('description') or f"{c['name']} у BB610 Market"
    t=cat_template.replace('<head>','<head><base href="../../">',1)
    t=t.replace('<title>Каталог · BB610 Market</title>',f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}"><meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}">',1)
    t=t.replace('<h1>Каталог</h1>',f'<h1>{esc(c["name"])}</h1>',1)
    static_links=''.join(f'<article><a href="products/{esc(pp["slug"])}/index.html"><strong>{esc(pp["name"])}</strong></a><div>{esc(pp.get("brand",""))}</div></article>' for pp in master['products'] if pp['category_id']==c['id'])
    t=t.replace('<div id="catalog-grid" class="products-grid"></div>',f'<div id="catalog-grid" class="products-grid seo-static-list">{static_links}</div>',1)
    t=t.replace('<script src="data/catalog.runtime.js"></script>',f'<script>window.BB610_CATEGORY_ID={json.dumps(c["id"])};</script><script src="data/catalog.runtime.js"></script>',1)
    out=categories_dir/c['slug']/'index.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(t,encoding='utf-8')

# ---------- feeds ----------
feeds=ROOT/'feeds';feeds.mkdir(exist_ok=True)
eligible=[s for s in master['skus'] if feed_eligible(s)]
common_fields=['id','title','description','availability','condition','price','link','image_link','brand','gtin','mpn']
rows=[]
for s in eligible:
    p=prod[s['product_id']]
    rows.append({
      'id':s['id'],
      'title':(p['name']+' '+s.get('variant','')).strip(),
      'description':description_for(p,s),
      'availability':availability_feed(s.get('availability')),
      'condition':'new',
      'price':f"{s['price']} {s.get('currency','UAH')}",
      'link':SITE+s['url'],
      'image_link':abs_url(s.get('image') or p.get('image',{}).get('local')),
      'brand':p.get('brand',''),
      'gtin':s.get('gtin_ean') or '',
      'mpn':s.get('mpn') or ''
    })

def write_csv(path,fields,rows):
    buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=fields);w.writeheader();w.writerows(rows);path.write_text(buf.getvalue(),encoding='utf-8')
write_csv(feeds/'google-merchant.csv',common_fields,rows)
write_csv(feeds/'meta-catalog.csv',common_fields,rows)
# backwards-compatible template name
write_csv(feeds/'merchant-meta-template.csv',common_fields,rows)

status=[]
for s in master['skus']:
    reasons=[]
    if s.get('commercial_status')!='active': reasons.append('commercial_status_not_active')
    if s.get('offer_status')!='active': reasons.append('offer_status_not_active')
    if not s.get('feed_eligible'): reasons.append('feed_eligible_false')
    if s.get('price') is None: reasons.append('price_missing')
    if s.get('availability') in (None,'unknown'): reasons.append('availability_unknown')
    status.append({'sku':s['id'],'included':not reasons,'reasons':reasons})
(feeds/'feed-status.json').write_text(json.dumps({'generated_from':'data/catalog.master.json','base_url':SITE,'eligible_count':len(eligible),'items':status},ensure_ascii=False,indent=2),encoding='utf-8')

# ---------- sitemap / robots ----------
urls=[SITE+'/',SITE+'/catalog.html',SITE+'/about.html']
urls += [SITE+'/categories/'+c['slug']+'/' for c in master['categories'] if c.get('enabled')]
urls += [SITE+'/products/'+p['slug']+'/' for p in master['products'] if not p.get('internal_only')]
urls += [SITE+s['url'] for s in master['skus'] if sku_indexable(s) and not s.get('internal_only') and not prod[s['product_id']].get('internal_only')]
sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{esc(u)}</loc></url>\n' for u in urls)+'</urlset>\n'
(ROOT/'sitemap.xml').write_text(sitemap,encoding='utf-8')
(ROOT/'robots.txt').write_text(f'''User-agent: *\nAllow: /\nDisallow: /cart.html\nDisallow: /checkout.html\nDisallow: /compare.html\nDisallow: /favorites.html\nDisallow: /tools/\n\nSitemap: {SITE}/sitemap.xml\n''',encoding='utf-8')

# ---------- page-level SEO defaults ----------
def inject_once(path, needle, replacement):
    text=path.read_text(encoding='utf-8')
    if replacement not in text:
        text=text.replace(needle,replacement,1)
    path.write_text(text,encoding='utf-8')

# index canonical/OG
idx=ROOT/'index.html';tx=idx.read_text(encoding='utf-8')
if 'rel="canonical"' not in tx:
    tx=tx.replace('</title>','</title><link rel="canonical" href="https://market.bb610.com.ua/"><meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:type" content="website"><meta property="og:site_name" content="BB610 Market"><meta property="og:url" content="https://market.bb610.com.ua/"><meta property="og:title" content="BB610 Market · професійні товари для вирощування"><meta property="og:image" content="https://market.bb610.com.ua/assets/bb610-market-logo.png">',1)
idx.write_text(tx,encoding='utf-8')
# catalog canonical
catf=ROOT/'catalog.html';tx=catf.read_text(encoding='utf-8')
if 'rel="canonical"' not in tx:
    tx=tx.replace('</title>','</title><meta name="description" content="Каталог BB610 Market: професійне живлення, біостимуляція, захист рослин та контейнери."><link rel="canonical" href="https://market.bb610.com.ua/catalog.html"><meta name="robots" content="index,follow,max-image-preview:large">',1)
catf.write_text(tx,encoding='utf-8')
# transactional/utility pages noindex
for fn in ['cart.html','checkout.html','compare.html','favorites.html','404.html']:
    path=ROOT/fn;tx=path.read_text(encoding='utf-8')
    if 'name="robots"' not in tx:
        tx=tx.replace('</title>','</title><meta name="robots" content="noindex,nofollow">',1)
    path.write_text(tx,encoding='utf-8')

print(f"Built Stage 4: {len(master['products'])} product pages, {len(master['skus'])} SKU pages, {len(master['categories'])} category pages, {len(eligible)} feed-eligible SKUs, {len(urls)} sitemap URLs")
