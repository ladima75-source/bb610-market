from __future__ import annotations
import csv, io, json
from urllib.parse import urljoin
from ..catalog_provider import load_catalog
from .product_commerce import commerce_map

SITE='https://market.bb610.com.ua'
API='https://api.market.bb610.com.ua'
GOOGLE_FIELDS=['id','title','description','availability','condition','price','link','image_link','brand','gtin','mpn','item_group_id','product_type','custom_label_0']
META_FIELDS=['id','title','description','availability','condition','price','link','image_link','brand','gtin','mpn','item_group_id','product_type','custom_label_0']


def _products_and_skus():
    data=load_catalog()
    products={p['id']:dict(p) for p in data.get('products',[])}
    skus=[dict(s) for s in data.get('skus',[])]
    hidden=set()
    try:
        from .catalog_cms import _overrides, _dynamic_skus
        ov=_overrides()
        for pid,c in ov.items():
            if pid in products:
                if not c.get('cms_published'):
                    hidden.add(pid)
                else:
                    products[pid].update({k:v for k,v in c.items() if not k.startswith('cms_')})
            elif c.get('cms_published'):
                products[pid]={k:v for k,v in c.items() if not k.startswith('cms_')}
        # Dynamic SKUs are included only if their product explicitly carries feed_policy=allowed.
        skus += _dynamic_skus()
    except Exception:
        pass
    return data,products,skus,hidden


def _image(p,s):
    raw=s.get('image')
    if not raw:
        im=p.get('image')
        raw=im.get('local') if isinstance(im,dict) else im
    raw=str(raw or '')
    if not raw:return ''
    if raw.startswith('http://') or raw.startswith('https://'):return raw
    if raw.startswith('/media/') or raw.startswith('media/'):
        return API+'/'+raw.lstrip('/')
    return SITE+'/'+raw.lstrip('/')


def _real_image_ready(p,s):
    raw=s.get('image') or ((p.get('image') or {}).get('local') if isinstance(p.get('image'),dict) else p.get('image')) or ''
    raw=str(raw)
    real_path=('/real/' in raw or raw.startswith('/media/products/') or raw.startswith('https://')) and not raw.endswith('.svg')
    if real_path:return True
    explicit=s.get('feed_image_ready')
    if explicit is None: explicit=p.get('feed_image_ready')
    return bool(explicit) if explicit is not None else False


def _title(p,s):
    sku_title=((s.get('feed') or {}).get('title') or '').strip()
    if sku_title:
        return sku_title[:150]
    base=((p.get('feed') or {}).get('title') or p.get('official_name') or p.get('name') or s.get('product_id') or s.get('id')).strip()
    variant=(s.get('variant') or '').strip()
    return (base+' '+variant).strip()[:150]


def _description(p,s):
    x=((p.get('feed') or {}).get('description') or p.get('short_description') or p.get('manufacturer_use') or p.get('product_type') or '').strip()
    return x[:5000]


def _link(p,s):
    u=str(s.get('url') or '')
    if u.startswith('http'):return u
    if u.startswith('/'):return SITE+u
    return SITE+'/'+u.lstrip('/') if u else ''


def _availability_google(v):
    return {'in_stock':'in_stock','out_of_stock':'out_of_stock','preorder':'preorder','backorder':'backorder'}.get(v,'')


def _availability_meta(v):
    return {'in_stock':'in stock','out_of_stock':'out of stock','preorder':'preorder','backorder':'available for order'}.get(v,'')


def _status_row(p,s,c,hidden):
    sid=s.get('id') or s.get('sku')
    reasons=[]; warnings=[]
    enabled=bool(c.get('enabled'))
    price=c.get('effective_price')
    availability=c.get('availability','unknown')
    if not enabled:reasons.append('sale_disabled')
    if price is None or float(price)<=0:reasons.append('price_missing_or_zero')
    if availability not in {'in_stock','out_of_stock','preorder','backorder'}:reasons.append('availability_unknown')
    if p.get('id') in hidden or p.get('runtime_hidden'):reasons.append('product_not_published')
    if p.get('feed_policy')!='allowed' or s.get('feed_policy') not in (None,'allowed'):
        reasons.append('feed_policy_not_allowed')
    if not _real_image_ready(p,s):reasons.append('real_product_image_missing')
    if not _image(p,s):reasons.append('image_missing')
    if not _link(p,s):reasons.append('link_missing')
    brand=(p.get('brand') or '').strip()
    if (p.get('feed') or {}).get('brand_required') and not brand:reasons.append('brand_missing')
    gtin=(s.get('gtin_ean') or '').strip(); mpn=(s.get('mpn') or '').strip()
    if not gtin and not mpn:warnings.append('gtin_mpn_unverified')
    if s.get('launch_matrix_2026') and s.get('identifier_status')=='unverified':warnings.append('identifiers_require_source_check')
    return {'sku':sid,'product_id':s.get('product_id'),'title':_title(p,s),'launch_priority':s.get('launch_matrix_priority'),'included':not reasons,'reasons':reasons,'warnings':sorted(set(warnings)),'price':price,'availability':availability,'enabled':enabled,'image_link':_image(p,s)}


def snapshot(commerce_override:dict|None=None):
    data,products,skus,hidden=_products_and_skus()
    cm=commerce_override if commerce_override is not None else commerce_map()
    rows=[]; status=[]
    seen=set()
    for s in skus:
        sid=s.get('id') or s.get('sku')
        if not sid or sid in seen:continue
        seen.add(sid)
        p=products.get(s.get('product_id'))
        if not p:continue
        c=cm.get(sid,{})
        sr=_status_row(p,s,c,hidden); status.append(sr)
        if not sr['included']:continue
        price=float(c.get('effective_price'))
        base={
            'id':sid,'title':_title(p,s),'description':_description(p,s),
            'condition':'new','price':f'{price:.2f} UAH','link':_link(p,s),'image_link':_image(p,s),
            'brand':(p.get('brand') or '').strip(),'gtin':s.get('gtin_ean') or '','mpn':s.get('mpn') or '',
            'item_group_id':s.get('product_id') or '','product_type':p.get('product_type') or '',
            'custom_label_0':('warehouse' if s.get('launch_matrix_priority')=='A' else ('test' if s.get('launch_matrix_priority')=='B' else '')),
        }
        rows.append((base,c.get('availability')))
    return {'rows':rows,'status':status,'catalog_sku_count':len(seen)}


def _csv(fields, rows):
    buf=io.StringIO(newline=''); w=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows); return '\ufeff'+buf.getvalue()


def google_csv(commerce_override:dict|None=None):
    snap=snapshot(commerce_override); out=[]
    for base,av in snap['rows']:
        x=dict(base); x['availability']=_availability_google(av); out.append(x)
    return _csv(GOOGLE_FIELDS,out)


def meta_csv(commerce_override:dict|None=None):
    snap=snapshot(commerce_override); out=[]
    for base,av in snap['rows']:
        x=dict(base); x['availability']=_availability_meta(av); out.append(x)
    return _csv(META_FIELDS,out)


def feed_status(commerce_override:dict|None=None):
    snap=snapshot(commerce_override); items=snap['status']; launch=[x for x in items if x.get('launch_priority') in ('A','B')]
    return {
        'source':'catalog + live sku_commerce',
        'generated_for':'BB610 Market Stage 16A',
        'catalog_sku_count':snap['catalog_sku_count'],
        'eligible_count':sum(1 for x in items if x['included']),
        'launch_sku_count':len(launch),
        'launch_eligible_count':sum(1 for x in launch if x['included']),
        'note':'Price, availability, stock and sale-enabled state come from the backend admin database. Static catalog prices are not authoritative.',
        'items':items,
    }
