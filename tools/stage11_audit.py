#!/usr/bin/env python3
import json, pathlib, re, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
checks=[]
def add(cid, area, status, detail, blocking=False):
    checks.append({'id':cid,'area':area,'status':status,'blocking':bool(blocking),'detail':detail})
def read(rel): return (ROOT/rel).read_text(encoding='utf-8', errors='replace')

required=['index.html','catalog.html','cart.html','checkout.html','favorites.html','compare.html','contacts.html','delivery.html','payment.html','returns.html','terms.html','privacy.html','about.html','robots.txt','sitemap.xml']
missing=[p for p in required if not (ROOT/p).exists()]
add('static.required_pages','Frontend','PASS' if not missing else 'FAIL','Все обязательные публичные/служебные страницы существуют.' if not missing else 'Отсутствуют: '+', '.join(missing),bool(missing))

bad=[]
htmls=list(ROOT.rglob('*.html'))
for f in htmls:
    text=f.read_text(encoding='utf-8',errors='replace')
    bm=re.search(r"<base\s+href=[\"']([^\"']+)[\"']", text, re.I)
    if bm:
        basev=bm.group(1)
        if basev.startswith('/'):
            base_dir=ROOT/basev.lstrip('/')
        elif basev.startswith(('http://','https://','//')):
            base_dir=ROOT
        else:
            base_dir=(f.parent/basev).resolve()
    else:
        base_dir=f.parent
    link_text=re.sub(r"<base\s+href=[\"'][^\"']+[\"'][^>]*>", '', text, flags=re.I)
    for val in re.findall(r"(?:href|src)=[\"']([^\"']+)[\"']", link_text):
        if not val or val.startswith(('#','mailto:','tel:','data:','javascript:','http://','https://','//')):
            continue
        val=val.split('?',1)[0].split('#',1)[0]
        if not val: continue
        target=(ROOT/val.lstrip('/')) if val.startswith('/') else (base_dir/val).resolve()
        if target.is_dir(): target=target/'index.html'
        if not target.exists(): bad.append(f'{f.relative_to(ROOT)} -> {val}')
add('static.local_links','Frontend','PASS' if not bad else 'FAIL',f'Проверено {len(htmls)} HTML; битых локальных href/src: {len(bad)}.'+('' if not bad else ' Примеры: '+'; '.join(bad[:8])),bool(bad))

js_files=list((ROOT/'js').glob('*.js'))+list((ROOT/'admin').glob('*.js'))+list((ROOT/'config').glob('*.js'))
js_fail=[]
for p in js_files:
    r=subprocess.run(['node','--check',str(p)],capture_output=True,text=True)
    if r.returncode: js_fail.append(f'{p.relative_to(ROOT)}: {r.stderr.strip()[:180]}')
add('code.javascript_syntax','Code','PASS' if not js_fail else 'FAIL',f'JS syntax: {len(js_files)-len(js_fail)}/{len(js_files)} OK.'+('' if not js_fail else ' Ошибки: '+' | '.join(js_fail[:4])),bool(js_fail))

py_files=list((ROOT/'backend').rglob('*.py'))+list((ROOT/'tools').glob('*.py'))
py_fail=[]
for p in py_files:
    r=subprocess.run([sys.executable,'-m','py_compile',str(p)],capture_output=True,text=True)
    if r.returncode: py_fail.append(f'{p.relative_to(ROOT)}: {r.stderr.strip()[:180]}')
add('code.python_compile','Code','PASS' if not py_fail else 'FAIL',f'Python compile: {len(py_files)-len(py_fail)}/{len(py_files)} OK.'+('' if not py_fail else ' Ошибки: '+' | '.join(py_fail[:4])),bool(py_fail))

catalog=json.loads(read('data/catalog.master.json'))
skus=catalog.get('skus',[]); products=catalog.get('products',[])
active=[s for s in skus if s.get('commercial_status')=='active' and s.get('offer_status')=='active']
feed_eligible=[s for s in skus if s.get('feed_eligible') is True]
add('catalog.identities','Commerce','PASS',f'PRODUCT: {len(products)}; SKU: {len(skus)}. Стабильная SKU-модель присутствует.')
add('catalog.active_skus','Commerce','PASS' if active else 'BLOCKED',f'Активных коммерческих SKU: {len(active)}.' if active else 'Нет активных коммерческих SKU с реальной ценой/наличием. Магазин нельзя считать продающим.',not bool(active))
add('feeds.eligible','Advertising','PASS' if feed_eligible else 'BLOCKED',f'Feed-eligible SKU: {len(feed_eligible)}.' if feed_eligible else 'Merchant/Meta feeds корректно не содержат продаваемых SKU, пока коммерческие данные не активированы.',False)

store=read('config/store-info.js')
missing_seller=[k for k in ['legal_name','edrpou_or_tax_id','registered_address','phone','email'] if re.search(rf'{re.escape(k)}\s*:\s*null',store)]
missing_returns=[k for k in ['window_days','return_method','return_shipping_payer','refund_timing'] if re.search(rf'{re.escape(k)}\s*:\s*null',store)]
add('legal.seller','Legal','PASS' if not missing_seller else 'BLOCKED','Реквизиты продавца заполнены.' if not missing_seller else 'Не заполнены реквизиты: '+', '.join(missing_seller),bool(missing_seller))
add('legal.returns','Legal','PASS' if not missing_returns else 'BLOCKED','Политика возврата параметризована.' if not missing_returns else 'Не определены правила возврата: '+', '.join(missing_returns),bool(missing_returns))

required_backend=['backend/app.py','backend/db.py','backend/services/orders.py','backend/services/delivery_service.py','backend/services/payment_service.py','admin/index.html']
mb=[p for p in required_backend if not (ROOT/p).exists()]
add('backend.core','Operations','PASS' if not mb else 'FAIL','Orders/Delivery/Payment/Admin skeleton присутствует.' if not mb else 'Отсутствует: '+', '.join(mb),bool(mb))

analytics=read('config/analytics-config.js')
analytics_disabled=bool(re.search(r'enabled\s*:\s*false',analytics)) or 'GTM-' not in analytics
add('payments.live_provider','Payments','BLOCKED','Реальный online payment provider и merchant credentials ещё не подключены. Это ожидаемый launch blocker.',True)
add('delivery.credentials','Delivery','BLOCKED','Нова пошта/Укрпошта требуют реальные account/API credentials и параметры отправителя перед live-работой.',True)
add('analytics.activation','Analytics','PASS' if analytics_disabled else 'REVIEW','Analytics/ads интеграции остаются подготовленными, но не активированы — правильно до live launch.',False)
succ=read('js/order-success.js') if (ROOT/'js/order-success.js').exists() else ''
gated=('purchase_ready' in succ and 'transaction_id' in succ)
add('analytics.purchase_gate','Analytics','PASS' if gated else 'FAIL','purchase остаётся backend-confirmed и требует transaction_id.' if gated else 'Не найдено ожидаемое backend-gating purchase.',not gated)

robots=read('robots.txt'); sitemap=read('sitemap.xml')
seo_ok='Sitemap:' in robots and '<urlset' in sitemap
add('seo.robots_sitemap','SEO','PASS' if seo_ok else 'FAIL','robots.txt и sitemap.xml присутствуют и связаны.' if seo_ok else 'robots/sitemap требуют исправления.',not seo_ok)

secret_patterns=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix.lower() in {'.png','.webp','.ico','.zip','.md','.txt'}: continue
    try: t=p.read_text(encoding='utf-8',errors='ignore')
    except: continue
    for m in re.finditer(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[\"']([^\"']{16,})[\"']",t):
        v=m.group(2).lower()
        if any(x in v for x in ['example','placeholder','change-me','use-a-long','your-','test-']): continue
        secret_patterns.append(f'{p.relative_to(ROOT)}:{m.group(1)}')
add('security.no_embedded_secrets','Security','PASS' if not secret_patterns else 'REVIEW','Явных production secrets в публичных файлах не обнаружено.' if not secret_patterns else 'Проверить возможные secrets: '+', '.join(secret_patterns[:8]),bool(secret_patterns))
add('security.https','Security','MANUAL','Перед live запуском backend и storefront должны работать только через HTTPS; проверяется после deployment.',True)
add('security.backup','Operations','BLOCKED','Не настроено реальное резервное копирование Orders DB и проверка восстановления.',True)
add('qa.mobile_checkout','QA','MANUAL','Нужен ручной тест 360–430 px: landing → product → cart → checkout → confirmation.',True)
add('qa.live_order','QA','BLOCKED','Live end-to-end заказ нельзя выполнить до активации хотя бы одного SKU, delivery credentials и payment method.',True)

blocking=[c for c in checks if c['blocking'] and c['status']!='PASS']
status={'stage':11,'launch_ready':len(blocking)==0,'summary':{'total_checks':len(checks),'pass':sum(c['status']=='PASS' for c in checks),'blocked':sum(c['status']=='BLOCKED' for c in checks),'fail':sum(c['status']=='FAIL' for c in checks),'manual':sum(c['status']=='MANUAL' for c in checks),'review':sum(c['status']=='REVIEW' for c in checks),'blocking_count':len(blocking)},'blocking_ids':[c['id'] for c in blocking],'checks':checks,'conclusion':'Architecture skeleton is coherent, but the store is not launch-ready until merchant identity/policies, active SKU commercial data, live delivery/payment credentials, HTTPS deployment, backups and mobile/live E2E are completed.'}
(ROOT/'docs/stage11-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(status,ensure_ascii=False,indent=2))
sys.exit(0 if not any(c['status']=='FAIL' for c in checks) else 2)
