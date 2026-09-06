#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else "/opt/bb610-market")
p=ROOT/"admin/product-card-v2-editor.js"
t=p.read_text(encoding="utf-8")

marker="BB610_STAGE22M_FIX6_FETCH_FULL_CARD"
if marker in t:
    print("OK: FIX6 already present")
    raise SystemExit(0)

old="""/* BB610_STAGE22M_FIX5_NESTED_V2_RENDER */
const v=(d&&d.product_card_v2&&typeof d.product_card_v2==='object')?d.product_card_v2:d;
const app=v.application||{}, how=v.how_it_works||{}, origin=v.origin||{}, src=(Array.isArray(v.sources)?(v.sources[0]||{}):(v.sources||{}));"""

if old not in t:
    raise SystemExit("ERROR: FIX5 renderer block not found; refusing blind patch")

new="""/* BB610_STAGE22M_FIX5_NESTED_V2_RENDER */
/* BB610_STAGE22M_FIX6_FETCH_FULL_CARD */
let v=(d&&d.product_card_v2&&typeof d.product_card_v2==='object')?d.product_card_v2:d;
try{
  const full=await api('/api/v1/admin/product-cards/'+encodeURIComponent(id));
  if(full&&full.product_card_v2&&typeof full.product_card_v2==='object'){
    v=full.product_card_v2;
  }
}catch(e){
  console.warn('BB610 FIX6 full-card fetch failed',e);
}
const app=v.application||{}, how=v.how_it_works||{}, origin=v.origin||{}, src=(Array.isArray(v.sources)?(v.sources[0]||{}):(v.sources||{}));"""

t=t.replace(old,new,1)

if marker not in t:
    raise SystemExit("ERROR: FIX6 marker missing after patch")
if "/api/v1/admin/product-cards/" not in t:
    raise SystemExit("ERROR: full-card route missing after patch")

p.write_text(t,encoding="utf-8")
print("OK: V2 renderer now fetches full product card directly")
print("MARKER:",marker)
