from __future__ import annotations
from pathlib import Path
from typing import Optional
import base64, datetime, json, os, re, shutil

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/admin/manual-media", tags=["admin-manual-media"])

ROOT = Path(__file__).resolve().parents[1]
MASTER_CANDIDATES = [
    ROOT / "data" / "product_cards.master.json",
    ROOT / "data" / "product-cards.master.json",
]
ALLOWED_EXT={".jpg",".jpeg",".png",".webp",".avif"}
MAX_BYTES=15*1024*1024

def _auth(authorization: Optional[str]):
    token=os.getenv("BB610_ADMIN_TOKEN","").strip()
    got=(authorization or "").replace("Bearer ","",1).strip()
    if not token or got!=token:
        raise HTTPException(status_code=401,detail="Unauthorized")

def _master_path():
    for p in MASTER_CANDIDATES:
        if p.exists(): return p
    raise HTTPException(status_code=500,detail="Product master not found")

def _load(p): return json.loads(p.read_text(encoding="utf-8"))
def _save(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def _collection(obj):
    if isinstance(obj,list): return obj
    if isinstance(obj,dict):
        for k in ("products","cards","items"):
            v=obj.get(k)
            if isinstance(v,list): return v
            if isinstance(v,dict): return list(v.values())
        return list(obj.values())
    return []

def _source_row(card):
    m=card.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None:return int(m.get(k))
            except: pass
    return None

def _variants(card):
    for k in ("variants","skus","offers"):
        v=card.get(k)
        if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
        if isinstance(v,dict): return [x for x in v.values() if isinstance(x,dict)]
    return []

def _sku(v):
    for k in ("sku","id","variant_id"):
        x=v.get(k)
        if isinstance(x,str) and x.strip(): return x.strip()
    return ""

def _img(v):
    for k in ("image","image_url","primary_image","main_image","photo","photo_url","thumbnail"):
        x=v.get(k)
        if isinstance(x,str) and x.strip(): return x.strip()
    return ""

def _slug(s):
    s=str(s or "").lower()
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s[:60] or "product"

def _backup(master):
    ts=datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    b=ROOT/"var"/"manual-media-backups"/ts
    b.mkdir(parents=True,exist_ok=True)
    shutil.copy2(master,b/master.name)
    return b

def _find_card(cards,row):
    for c in cards:
        if isinstance(c,dict) and _source_row(c)==row:return c
    raise HTTPException(status_code=404,detail="Card not found")

@router.get("")
def list_missing(authorization: Optional[str]=Header(default=None)):
    _auth(authorization)
    obj=_load(_master_path())
    out=[]
    for c in _collection(obj):
        if not isinstance(c,dict): continue
        row=_source_row(c)
        if row is None: continue
        vv=_variants(c)
        missing=[v for v in vv if _sku(v) and not _img(v)]
        if not missing: continue
        out.append({
            "source_row":row,
            "name":c.get("name",""),
            "brand":c.get("brand",""),
            "total_variants":len(vv),
            "missing_variants":len(missing),
            "variants":[{
                "sku":_sku(v),
                "label":v.get("variant") or v.get("name") or v.get("label") or "",
                "image":_img(v)
            } for v in vv],
            "source_url":((c.get("sources") or {}).get("source_url","") if isinstance(c.get("sources"),dict) else "")
        })
    out.sort(key=lambda x:x["source_row"])
    return {"ok":True,"count":len(out),"cards":out}

class UploadBody(BaseModel):
    source_row:int
    filename:str
    content_base64:str

@router.post("/upload")
def upload(body:UploadBody,authorization: Optional[str]=Header(default=None)):
    _auth(authorization)
    ext=Path(body.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400,detail="Allowed: JPG/JPEG/PNG/WEBP/AVIF")
    try:
        raw=base64.b64decode(body.content_base64,validate=True)
    except Exception:
        raise HTTPException(status_code=400,detail="Invalid image payload")
    if not raw or len(raw)>MAX_BYTES:
        raise HTTPException(status_code=400,detail="Image must be <= 15 MB")

    master=_master_path()
    obj=_load(master)
    cards=[x for x in _collection(obj) if isinstance(x,dict)]
    card=_find_card(cards,body.source_row)
    missing=[v for v in _variants(card) if _sku(v) and not _img(v)]
    if not missing:
        return {"ok":True,"changed":0,"message":"No missing variants"}

    backup=_backup(master)
    outdir=ROOT/"assets"/"img"/"manual-products"
    outdir.mkdir(parents=True,exist_ok=True)
    name=f"row{body.source_row:02d}-{_slug(card.get('name',''))}{ext}"
    rel=f"assets/img/manual-products/{name}"
    (ROOT/rel).write_bytes(raw)

    changed=[]
    for v in missing:
        v["image"]=rel
        meta=v.setdefault("media_meta",{})
        if isinstance(meta,dict):
            meta["assigned_by"]="stage22l_manual_admin"
            meta["assigned_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
            meta["original_filename"]=body.filename
        changed.append(_sku(v))

    _save(master,obj)
    return {"ok":True,"changed":len(changed),"skus":changed,"image":rel,"backup":str(backup)}
