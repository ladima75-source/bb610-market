#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1] if len(sys.argv)>1 else "/opt/bb610-market")/"backend/app.py"
t=p.read_text(encoding="utf-8")
imp="from .stage22l_manual_media_api import router as stage22l_manual_media_router"
inc="app.include_router(stage22l_manual_media_router)"
if imp not in t:t+="\n"+imp+"\n"
if inc not in t:t+=inc+"\n"
p.write_text(t,encoding="utf-8")
print("OK: app patched")
