#!/usr/bin/env python3
from __future__ import annotations
import csv,io,json,re,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE='https://market.bb610.com.ua'
FEED='https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.csv'
REPORT=ROOT/'docs/ai_sales/AI_SALES_STAGE2_LIVE_VALIDATION.json'

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'BB610-AI-Sales-Validator/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.status,r.read().decode('utf-8-sig','replace')

def main():
    errors=[]
    status,raw=get(FEED)
    rows=list(csv.DictReader(io.StringIO(raw)))
    expected=json.loads((ROOT/'ops/merchant_feed_guard.json').read_text(encoding='utf-8'))['expected_active_items']
    if status!=200:errors.append(f'feed_http={status}')
    if len(rows)!=expected:errors.append(f'feed_count={len(rows)} expected={expected}')
    robots_status,robots=get(SITE+'/robots.txt')
    for bot in ('OAI-SearchBot','OAI-AdsBot','Claude-SearchBot','Claude-User'):
        if bot not in robots:errors.append('robots_missing:'+bot)
    checked=0
    for row in rows:
        url=(row.get('url') or '').strip()
        if not url.startswith(SITE+'/products/'):errors.append('bad_url:'+row.get('item_id',''));continue
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
    report={'status':'PASS' if not errors else 'FAIL','feed_rows':len(rows),'expected_rows':expected,'pages_checked':checked,'robots_http':robots_status,'errors':errors}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
