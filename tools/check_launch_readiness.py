#!/usr/bin/env python3
import re,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
required_pages=['contacts.html','delivery.html','payment.html','returns.html','terms.html','privacy.html','about.html']
issues=[]
for x in required_pages:
    if not (ROOT/x).exists(): issues.append('missing:'+x)
text=(ROOT/'config/store-info.js').read_text(encoding='utf-8')
for k in ['legal_name','edrpou_or_tax_id','registered_address','phone','email']:
    if re.search(rf'{k}:null',text): issues.append('seller_missing:'+k)
for k in ['window_days','return_method','return_shipping_payer','refund_timing']:
    if re.search(rf'{k}:null',text): issues.append('returns_missing:'+k)
status={'stage':10,'launch_ready':not issues,'issues':issues,'note':'Legal/policy templates are structural only until real merchant details and policies are supplied.'}
(ROOT/'docs/stage10-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(status,ensure_ascii=False,indent=2))
