from __future__ import annotations
from pathlib import Path
from typing import Optional
import base64, datetime, json, os, re, shutil, subprocess

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

def _find_variant(card,sku):
    for v in _variants(card):
        if _sku(v)==sku:return v
    raise HTTPException(status_code=404,detail="SKU not found")

def _decode_image(filename,content_base64):
    ext=Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400,detail="Allowed: JPG/JPEG/PNG/WEBP/AVIF")
    try:
        raw=base64.b64decode(content_base64,validate=True)
    except Exception:
        raise HTTPException(status_code=400,detail="Invalid image payload")
    if not raw or len(raw)>MAX_BYTES:
        raise HTTPException(status_code=400,detail="Image must be <= 15 MB")
    return ext,raw

def _git_publish(paths, message):
    rels=[]
    for p in paths:
        p=Path(p)
        rels.append(str(p.relative_to(ROOT)) if p.is_absolute() else str(p))
    try:
        subprocess.run(["git","add","-f",*rels],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        diff=subprocess.run(["git","diff","--cached","--quiet"],cwd=ROOT)
        if diff.returncode==0:
            return {"ok":True,"committed":False,"message":"No git changes"}
        c=subprocess.run(["git","commit","-m",message],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        p=subprocess.run(["git","push"],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        return {"ok":True,"committed":True,"commit_output":c.stdout.strip(),"push_output":p.stdout.strip()}
    except subprocess.CalledProcessError as e:
        err=(e.stderr or e.stdout or str(e)).strip()
        raise HTTPException(status_code=500,detail=f"Saved locally, but git publish failed: {err}")

@router.get("")
def list_cards(authorization: Optional[str]=Header(default=None)):
    _auth(authorization)
    obj=_load(_master_path())
    out=[]
    for c in _collection(obj):
        if not isinstance(c,dict): continue
        row=_source_row(c)
        if row is None: continue
        vv=_variants(c)
        if not vv: continue
        imgs=[_img(v) for v in vv if _sku(v)]
        unique=sorted(set(x for x in imgs if x))
        out.append({
            "source_row":row,
            "name":c.get("name",""),
            "brand":c.get("brand",""),
            "total_variants":len(vv),
            "missing_variants":sum(1 for v in vv if _sku(v) and not _img(v)),
            "same_image_for_all": bool(unique) and len(unique)==1 and all(_img(v) for v in vv if _sku(v)),
            "variants":[{
                "sku":_sku(v),
                "label":v.get("variant") or v.get("name") or v.get("label") or "",
                "image":_img(v)
            } for v in vv if _sku(v)],
            "source_url":((c.get("sources") or {}).get("source_url","") if isinstance(c.get("sources"),dict) else "")
        })
    out.sort(key=lambda x:x["source_row"])
    return {"ok":True,"count":len(out),"cards":out}

class UploadSKUBody(BaseModel):
    source_row:int
    sku:str
    filename:str
    content_base64:str
    replace_existing:bool=False

@router.post("/upload-sku")
def upload_sku(body:UploadSKUBody,authorization: Optional[str]=Header(default=None)):
    _auth(authorization)
    ext,raw=_decode_image(body.filename,body.content_base64)

    master=_master_path()
    obj=_load(master)
    cards=[x for x in _collection(obj) if isinstance(x,dict)]
    card=_find_card(cards,body.source_row)
    v=_find_variant(card,body.sku)
    old=_img(v)
    if old and not body.replace_existing:
        raise HTTPException(status_code=409,detail=f"SKU already has image: {old}")

    backup=_backup(master)
    outdir=ROOT/"assets"/"img"/"manual-products"
    outdir.mkdir(parents=True,exist_ok=True)
    safe_sku=_slug(body.sku)
    name=f"row{body.source_row:02d}-{_slug(card.get('name',''))}-{safe_sku}{ext}"
    rel=f"assets/img/manual-products/{name}"
    img_path=ROOT/rel
    img_path.write_bytes(raw)

    v["image"]=rel
    meta=v.setdefault("media_meta",{})
    if isinstance(meta,dict):
        meta["assigned_by"]="stage22l_fix2_manual_sku"
        meta["assigned_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
        meta["original_filename"]=body.filename
        meta["replaced_image"]=old or ""

    _save(master,obj)
    pub=_git_publish([master,img_path], f"Update product image {body.sku}")
    return {"ok":True,"sku":body.sku,"image":rel,"old_image":old,"backup":str(backup),"published":pub}

class UploadCommonBody(BaseModel):
    source_row:int
    filename:str
    content_base64:str

@router.post("/upload-common-missing")
def upload_common_missing(body:UploadCommonBody,authorization: Optional[str]=Header(default=None)):
    _auth(authorization)
    ext,raw=_decode_image(body.filename,body.content_base64)
    master=_master_path()
    obj=_load(master)
    cards=[x for x in _collection(obj) if isinstance(x,dict)]
    card=_find_card(cards,body.source_row)
    targets=[v for v in _variants(card) if _sku(v) and not _img(v)]
    if not targets:
        return {"ok":True,"changed":0}

    backup=_backup(master)
    outdir=ROOT/"assets"/"img"/"manual-products"
    outdir.mkdir(parents=True,exist_ok=True)
    name=f"row{body.source_row:02d}-{_slug(card.get('name',''))}-common{ext}"
    rel=f"assets/img/manual-products/{name}"
    img_path=ROOT/rel
    img_path.write_bytes(raw)

    changed=[]
    for v in targets:
        v["image"]=rel
        meta=v.setdefault("media_meta",{})
        if isinstance(meta,dict):
            meta["assigned_by"]="stage22l_fix2_manual_common_missing"
            meta["assigned_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
            meta["original_filename"]=body.filename
        changed.append(_sku(v))

    _save(master,obj)
    pub=_git_publish([master,img_path], f"Update product images row {body.source_row}")
    return {"ok":True,"changed":len(changed),"skus":changed,"image":rel,"backup":str(backup),"published":pub}
