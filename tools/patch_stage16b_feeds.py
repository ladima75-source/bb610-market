#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
p=root/'backend'/'services'/'catalog_feeds.py'
s=p.read_text(encoding='utf-8')
old="""def _title(p,s):
    base=((p.get('feed') or {}).get('title') or p.get('name') or s.get('product_id') or s.get('id')).strip()
    variant=(s.get('variant') or '').strip()
    return (base+' '+variant).strip()[:150]
"""
new="""def _title(p,s):
    sku_title=((s.get('feed') or {}).get('title') or '').strip()
    if sku_title:
        return sku_title[:150]
    base=((p.get('feed') or {}).get('title') or p.get('official_name') or p.get('name') or s.get('product_id') or s.get('id')).strip()
    variant=(s.get('variant') or '').strip()
    return (base+' '+variant).strip()[:150]
"""
if old in s:
    s=s.replace(old,new,1)
elif "sku_title=((s.get('feed')" not in s:
    raise SystemExit('ERROR: expected _title() block not found')
p.write_text(s,encoding='utf-8')
print('Stage 16B feed title preference applied')
