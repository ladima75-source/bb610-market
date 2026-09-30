#!/usr/bin/env python3
from __future__ import annotations
import csv,io,json,re,urllib.request
from urllib.parse import urlparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE='https://market.bb610.com.ua'
FEED='https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.csv'
GOOGLE_FEED='https://api.market.bb610.com.ua/api/v1/catalog/feeds/google-merchant.csv'
REPORT=ROOT/'docs/ai_sales/AI_SALES_STAGE2_LIVE_VALIDATION.json'
GOOGLE_VERIFICATION_PATH='/google61cfaf68d12ddac6.html'
GOOGLE_VERIFICATION_BODY='google-site-verification: google61cfaf68d12ddac6.html'

GUIDE_PATHS=[
    'abiotic-stress-and-megafol',
    'before-planting-seedlings-product-selection',
    'blueberry-pot-25l-vs-40l',
    'ferrilene-vs-brexil-fe',
    'high-phosphorus-alternatives-master-13-40-13',
    'how-to-choose-pack-size',
    'master-13-40-13-vs-20-20-20',
    'plantafol-20-20-20-vs-master-20-20-20',
]

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'BB610-AI-Sales-Validator/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.status,r.read().decode('utf-8-sig','replace')

def jsonld_types(body):
    types=set()
    blocks=re.findall(r'<script type="application/ld\+json">(.*?)</script>',body,re.S|re.I)
    for block in blocks:
        try:
            obj=json.loads(block)
        except Exception:
            continue
        nodes=[]
        if isinstance(obj,dict):
            nodes.append(obj)
            graph=obj.get('@graph')
            if isinstance(graph,list):
                nodes.extend(x for x in graph if isinstance(x,dict))
        elif isinstance(obj,list):
            nodes.extend(x for x in obj if isinstance(x,dict))
        for node in nodes:
            value=node.get('@type')
            if isinstance(value,list):
                types.update(str(x) for x in value)
            elif value:
                types.add(str(value))
    return types

def image_magic(url):
    try:
        req=urllib.request.Request(
            url,
            headers={
                'Range':'bytes=0-31',
                'User-Agent':'BB610-AI-Sales-Validator/1.0',
            },
        )
        with urllib.request.urlopen(req,timeout=20) as r:
            raw=r.read(32)
        if raw.startswith(bytes.fromhex('ffd8ff')):
            return 'jpeg'
        if raw.startswith(bytes.fromhex('89504e470d0a1a0a')):
            return 'png'
        if raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':
            return 'webp'
        return 'unknown'
    except Exception as e:
        return 'error:'+str(e)[:80]

def main():
    errors=[]
    guide_paths=list(GUIDE_PATHS)
    status,raw=get(FEED)
    rows=list(csv.DictReader(io.StringIO(raw)))
    google_status,google_raw=get(GOOGLE_FEED)
    google_rows=list(csv.DictReader(io.StringIO(google_raw)))
    expected=json.loads((ROOT/'ops/merchant_feed_guard.json').read_text(encoding='utf-8'))['expected_active_items']
    if status!=200:errors.append(f'feed_http={status}')
    if google_status!=200:errors.append(f'google_feed_http={google_status}')
    if len(rows)!=expected:errors.append(f'feed_count={len(rows)} expected={expected}')
    if len(google_rows)!=expected:errors.append(f'google_feed_count={len(google_rows)} expected={expected}')
    required_openai_core_fields={
        'item_id','title','description','url','brand','seller_name','image_url',
        'availability','price','is_eligible_search','is_eligible_checkout'
    }
    actual_fields=set(rows[0].keys()) if rows else set()
    missing_fields=sorted(required_openai_core_fields-actual_fields)
    if missing_fields:errors.append('openai_core_fields_missing:'+','.join(missing_fields))
    market_field_present='target_countries' in actual_fields
    market_targets=sorted({str(x.get('target_countries') or '').strip() for x in rows if str(x.get('target_countries') or '').strip()})
    openai_market_gate='READY' if market_field_present and market_targets else 'BLOCKED_MARKET_TARGET'

    if 'is_ads_eligible' not in actual_fields:
        errors.append('openai_ads_policy_field_missing:is_ads_eligible')
    google_by_id={str(x.get('id') or ''):x for x in google_rows}
    robots_status,robots=get(SITE+'/robots.txt')
    for bot in ('OAI-SearchBot','OAI-AdsBot','ChatGPT-User','Claude-SearchBot','Claude-User','Googlebot','Google-Extended'):
        if bot not in robots:errors.append('robots_missing:'+bot)

    sitemap_lastmod='FAIL'
    sitemap_urls_checked=0
    try:
        sitemap_code,sitemap_body=get(SITE+'/sitemap.xml')
        entries=re.findall(r'<url>\s*<loc>(.*?)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?\s*</url>',sitemap_body,re.S|re.I)
        sitemap_map={loc.strip():lastmod.strip() for loc,lastmod in entries}
        live_guide_prefix=SITE+'/guides/'
        discovered_guide_paths=sorted({
            loc.strip()[len(live_guide_prefix):].strip('/')
            for loc,_lastmod in entries
            if loc.strip().startswith(live_guide_prefix)
            and loc.strip()!=live_guide_prefix
            and loc.strip().endswith('/')
        })
        if discovered_guide_paths:
            guide_paths=discovered_guide_paths
        discovery_urls={SITE+'/',SITE+'/guides/'}
        discovery_urls.update(f'{SITE}/guides/{slug}/' for slug in guide_paths)
        stage1=json.loads((ROOT/'docs/ai_sales/AI_SALES_STAGE1_PDP_SYNC_REPORT.json').read_text(encoding='utf-8'))
        for item in stage1.get('items') or []:
            parsed=urlparse(str(item.get('url') or '').strip())
            if parsed.scheme and parsed.netloc and parsed.path:
                discovery_urls.add(f'{parsed.scheme}://{parsed.netloc}{parsed.path}')
        missing_sitemap=sorted(u for u in discovery_urls if u not in sitemap_map)
        stale_lastmod=sorted(
            u for u in discovery_urls
            if u in sitemap_map and (
                not re.fullmatch(r'\d{4}-\d{2}-\d{2}',sitemap_map.get(u,''))
                or sitemap_map.get(u,'')<'2026-09-30'
            )
        )
        sitemap_urls_checked=len(discovery_urls)-len(missing_sitemap)
        if sitemap_code!=200:
            errors.append(f'sitemap_http={sitemap_code}')
        if missing_sitemap:
            errors.append('sitemap_missing_urls:'+','.join(missing_sitemap[:20]))
        if stale_lastmod:
            errors.append('sitemap_lastmod_missing_or_stale:'+','.join(stale_lastmod[:20]))
        if not missing_sitemap and not stale_lastmod:
            sitemap_lastmod='PASS'
    except Exception as e:
        errors.append('sitemap_validation:'+str(e))

    google_site_verification='FAIL'
    try:
        gcode,gbody=get(SITE+GOOGLE_VERIFICATION_PATH)
        if gcode!=200:
            errors.append(f'google_site_verification_http={gcode}')
        elif gbody.strip()!=GOOGLE_VERIFICATION_BODY:
            errors.append('google_site_verification_body_mismatch')
        else:
            google_site_verification='PASS'
    except Exception as e:
        errors.append('google_site_verification_fetch:'+str(e))

    sitemap_status='FAIL'
    sitemap_exact_sku_lastmod=0
    sitemap_guides_lastmod=0
    sitemap_dnipro_lastmod=False
    try:
        scode,sbody=get(SITE+'/sitemap.xml')
        if scode!=200:
            errors.append(f'sitemap_http={scode}')
        else:
            expected_exact=[str(row.get('url') or '').split('?',1)[0] for row in rows]
            missing=[u for u in expected_exact if f'<loc>{u}</loc>' not in sbody]
            if missing:
                errors.append('sitemap_missing_exact_sku:'+','.join(missing[:10]))
            else:
                sitemap_exact_sku_lastmod=sum(
                    1 for u in expected_exact
                    if f'<loc>{u}</loc><lastmod>2026-09-30</lastmod>' in sbody
                )
                guide_urls=[SITE+'/guides/']+[f'{SITE}/guides/{slug}/' for slug in guide_paths]
                gmissing=[u for u in guide_urls if f'<loc>{u}</loc>' not in sbody]
                if gmissing:
                    errors.append('sitemap_missing_guides:'+','.join(gmissing))
                else:
                    sitemap_guides_lastmod=sum(
                        1 for u in guide_urls
                        if f'<loc>{u}</loc><lastmod>2026-09-30</lastmod>' in sbody
                    )
                    sitemap_dnipro_lastmod=(
                        f'<loc>{SITE}/dnipro/</loc><lastmod>2026-09-30</lastmod>' in sbody
                    )
                    if sitemap_exact_sku_lastmod!=len(expected_exact):
                        errors.append(f'sitemap_exact_sku_lastmod={sitemap_exact_sku_lastmod}/{len(expected_exact)}')
                    elif sitemap_guides_lastmod!=len(guide_urls):
                        errors.append(f'sitemap_guides_lastmod={sitemap_guides_lastmod}/{len(guide_urls)}')
                    elif not sitemap_dnipro_lastmod:
                        errors.append('sitemap_dnipro_lastmod_missing')
                    else:
                        sitemap_status='PASS'
    except Exception as e:
        errors.append('sitemap_fetch:'+str(e))

    local_landing='FAIL'
    try:
        lurl=SITE+'/dnipro/'
        lcode,lbody=get(lurl)
        ltypes=jsonld_types(lbody)
        if lcode!=200:
            errors.append(f'local_landing_http={lcode}')
        elif f'<link rel="canonical" href="{lurl}">' not in lbody:
            errors.append('local_landing_canonical')
        elif 'index,follow' not in lbody:
            errors.append('local_landing_noindex')
        elif any(t not in ltypes for t in ('WebPage','Store','BreadcrumbList')):
            errors.append('local_landing_schema_missing')
        elif 'вул. М. Рильського, 106' not in lbody:
            errors.append('local_landing_address_missing')
        elif '+380 (77) 017 97 70' not in lbody:
            errors.append('local_landing_phone_missing')
        elif 'від 2 000 грн' not in lbody:
            errors.append('local_landing_delivery_threshold_missing')
        else:
            local_landing='PASS'
    except Exception as e:
        errors.append('local_landing_fetch:'+str(e))

    merchant_return_policy='FAIL'
    try:
        home_code,home_body=get(SITE+'/')
        home_blocks=re.findall(r'<script type="application/ld\+json">(.*?)</script>',home_body,re.S|re.I)
        home_nodes=[]
        for block in home_blocks:
            try:obj=json.loads(block)
            except Exception:continue
            if isinstance(obj,dict):
                home_nodes.append(obj)
                graph=obj.get('@graph')
                if isinstance(graph,list):
                    home_nodes.extend(x for x in graph if isinstance(x,dict))
        def has_type(node,value):
            current=node.get('@type') if isinstance(node,dict) else None
            return value in current if isinstance(current,list) else current==value
        org=next((x for x in home_nodes if has_type(x,'OnlineStore') and x.get('@id')==SITE+'/#organization'),None)
        policy=(org or {}).get('hasMerchantReturnPolicy') or {}
        if home_code!=200:
            errors.append(f'home_http={home_code}')
        elif str((org or {}).get('taxID') or '').strip()!='2560502404':
            errors.append('merchant_tax_id_missing_or_mismatch')
        elif not isinstance(policy,dict) or policy.get('@type')!='MerchantReturnPolicy':
            errors.append('merchant_return_policy_missing')
        elif str(policy.get('merchantReturnLink') or '').strip()!=SITE+'/returns.html':
            errors.append('merchant_return_policy_link_mismatch')
        else:
            merchant_return_policy='PASS'
    except Exception as e:
        errors.append('merchant_return_policy_fetch:'+str(e))

    guide_pages_checked=0
    guide_hub_status='FAIL'
    try:
        hub_code,hub_body=get(SITE+'/guides/')
        hub_types=jsonld_types(hub_body)
        if hub_code!=200:
            errors.append(f'guide_hub_http={hub_code}')
        elif 'CollectionPage' not in hub_types:
            errors.append('guide_hub_schema_missing:CollectionPage')
        elif 'index,follow' not in hub_body:
            errors.append('guide_hub_noindex')
        else:
            missing_links=[slug for slug in guide_paths if f'href="{slug}/"' not in hub_body]
            if missing_links:
                errors.append('guide_hub_missing_links:'+','.join(missing_links))
            else:
                guide_hub_status='PASS'
    except Exception as e:
        errors.append('guide_hub_fetch:'+str(e))

    for slug in guide_paths:
        guide_url=f'{SITE}/guides/{slug}/'
        try:
            code,body=get(guide_url)
            if code!=200:
                errors.append(f'guide_http:{slug}={code}')
                continue
            canonical=f'<link rel="canonical" href="{guide_url}">'
            if canonical not in body:
                errors.append('guide_canonical:'+slug)
            if 'index,follow' not in body:
                errors.append('guide_noindex:'+slug)
            types=jsonld_types(body)
            for required_type in ('Article','BreadcrumbList'):
                if required_type not in types:
                    errors.append(f'guide_schema_missing:{slug}:{required_type}')
            if 'Усі матеріали довідника' not in body:
                errors.append('guide_hub_backlink_missing:'+slug)
            guide_pages_checked+=1
        except Exception as e:
            errors.append(f'guide_fetch:{slug}:{e}')

    offer_ids=[str(x.get('offer_id') or '').strip() for x in rows]
    if 'offer_id' not in actual_fields:
        errors.append('openai_quality_field_missing:offer_id')
    elif any(not x for x in offer_ids):
        errors.append('openai_offer_id_missing')
    elif len(set(offer_ids))!=len(offer_ids):
        errors.append('openai_offer_id_not_unique')
    if 'return_policy' not in actual_fields:
        errors.append('openai_quality_field_missing:return_policy')
    elif any(str(x.get('return_policy') or '').strip()!=SITE+'/returns.html' for x in rows):
        errors.append('openai_return_policy_mismatch')

    checked=0
    grouped_pages_checked=0
    for row in rows:
        item_id=str(row.get('item_id') or '')
        for field in required_openai_core_fields:
            if str(row.get(field) or '').strip()=='':
                errors.append('openai_required_value_missing:'+item_id+':'+field)
        if str(row.get('is_eligible_search') or '').strip().lower()!='true':
            errors.append('openai_search_eligibility_invalid:'+item_id)
        if str(row.get('is_eligible_checkout') or '').strip().lower()!='false':
            errors.append('openai_checkout_must_be_false:'+item_id)
        if str(row.get('is_ads_eligible') or '').strip().lower()!='false':
            errors.append('openai_ads_must_be_false:'+item_id)
        url=(row.get('url') or '').strip()
        if not url.startswith(SITE+'/products/'):errors.append('bad_url:'+item_id);continue
        if 'utm_source=chatgpt' not in url or 'utm_medium=product_feed' not in url:
            errors.append('openai_attribution_missing:'+item_id)
        grow=google_by_id.get(item_id)
        if not grow:
            errors.append('google_missing:'+item_id)
        else:
            glink=str(grow.get('link') or '')
            if not glink.startswith(SITE+'/products/'):
                errors.append('google_not_exact_sku_url:'+item_id)
            try:
                if float(str(grow.get('price') or '').split()[0])!=float(str(row.get('price') or '').split()[0]):
                    errors.append('google_openai_price_mismatch:'+item_id)
            except Exception:
                errors.append('google_openai_price_invalid:'+item_id)
        try:
            code,body=get(url)
            if code!=200:errors.append(f'http:{row.get("item_id")}={code}');continue
            if 'index,follow,max-image-preview:large' not in body:errors.append('noindex:'+row.get('item_id',''))
            blocks=re.findall(r'<script type="application/ld\+json">(.*?)</script>',body,re.S|re.I)
            product=None
            product_group=None
            breadcrumb_schema=None
            for block in blocks:
                try:obj=json.loads(block)
                except Exception:continue
                if obj.get('@type')=='Product' and product is None:
                    product=obj
                elif obj.get('@type')=='ProductGroup' and product_group is None:
                    product_group=obj
                elif obj.get('@type')=='BreadcrumbList' and breadcrumb_schema is None:
                    breadcrumb_schema=obj
            if not product:errors.append('schema_missing:'+row.get('item_id',''));continue
            if str(product.get('sku') or '')!=str(row.get('item_id') or ''):errors.append('sku_mismatch:'+row.get('item_id',''))
            if not breadcrumb_schema:
                errors.append('breadcrumb_schema_missing:'+item_id)
            else:
                items=breadcrumb_schema.get('itemListElement') or []
                if not isinstance(items,list) or len(items)<2:
                    errors.append('breadcrumb_items_invalid:'+item_id)
                else:
                    positions=[x.get('position') for x in items if isinstance(x,dict)]
                    if positions!=list(range(1,len(items)+1)):
                        errors.append('breadcrumb_positions_invalid:'+item_id)
                    last=items[-1] if items else {}
                    if str(last.get('item') or '').strip()!=url.split('?',1)[0]:
                        errors.append('breadcrumb_current_url_mismatch:'+item_id)

            group_id=str(row.get('group_id') or '').strip()
            if group_id:
                if str(product.get('inProductGroupWithID') or '').strip()!=group_id:
                    errors.append('product_group_id_mismatch:'+item_id)
                is_variant=product.get('isVariantOf') or {}
                if not isinstance(is_variant,dict) or is_variant.get('@type')!='ProductGroup' or not str(is_variant.get('@id') or '').strip():
                    errors.append('product_is_variant_of_missing:'+item_id)
                try:
                    variant_dict=json.loads(str(row.get('variant_dict') or '{}'))
                except Exception:
                    variant_dict={}
                expected_size=str(variant_dict.get('package') or '').strip()
                if expected_size and str(product.get('size') or '').strip()!=expected_size:
                    errors.append('product_variant_size_mismatch:'+item_id)
                if not product_group:
                    errors.append('product_group_schema_missing:'+item_id)
                else:
                    if str(product_group.get('productGroupID') or '').strip()!=group_id:
                        errors.append('product_group_schema_id_mismatch:'+item_id)
                    varies=product_group.get('variesBy') or []
                    if isinstance(varies,str):varies=[varies]
                    if 'https://schema.org/size' not in varies:
                        errors.append('product_group_variesby_missing:'+item_id)
                    variants=product_group.get('hasVariant') or []
                    if not isinstance(variants,list) or len(variants)<2:
                        errors.append('product_group_variants_missing:'+item_id)
                grouped_pages_checked+=1

            offer=product.get('offers') or {}
            feed_price=str(row.get('price') or '').split()[0]
            try:
                same_price=float(offer.get('price'))==float(feed_price)
            except Exception:
                same_price=False
            if not same_price:errors.append('price_mismatch:'+row.get('item_id',''))
            checked+=1
        except Exception as e:
            errors.append(f'fetch:{row.get("item_id")}:{e}')
    image_ext_counts={}
    unsupported_images=[]
    for x in rows:
        image_url=str(x.get('image_url') or '').strip()
        path=urlparse(image_url).path.lower()
        ext=Path(path).suffix
        image_ext_counts[ext]=image_ext_counts.get(ext,0)+1
        if ext not in {'.jpg','.jpeg','.png'}:
            unsupported_images.append(str(x.get('item_id') or '')+':'+image_url)
    unsupported_image_magic={item.split(':',1)[0]:image_magic(item.split(':',1)[1]) for item in unsupported_images}
    quality={
        'seller_url':sum(1 for x in rows if str(x.get('seller_url') or '').strip()),
        'product_category':sum(1 for x in rows if str(x.get('product_category') or '').strip()),
        'gtin':sum(1 for x in rows if str(x.get('gtin') or '').strip()),
        'mpn':sum(1 for x in rows if str(x.get('mpn') or '').strip()),
        'gtin_or_mpn':sum(1 for x in rows if str(x.get('gtin') or '').strip() or str(x.get('mpn') or '').strip()),
        'group_id':sum(1 for x in rows if str(x.get('group_id') or '').strip()),
        'variant_dict':sum(1 for x in rows if str(x.get('variant_dict') or '').strip()),
        'listing_has_variations_true':sum(1 for x in rows if str(x.get('listing_has_variations') or '').strip().lower()=='true'),
        'offer_id':sum(1 for x in rows if str(x.get('offer_id') or '').strip()),
        'return_policy':sum(1 for x in rows if str(x.get('return_policy') or '').strip()),
        'image_extension_counts':image_ext_counts,
        'openai_image_format_supported':len(rows)-len(unsupported_images),
        'openai_image_format_unsupported':len(unsupported_images),
        'unsupported_image_magic':unsupported_image_magic,
    }
    report={
        'status':'PASS' if not errors else 'FAIL',
        'openai_feed_rows':len(rows),
        'google_feed_rows':len(google_rows),
        'google_feed_inventory':[
            {
                'id':str(x.get('id') or ''),
                'title':str(x.get('title') or ''),
                'link':str(x.get('link') or ''),
                'price':str(x.get('price') or ''),
                'availability':str(x.get('availability') or ''),
            }
            for x in sorted(google_rows,key=lambda row:str(row.get('id') or ''))
        ],
        'expected_rows':expected,
        'pages_checked':checked,
        'grouped_pages_checked':grouped_pages_checked,
        'google_site_verification':google_site_verification,
        'sitemap_status':sitemap_status,
        'sitemap_exact_sku_lastmod':sitemap_exact_sku_lastmod,
        'sitemap_guides_lastmod':sitemap_guides_lastmod,
        'sitemap_dnipro_lastmod':sitemap_dnipro_lastmod,
        'local_landing':local_landing,
        'merchant_return_policy':merchant_return_policy,
        'sitemap_lastmod':sitemap_lastmod,
        'sitemap_discovery_urls_checked':sitemap_urls_checked,
        'guide_hub':guide_hub_status,
        'guide_pages_expected':len(guide_paths),
        'guide_pages_checked':guide_pages_checked,
        'robots_http':robots_status,
        'openai_attribution':'PASS' if all('utm_source=chatgpt' in str(x.get('url') or '') for x in rows) else 'FAIL',
        'google_exact_sku_links':'PASS' if all(str(x.get('link') or '').startswith(SITE+'/products/') for x in google_rows) else 'FAIL',
                'openai_core_fields':'PASS' if not missing_fields else 'FAIL',
        'openai_market_targeting':openai_market_gate,
        'openai_target_countries':market_targets,
        'openai_stable_submission':'READY_FOR_ONBOARDING_VALIDATION' if not missing_fields else 'FAIL',
        'openai_market_setup':'READY' if openai_market_gate=='READY' else 'REQUIRES_OPENAI_MARKET_SETUP',

        'openai_search_eligibility':'PASS' if all(str(x.get('is_eligible_search') or '').lower()=='true' for x in rows) else 'FAIL',
        'openai_checkout_eligibility':'PASS' if all(str(x.get('is_eligible_checkout') or '').lower()=='false' for x in rows) else 'FAIL',
        'openai_ads_policy':'PASS' if all(str(x.get('is_ads_eligible') or '').lower()=='false' for x in rows) else 'FAIL',
        'openai_quality_coverage':quality,
        'openai_image_format':'PASS' if not unsupported_images else 'BLOCKED_UNSUPPORTED_IMAGE_FORMAT',
        'openai_unsupported_images':unsupported_images[:50],
        'errors':errors
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
