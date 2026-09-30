#!/usr/bin/env python3
from __future__ import annotations
import csv,io,json,re,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE='https://market.bb610.com.ua'
FEED='https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.csv'
GOOGLE_FEED='https://api.market.bb610.com.ua/api/v1/catalog/feeds/google-merchant.csv'
REPORT=ROOT/'docs/ai_sales/AI_SALES_STAGE2_LIVE_VALIDATION.json'

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'BB610-AI-Sales-Validator/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.status,r.read().decode('utf-8-sig','replace')

def main():
    errors=[]
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
    for bot in ('OAI-SearchBot','OAI-AdsBot','Claude-SearchBot','Claude-User'):
        if bot not in robots:errors.append('robots_missing:'+bot)
    checked=0
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
            for block in blocks:
                try:obj=json.loads(block)
                except Exception:continue
                if obj.get('@type')=='Product':product=obj;break
            if not product:errors.append('schema_missing:'+row.get('item_id',''));continue
            if str(product.get('sku') or '')!=str(row.get('item_id') or ''):errors.append('sku_mismatch:'+row.get('item_id',''))
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
    report={
        'status':'PASS' if not errors else 'FAIL',
        'openai_feed_rows':len(rows),
        'google_feed_rows':len(google_rows),
        'expected_rows':expected,
        'pages_checked':checked,
        'robots_http':robots_status,
        'openai_attribution':'PASS' if all('utm_source=chatgpt' in str(x.get('url') or '') for x in rows) else 'FAIL',
        'google_exact_sku_links':'PASS' if all(str(x.get('link') or '').startswith(SITE+'/products/') for x in google_rows) else 'FAIL',
                'openai_core_fields':'PASS' if not missing_fields else 'FAIL',
        'openai_market_targeting':openai_market_gate,
        'openai_target_countries':market_targets,
        'openai_stable_submission':'READY' if openai_market_gate=='READY' and not missing_fields else 'BLOCKED_MARKET_TARGET' if openai_market_gate!='READY' else 'FAIL',

        'openai_search_eligibility':'PASS' if all(str(x.get('is_eligible_search') or '').lower()=='true' for x in rows) else 'FAIL',
        'openai_checkout_eligibility':'PASS' if all(str(x.get('is_eligible_checkout') or '').lower()=='false' for x in rows) else 'FAIL',
        'openai_ads_policy':'PASS' if all(str(x.get('is_ads_eligible') or '').lower()=='false' for x in rows) else 'FAIL',
        'errors':errors
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
