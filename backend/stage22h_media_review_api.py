from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import json, os, shutil, datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/admin/media-review", tags=["admin-media-review"])

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "var" / "import-reports"
MASTER_CANDIDATES = [
    ROOT / "data" / "product_cards.master.json",
    ROOT / "data" / "product-cards.master.json",
]

def _auth(authorization: Optional[str]):
    token = os.getenv("BB610_ADMIN_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="BB610_ADMIN_TOKEN is not configured")
    got = (authorization or "").replace("Bearer ", "", 1).strip()
    if got != token:
        raise HTTPException(status_code=401, detail="Unauthorized")

def _master_path() -> Path:
    for p in MASTER_CANDIDATES:
        if p.exists():
            return p
    raise HTTPException(status_code=500, detail="Product card master not found")

def _load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def _save_json(p: Path, obj: Any):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def _collection(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("products", "cards", "items"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                return list(v.values())
        return list(obj.values())
    return []

def _source_row(card: dict) -> Optional[int]:
    m = card.get("import_meta")
    if isinstance(m, dict):
        for k in ("organic_planet_source_row", "source_row"):
            try:
                if m.get(k) is not None:
                    return int(m.get(k))
            except Exception:
                pass
    return None

def _variants(card: dict) -> List[dict]:
    for k in ("variants", "skus", "offers"):
        v = card.get(k)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
        if isinstance(v, dict):
            return [x for x in v.values() if isinstance(x, dict)]
    return []

def _sku(v: dict) -> str:
    for k in ("sku", "id", "variant_id"):
        x = v.get(k)
        if isinstance(x, str) and x.strip():
            return x.strip()
    return ""

def _img(v: dict) -> str:
    for k in ("image", "image_url", "primary_image", "main_image", "photo", "photo_url", "thumbnail"):
        x = v.get(k)
        if isinstance(x, str) and x.strip():
            return x.strip()
    return ""

def _find_card(cards: List[dict], row: int) -> dict:
    for c in cards:
        if isinstance(c, dict) and _source_row(c) == row:
            return c
    raise HTTPException(status_code=404, detail=f"Card row {row} not found")

def _candidate_to_store(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="Empty candidate")
    if s.startswith("http://") or s.startswith("https://"):
        return s
    rel = s.lstrip("/")
    fs = ROOT / rel
    if not fs.exists():
        raise HTTPException(status_code=400, detail=f"Candidate file not found: {rel}")
    return rel

def _backup(master: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    bdir = ROOT / "var" / "media-review-backups" / ts
    bdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(master, bdir / master.name)
    return bdir

def _log(entry: dict):
    p = REPORTS / "stage22h_media_review_actions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    entry["at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _review_payload():
    p = REPORTS / "stage22j_exact_media_review_latest.json" if (REPORTS / "stage22j_exact_media_review_latest.json").exists() else REPORTS / "stage22g_manual_media_review_latest.json"
    if not p.exists():
        raise HTTPException(status_code=500, detail="Stage 22G report not found")
    data = _load_json(p)
    detail_csv = REPORTS / ("stage22j_exact_media_sku_review_latest.csv" if (REPORTS / "stage22j_exact_media_sku_review_latest.csv").exists() else "stage22g_manual_media_sku_review_latest.csv")
    details = []
    if detail_csv.exists():
        import csv
        with detail_csv.open("r", encoding="utf-8-sig", newline="") as f:
            details = list(csv.DictReader(f))
    return data, details

@router.get("")
def get_review(authorization: Optional[str] = Header(default=None)):
    _auth(authorization)
    data, details = _review_payload()
    master = _load_json(_master_path())
    cards = [x for x in _collection(master) if isinstance(x, dict)]
    current = {}
    for c in cards:
        sr = _source_row(c)
        if sr is None:
            continue
        current[sr] = { _sku(v): _img(v) for v in _variants(c) if _sku(v) }
    return {
        "ok": True,
        "summary": {
            "cards_requiring_attention": data.get("cards_requiring_attention", 0),
            "decision_groups": data.get("decision_groups", {}),
        },
        "cards": data.get("summary", []),
        "details": details,
        "current_images": current,
    }

class CommonApply(BaseModel):
    source_row: int
    candidate: str

class VariantApply(BaseModel):
    source_row: int
    sku: str
    candidate: str

@router.post("/apply-common")
def apply_common(body: CommonApply, authorization: Optional[str] = Header(default=None)):
    _auth(authorization)
    candidate = _candidate_to_store(body.candidate)
    master_path = _master_path()
    master = _load_json(master_path)
    cards = [x for x in _collection(master) if isinstance(x, dict)]
    card = _find_card(cards, body.source_row)
    changed = []
    preserved = []
    bdir = _backup(master_path)
    for v in _variants(card):
        sku = _sku(v)
        if not sku:
            continue
        old = _img(v)
        if old:
            preserved.append({"sku": sku, "image": old})
            continue
        v["image"] = candidate
        meta = v.setdefault("media_meta", {})
        if isinstance(meta, dict):
            meta["assigned_by"] = "stage22h_admin_common"
            meta["source_candidate"] = candidate
        changed.append(sku)
    _save_json(master_path, master)
    _log({"action":"apply_common","source_row":body.source_row,"candidate":candidate,"changed":changed,"preserved":preserved,"backup":str(bdir)})
    return {"ok": True, "changed": changed, "preserved": preserved, "backup": str(bdir)}

@router.post("/apply-variant")
def apply_variant(body: VariantApply, authorization: Optional[str] = Header(default=None)):
    _auth(authorization)
    candidate = _candidate_to_store(body.candidate)
    master_path = _master_path()
    master = _load_json(master_path)
    cards = [x for x in _collection(master) if isinstance(x, dict)]
    card = _find_card(cards, body.source_row)
    target = None
    for v in _variants(card):
        if _sku(v) == body.sku:
            target = v
            break
    if target is None:
        raise HTTPException(status_code=404, detail="SKU not found")
    old = _img(target)
    if old and old != candidate:
        raise HTTPException(status_code=409, detail=f"SKU already has different image: {old}")
    bdir = _backup(master_path)
    if not old:
        target["image"] = candidate
        meta = target.setdefault("media_meta", {})
        if isinstance(meta, dict):
            meta["assigned_by"] = "stage22h_admin_variant"
            meta["source_candidate"] = candidate
        _save_json(master_path, master)
        changed = True
    else:
        changed = False
    _log({"action":"apply_variant","source_row":body.source_row,"sku":body.sku,"candidate":candidate,"changed":changed,"backup":str(bdir)})
    return {"ok": True, "changed": changed, "backup": str(bdir)}

@router.get("/actions")
def actions(authorization: Optional[str] = Header(default=None)):
    _auth(authorization)
    p = REPORTS / "stage22h_media_review_actions.jsonl"
    if not p.exists():
        return {"ok": True, "items": []}
    items = []
    for line in p.read_text(encoding="utf-8").splitlines()[-200:]:
        try:
            items.append(json.loads(line))
        except Exception:
            pass
    return {"ok": True, "items": list(reversed(items))}
