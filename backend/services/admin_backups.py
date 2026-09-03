
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import os,re

ROOT=Path(__file__).resolve().parents[2]

def _dir_size(path:Path):
    total=0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try: total+=p.stat().st_size
                except: pass
    except: pass
    return total

def _fmt_size(n):
    units=["B","KB","MB","GB"]
    v=float(n)
    for u in units:
        if v<1024 or u=="GB": return f"{v:.1f} {u}"
        v/=1024

def backups():
    rows=[]
    seen=set()
    candidates=[]
    candidates.extend(ROOT.glob(".stage*-backup-*"))
    for base in (ROOT/"var", ROOT/"data"):
        if base.exists():
            candidates.extend(base.rglob("*backup*"))
    for p in candidates:
        try:
            p=p.resolve()
            if p in seen or not p.exists(): continue
            seen.add(p)
            st=p.stat()
            rows.append({
                "name":p.name,
                "path":str(p.relative_to(ROOT)) if str(p).startswith(str(ROOT)) else str(p),
                "is_dir":p.is_dir(),
                "modified":datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                "size":_fmt_size(_dir_size(p) if p.is_dir() else st.st_size),
            })
        except: continue
    rows.sort(key=lambda x:x["modified"],reverse=True)
    return rows
