#!/usr/bin/env python3
from pathlib import Path
import re, sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else "/opt/bb610-market")
p=ROOT/"backend/master_product_card_api.py"
t=p.read_text(encoding="utf-8")

marker="BB610_STAGE22M_FIX7_1_V1_BRIDGE"
if marker in t:
    print("OK: FIX7.1 already present")
    raise SystemExit(0)

helper = '''
# BB610_STAGE22M_FIX7_1_V1_BRIDGE
def _bb610_cards_collection(obj):
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for k in ("products", "cards", "items"):
            v=obj.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                return [x for x in v.values() if isinstance(x, dict)]
        return [x for x in obj.values() if isinstance(x, dict)]
    return []

def _bb610_find_full_card(slug):
    from pathlib import Path
    import json
    root=Path(__file__).resolve().parents[1]
    target=str(slug or "").strip().lower()
    for rel in ("data/product_cards.master.json","data/product-cards.master.json"):
        q=root/rel
        if not q.exists():
            continue
        try:
            obj=json.loads(q.read_text(encoding="utf-8"))
        except Exception:
            continue
        for c in _bb610_cards_collection(obj):
            vals=[c.get("slug"),c.get("id"),c.get("product_id"),c.get("code"),c.get("name"),c.get("official_name"),c.get("title")]
            if any(str(v or "").strip().lower()==target for v in vals):
                return c
    return None

def _bb610_text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (int,float)):
        return str(v)
    if isinstance(v, list):
        return "\\n".join(_bb610_text(x) for x in v if _bb610_text(x))
    if isinstance(v, dict):
        for k in ("text","body","description","intro","note","value"):
            x=_bb610_text(v.get(k))
            if x:
                return x
    return ""

def _bb610_bridge_v1(slug, current):
    if isinstance(current, dict):
        meaningful = any([
            _bb610_text(current.get("display_name")),
            _bb610_text(current.get("subtitle")),
            _bb610_text(current.get("lead")),
            _bb610_text(current.get("short_description")),
            _bb610_text(current.get("full_description")),
            bool(current.get("why")),
            _bb610_text((current.get("how_it_works") or {}).get("text") if isinstance(current.get("how_it_works"),dict) else ""),
            _bb610_text((current.get("application") or {}).get("intro") if isinstance(current.get("application"),dict) else ""),
        ])
        if meaningful:
            return current

    card=_bb610_find_full_card(slug)
    if not isinstance(card, dict):
        return current

    v=card.get("product_card_v2") if isinstance(card.get("product_card_v2"),dict) else {}

    why=v.get("why", card.get("why_product",""))
    if isinstance(why, dict):
        body=_bb610_text(why.get("text") or why.get("body"))
        why_rows=[{"title":_bb610_text(why.get("title") or "Чому продукт"),"text":body}] if body else []
    elif isinstance(why, list):
        why_rows=[]
        for x in why:
            if isinstance(x,dict):
                why_rows.append({"title":_bb610_text(x.get("title")),"text":_bb610_text(x.get("text") or x.get("body"))})
            elif _bb610_text(x):
                why_rows.append({"title":"","text":_bb610_text(x)})
    else:
        why_rows=[{"title":"Чому продукт","text":_bb610_text(why)}] if _bb610_text(why) else []

    how=v.get("how_it_works")
    if not isinstance(how,dict):
        how={"badge":"Як працює","title":"Як працює","text":_bb610_text(card.get("how_works",""))}
    else:
        how={"badge":_bb610_text(how.get("badge") or "Як працює"),"title":_bb610_text(how.get("title") or "Як працює"),"text":_bb610_text(how.get("text") or how.get("body"))}

    app=v.get("application")
    if not isinstance(app,dict):
        app={"enabled":True,"intro":_bb610_text(card.get("application","")),"rows":[],"note":"","market_note":""}
    else:
        app={"enabled":True,"intro":_bb610_text(app.get("intro") or card.get("application","")),"rows":app.get("rows") if isinstance(app.get("rows"),list) else [],"note":_bb610_text(app.get("note") or app.get("market_note")),"market_note":_bb610_text(app.get("market_note") or app.get("note"))}

    specs=v.get("specs")
    if not isinstance(specs,dict):
        txt=_bb610_text(card.get("characteristics",""))
        specs={"intro":txt,"note":"","rows":[{"label":"Характеристики","value":txt}] if txt else []}
    else:
        specs={"intro":_bb610_text(specs.get("intro") or card.get("characteristics","")),"note":_bb610_text(specs.get("note")),"rows":specs.get("rows") if isinstance(specs.get("rows"),list) else []}

    origin=v.get("origin")
    if not isinstance(origin,dict):
        origin={}
    origin={"brand":_bb610_text(origin.get("brand") or card.get("brand")),"company":_bb610_text(origin.get("company")),"manufacturer":_bb610_text(origin.get("manufacturer")),"country":_bb610_text(origin.get("country") or card.get("origin")),"official_url":_bb610_text(origin.get("official_url"))}

    docs=v.get("documents", card.get("documents",[]))
    if not isinstance(docs,list):
        docs=[]

    src=v.get("sources", card.get("sources",{}))
    if isinstance(src,list):
        src=src[0] if src and isinstance(src[0],dict) else {}
    if not isinstance(src,dict):
        src={}

    full=_bb610_text(v.get("full_description") or card.get("description"))
    short=_bb610_text(v.get("short_description") or card.get("short_description"))
    name=_bb610_text(v.get("name") or card.get("official_name") or card.get("name") or card.get("title"))

    return {
        "version":"2.0",
        "enabled":bool(v.get("enabled", card.get("enabled", False))),
        "eyebrow":_bb610_text(v.get("eyebrow")),
        "display_name":name,
        "name":name,
        "subtitle":_bb610_text(v.get("subtitle") or short),
        "lead":_bb610_text(v.get("lead") or short),
        "short_description":short,
        "full_description":full,
        "why":why_rows,
        "how_it_works":how,
        "application":app,
        "specs":specs,
        "origin":origin,
        "documents":docs,
        "sources":{"source_url":_bb610_text(src.get("source_url") or src.get("url")),"source_pdf":_bb610_text(src.get("source_pdf") or src.get("pdf"))},
        "related":v.get("related") if isinstance(v.get("related"),list) else [],
        "default_sku_id":_bb610_text(card.get("default_sku_id")),
        "revision":_bb610_text(v.get("revision")),
        "verified_date":_bb610_text(v.get("verified_date")),
        "verified":bool(v.get("verified",False)),
    }
'''

route_pos=t.find("@router.")
if route_pos<0:
    raise SystemExit("ERROR: router decorator not found")
t=t[:route_pos]+helper+"\n"+t[route_pos:]

pattern = re.compile(r'(@router\.get\([\'\"]/api/v1/admin/product-card-v1/\{slug\}[\'\"]\)\s*\ndef\s+admin_get\([^\n]*\):\s*\n(?:[^\n]*\n){0,10}?\s*)return\s+s')
m=pattern.search(t)
if not m:
    raise SystemExit("ERROR: admin_get return s not found; refusing blind patch")

t=t[:m.start()]+m.group(1)+"return _bb610_bridge_v1(slug, s)"+t[m.end():]

if marker not in t or "_bb610_bridge_v1(slug, s)" not in t:
    raise SystemExit("ERROR: FIX7.1 validation failed")

p.write_text(t,encoding="utf-8")
print("OK: admin product-card-v1 endpoint bridged")
print("MARKER:",marker)
