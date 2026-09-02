#!/usr/bin/env python3
from __future__ import annotations
import html as htmlmod, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
CAT=ROOT/'data'/'catalog.master.json'
OUT=ROOT/'assets'/'img'/'real'/'stage16b'
OUT.mkdir(parents=True,exist_ok=True)
master=json.loads(CAT.read_text(encoding='utf-8'))

UA='Mozilla/5.0 (compatible; BB610Market/1.0; +https://market.bb610.com.ua/)'
OP='https://organicplanet.com.ua'
PL='https://getplantlogic.com'

def fetch(url, binary=False, timeout=25):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'image/avif,image/webp,image/apng,image/*,*/*;q=0.8' if binary else 'text/html,*/*;q=0.8'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=r.read()
        return data if binary else data.decode('utf-8','ignore'), r.headers.get('Content-Type','')

def absolute(base,u):
    u=htmlmod.unescape(u).replace('\\/','/')
    return urllib.parse.urljoin(base,u)

def image_from_page(url):
    try: page,_=fetch(url)
    except Exception as e:
        return '',f'page_fetch:{e}'
    patterns=[
      r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
      r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
      r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
      r'<img[^>]+(?:data-src|src)=["\']([^"\']+(?:534x534|600x600|product|portfolio)[^"\']*)["\']',
    ]
    for pat in patterns:
        m=re.search(pat,page,re.I)
        if m:
            u=absolute(url,m.group(1))
            if not any(x in u.lower() for x in ('logo','banner','icon','placeholder')):
                return u,''
    # Organic Planet fallback: choose first cached catalog image near product content.
    imgs=re.findall(r'(?:data-src|src)=["\']([^"\']+/image/cache/catalog/[^"\']+)["\']',page,re.I)
    for x in imgs:
        u=absolute(url,x)
        if not any(z in u.lower() for z in ('logo','banner','icon')):
            return u,''
    return '','image_not_found'

def search_organic(query):
    # OpenCart-compatible search; exact page URL is preferred when catalog has one.
    q=urllib.parse.quote(query)
    urls=[
      f'{OP}/index.php?route=product/search&search={q}',
      f'{OP}/?search={q}',
    ]
    tokens=[x.lower() for x in re.findall(r'[A-Za-zА-Яа-яІіЇїЄє0-9]{3,}',query) if x.lower() not in {'valagro','organic','planet'}]
    best=None
    for su in urls:
        try: page,_=fetch(su)
        except Exception: continue
        links=re.findall(r'href=["\'](https?://organicplanet\.com\.ua/katalog/[^"\']+)["\']',page,re.I)
        for link in links:
            clean=htmlmod.unescape(link)
            score=sum(1 for t in tokens if t in clean.lower())
            if best is None or score>best[0]: best=(score,clean)
        if best and best[0]>=2: break
    return best[1] if best else ''

def search_plantlogic(query):
    q=query.lower()
    if '1308125' in q or '25 liter round pot' in q:
        return 'https://getplantlogic.com/portfolio-items/new-25-liter-round-pot/'
    if '1308041' in q or '40 liter round pot' in q:
        return 'https://getplantlogic.com/portfolio-items/40l-round-pot-with-u-grooves/'
    return ''

def save_image(url,pid):
    raw,ctype=fetch(url,binary=True)
    if len(raw)<5000: raise RuntimeError(f'image too small ({len(raw)} bytes)')
    c=(ctype or '').lower()
    ext='.webp' if 'webp' in c else '.png' if 'png' in c else '.jpg'
    if not c.startswith('image/'):
        # Accept common magic signatures when server has poor Content-Type.
        if raw[:8]==b'\x89PNG\r\n\x1a\n': ext='.png'
        elif raw[:3]==b'\xff\xd8\xff': ext='.jpg'
        elif raw[:4]==b'RIFF' and b'WEBP' in raw[:16]: ext='.webp'
        else: raise RuntimeError(f'not an image: {ctype}')
    path=OUT/(re.sub(r'[^a-z0-9_-]+','-',pid.lower())+ext)
    path.write_bytes(raw)
    return path.relative_to(ROOT).as_posix()

report=[]
for p in master.get('products',[]):
    query=str(p.get('stage16b_image_query') or '').strip()
    if not query: continue
    pid=str(p.get('id') or p.get('slug') or 'product')
    page=str(p.get('stage16b_source_url') or '').strip()
    if not page:
        page=search_plantlogic(query) if 'plantlogic' in query.lower() else search_organic(query)
    if not page:
        report.append({'product_id':pid,'ok':False,'reason':'source_page_not_found','query':query})
        continue
    img,err=image_from_page(page)
    if not img:
        report.append({'product_id':pid,'ok':False,'reason':err,'source_page':page})
        continue
    try:
        local=save_image(img,pid)
        p['image']={'local':local,'officialSourceUrl':page,'status':'local-imported-product-photo'}
        p['feed_image_ready']=True
        p['stage16b_content_status']='complete'
        report.append({'product_id':pid,'ok':True,'local':local,'source_page':page,'source_image':img})
    except Exception as e:
        report.append({'product_id':pid,'ok':False,'reason':str(e),'source_page':page,'source_image':img})
    time.sleep(.15)

# SKUs inherit product image unless a SKU already has an explicit real local image.
products={p.get('id'):p for p in master.get('products',[])}
for s in master.get('skus',[]):
    p=products.get(s.get('product_id'))
    if not p: continue
    pim=p.get('image')
    plocal=pim.get('local','') if isinstance(pim,dict) else str(pim or '')
    if p.get('feed_image_ready') and plocal:
        current=str(s.get('image') or '')
        if not current or current.endswith('.svg') or 'product-' in current:
            s['image']=None
        s['feed_image_ready']=True

CAT.write_text(json.dumps(master,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
(ROOT/'STAGE16B_IMAGE_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
ok=sum(1 for x in report if x['ok'])
print(f'Stage 16B images: {ok}/{len(report)} downloaded locally')
for x in report:
    if not x['ok']: print('WARN:',x['product_id'],x['reason'])
