#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else "/opt/bb610-market")
p=ROOT/"admin/product-card-v2-editor.js"
t=p.read_text(encoding="utf-8")
marker="BB610_STAGE22M_FIX9_V2_CONTENT_PHOTOS"
anchor="const app=v.application||{}, how=v.how_it_works||{}, origin=v.origin||{}, src=(Array.isArray(v.sources)?(v.sources[0]||{}):(v.sources||{}));"
if marker not in t:
    if anchor not in t:
        raise SystemExit("ERROR: V2 renderer anchor not found")
    inject="/* BB610_STAGE22M_FIX9_V2_CONTENT_PHOTOS */\ntry{\n  const card=await api('/api/v1/admin/product-cards/'+encodeURIComponent(id));\n  if(card && typeof card==='object'){\n    const empty=x=>x==null||x===''||(Array.isArray(x)&&x.length===0)||(x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length===0);\n    const txt=x=>typeof x==='string'?x.trim():'';\n\n    if(empty(v.name)) v.name=card.official_name||card.name||card.title||'';\n    if(empty(v.short_description)) v.short_description=card.short_description||card.summary||'';\n    if(empty(v.subtitle)) v.subtitle=v.short_description||'';\n    if(empty(v.lead)) v.lead=v.short_description||'';\n    if(empty(v.full_description)) v.full_description=card.description||card.full_description||card.long_description||'';\n\n    if(empty(v.why) || (Array.isArray(v.why)&&!v.why.length)){\n      const w=card.why_product||card.why||card.benefits||'';\n      if(txt(w)) v.why=[{title:'Чому продукт',text:w}];\n    }\n    if(empty(v.how_it_works) || !txt(v.how_it_works?.text)){\n      const h=card.how_works||card.mechanism||card.mechanism_of_action||'';\n      if(txt(h)) v.how_it_works={title:'Як працює',badge:'Як працює',text:h};\n    }\n    if(empty(v.application) || !txt(v.application?.intro)){\n      const a=typeof card.application==='string'?card.application:(card.usage||card.use||card.recommendations||'');\n      if(txt(a)) v.application={enabled:true,intro:a,rows:[],note:'',market_note:''};\n    }\n    if(empty(v.specs) || !txt(v.specs?.intro)){\n      const s=typeof card.characteristics==='string'?card.characteristics:(card.specifications||card.properties||'');\n      if(txt(s)) v.specs={intro:s,rows:[{label:'Характеристики',value:s}],note:''};\n    }\n    if(empty(v.origin) || Object.keys(v.origin||{}).length===0){\n      v.origin={brand:card.brand||'',country:card.origin||card.country||'',company:'',manufacturer:'',official_url:''};\n    }\n    if(empty(v.documents)) v.documents=Array.isArray(card.documents)?card.documents:[];\n    if(empty(v.sources)) v.sources=card.sources||{};\n  }\n}catch(e){\n  console.warn('BB610 FIX9 content fallback failed',e);\n}\n"
    t=t.replace(anchor, inject+"\n"+anchor, 1)
p.write_text(t,encoding="utf-8")
p2=ROOT/"admin/product-cards.js"
s=p2.read_text(encoding="utf-8")
if "const bb610Img=" not in s:
    needle="const token=()=>$('#token').value.trim();"
    helper="const token=()=>$('#token').value.trim();\nconst bb610Img=x=>{\n  if(!x) return '';\n  if(typeof x==='string'){\n    const v=x.trim();\n    if(!v) return '';\n    if(/^https?:\\/\\//i.test(v) || v.startsWith('/')) return v;\n    if(v.startsWith('assets/')) return '/'+v;\n    return v;\n  }\n  if(typeof x==='object') return bb610Img(x.local||x.url||x.src||x.image||x.image_url||'');\n  return '';\n};\nconst bb610CardImg=c=>{\n  const direct=bb610Img(c&&c.image);\n  if(direct) return direct;\n  const g=c&&c.gallery;\n  if(g){\n    const arr=Array.isArray(g)?g:(Array.isArray(g.local)?g.local:[]);\n    for(const x of arr){ const u=bb610Img(x); if(u) return u; }\n  }\n  const v2=c&&c.product_card_v2;\n  if(v2&&Array.isArray(v2.sku_photo)){\n    for(const x of v2.sku_photo){ const u=bb610Img(x&&x.image); if(u) return u; }\n  }\n  return '';\n};"
    if needle in s:
        s=s.replace(needle,helper,1)
    else:
        s=helper+"\n"+s
old1="${esc(cardImg(x)||'/assets/img/placeholder.svg')}"
new1="${esc(bb610CardImg(x)||'/assets/img/placeholder.svg')}"
old2="${esc(x.image||'/assets/img/placeholder.svg')}"
new2="${esc(bb610CardImg(x)||'/assets/img/placeholder.svg')}"
s=s.replace(old1,new1).replace(old2,new2)
p2.write_text(s,encoding="utf-8")
print("OK: V2 content + photo rendering patched")
