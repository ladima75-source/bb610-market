#!/usr/bin/env python3
from pathlib import Path
import re, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "/opt/bb610-market")
app=root/"backend/app.py"
txt=app.read_text(encoding="utf-8")

imp="from .stage22h_media_review_api import router as stage22h_media_review_router"
inc="app.include_router(stage22h_media_review_router)"

if imp not in txt:
    txt += "\n"+imp+"\n"
if inc not in txt:
    txt += inc+"\n"
app.write_text(txt,encoding="utf-8")
print("OK: backend/app.py patched")
