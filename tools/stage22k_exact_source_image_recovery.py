#!/usr/bin/env python3
from pathlib import Path
import argparse, json, re, sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BAD_SOURCE = ("unverified_legacy_name","supplier_legacy_reference","legacy","source_conflict","conflict")
ALLOW_SOURCE = ("manufacturer","official","supplier_product_page","supplier_brand_product_page","supplier_market_product_page","registration_database_plus_market","current_","product_page")
BAD_IMAGE = ("logo","icon","favicon","sprite","placeholder","banner","avatar","loader","payment","visa","mastercard","facebook","instagram","youtube","telegram")
IMAGE_EXTS=(".jpg",".jpeg",".png",".webp",".avif")
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

def loadj(p): return json.loads(p.read_text(encoding="utf-8"))
def savej(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def coll(o):
    if isinstance(o,list): return o
    if isinstance(o,dict):
        for k in ("products","cards","items"):
            v=o.get(k)
            if isinstance(v,list): return v
            if isinstance(v,dict): return list(v.values())
        return list(o.values())
    return []
def row(c):
    m=c.get("import_meta") if isinstance(c,dict) else None
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None: return int(m.get(k))
            except: pass
    return None
def vars(c):
    for k in ("variants","skus","offers"):
        v=c.get(k)
        if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
        if isinstance(v,dict): return [x for x in v.values() if isinstance(x,dict)]
    return []
def image(o):
    if not isinstance(o,dict): return ""
    for k in ("image","image_url","primary_image","main_image","photo","photo_url","thumbnail"):
        x=o.get(k)
        if isinstance(x,str) and x.strip(): return x.strip()
    return ""
def card_has_image(c):
    return bool(image(c) or any(image(v) for v in vars(c)))
def slug(s):
    s=re.sub(r"[^a-z0-9а-яіїєґ]+","-",str(s or "").lower(),flags=re.I).strip("-")
    return s[:70] or "product"
def safe_source(c):
    src=c.get("sources") if isinstance(c.get("sources"),dict) else {}
    st=(src.get("source_type") or "").lower(); u=(src.get("source_url") or "").strip()
    if not u.startswith(("http://","https://")): return False,"no_http_source",u,st
    if u.lower().endswith(".pdf"): return False,"pdf_source",u,st
    if any(x in st for x in BAD_SOURCE): return False,"unsafe_source_type",u,st
    if st and not any(x in st for x in ALLOW_SOURCE): return False,"source_type_not_whitelisted",u,st
    return True,"ok",u,st
def fetch(url,max_bytes=8_000_000):
    req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8"})
    with urlopen(req,timeout=20) as r:
        ct=(r.headers.get("Content-Type") or "").lower(); data=r.read(max_bytes+1); final=r.geturl()
    if len(data)>max_bytes: raise ValueError("response_too_large")
    return data,ct,final
def candidates(html,base):
    t=html.decode("utf-8","ignore"); found=[]
    pats=[
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']']
    for p in pats:
        for m in re.finditer(p,t,re.I): found.append(("meta",urljoin(base,m.group(1).strip())))
    for m in re.finditer(r'<img\b[^>]*(?:src|data-src)=["\']([^"\']+)["\'][^>]*>',t,re.I):
        found.append(("img",urljoin(base,m.group(1).strip())))
    out=[]; seen=set()
    for kind,u in found:
        if not u or u in seen or u.startswith("data:"): continue
        seen.add(u); lu=u.lower()
        if any(x in lu for x in BAD_IMAGE): continue
        out.append((kind,u))
    return out
def valid_img(data,ct,u):
    if not ct.startswith("image/") and not urlparse(u).path.lower().endswith(IMAGE_EXTS): return False,"not_image"
    if len(data)<12000: return False,"too_small_file"
    try:
        from PIL import Image
        import io
        im=Image.open(io.BytesIO(data)); w,h=im.size
        if w<350 or h<350: return False,f"too_small_{w}x{h}"
        return True,f"{w}x{h}"
    except Exception:
        return True,"size_only"
def choose(page):
    data,ct,final=fetch(page)
    if "html" not in ct and "xhtml" not in ct: raise ValueError("source_not_html")
    for kind,u in candidates(data,final):
        try:
            b,ict,fu=fetch(u); ok,why=valid_img(b,ict,fu)
            if ok: return {"bytes":b,"ctype":ict,"url":fu,"why":why,"kind":kind}
        except Exception: pass
    raise ValueError("no_suitable_image")
def ext(ct,u):
    if "jpeg" in ct: return ".jpg"
    if "png" in ct: return ".png"
    if "webp" in ct: return ".webp"
    if "avif" in ct: return ".avif"
    s=Path(urlparse(u).path).suffix.lower()
    return s if s in IMAGE_EXTS else ".jpg"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="/opt/bb610-market"); ap.add_argument("--apply",action="store_true"); a=ap.parse_args()
    root=Path(a.root).resolve(); master=next((p for p in [root/"data/product_cards.master.json",root/"data/product-cards.master.json"] if p.exists()),None)
    if not master: raise SystemExit("ERROR: product card master not found")
    obj=loadj(master); cards=[c for c in coll(obj) if isinstance(c,dict) and row(c) is not None]; cards.sort(key=row)
    before=sum(1 for c in cards if not card_has_image(c))
    rep={"mode":"apply" if a.apply else "dry-run","cards_without_image_before":before,"cards_assigned":0,"variants_assigned":0,"skipped_unsafe_source":0,"fetch_failed":0,"no_suitable_image":0,"details":[]}
    outdir=root/"assets/img/official-source"; outdir.mkdir(parents=True,exist_ok=True) if a.apply else None
    for c in cards:
        if card_has_image(c): continue
        sr=row(c); ok,reason,url,st=safe_source(c)
        if not ok:
            rep["skipped_unsafe_source"]+=1; rep["details"].append({"row":sr,"name":c.get("name",""),"result":reason,"source_url":url}); continue
        try: im=choose(url)
        except Exception as e:
            if "no_suitable_image" in str(e): rep["no_suitable_image"]+=1; result="no_suitable_image"
            else: rep["fetch_failed"]+=1; result="fetch_failed"
            rep["details"].append({"row":sr,"name":c.get("name",""),"result":result,"error":str(e),"source_url":url}); continue
        rel=f"assets/img/official-source/row{sr:02d}-{slug(c.get('name',''))}{ext(im['ctype'],im['url'])}"
        if a.apply: (root/rel).write_bytes(im["bytes"])
        n=0
        for v in vars(c):
            if not image(v):
                if a.apply:
                    v["image"]=rel
                    m=v.setdefault("media_meta",{})
                    if isinstance(m,dict):
                        m.update({"assigned_by":"stage22k_exact_source_image_recovery","source_page":url,"source_image":im["url"],"assigned_at":datetime.now(timezone.utc).isoformat()})
                n+=1
        if n:
            rep["cards_assigned"]+=1; rep["variants_assigned"]+=n
            rep["details"].append({"row":sr,"name":c.get("name",""),"result":"assigned" if a.apply else "would_assign","variants":n,"stored":rel,"source_page":url,"source_image":im["url"],"check":im["why"]})
    if a.apply: savej(master,obj)
    after=sum(1 for c in cards if not card_has_image(c)) if a.apply else before-rep["cards_assigned"]
    rep["cards_without_image_after"]=after
    rdir=root/"var/import-reports"; rdir.mkdir(parents=True,exist_ok=True); rp=rdir/("stage22k_exact_source_image_apply_latest.json" if a.apply else "stage22k_exact_source_image_dryrun_latest.json")
    rp.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
    print("CARDS_WITHOUT_IMAGE_BEFORE:",before)
    print("CARDS_ASSIGNED:",rep["cards_assigned"])
    print("VARIANTS_ASSIGNED:",rep["variants_assigned"])
    print("SKIPPED_UNSAFE_SOURCE:",rep["skipped_unsafe_source"])
    print("FETCH_FAILED:",rep["fetch_failed"])
    print("NO_SUITABLE_IMAGE:",rep["no_suitable_image"])
    print("CARDS_WITHOUT_IMAGE_AFTER:",after)
    print("REPORT:",rp)
    print("IMPORTANT: prices/stock/availability/publication were NOT modified.")
if __name__=="__main__": main()
