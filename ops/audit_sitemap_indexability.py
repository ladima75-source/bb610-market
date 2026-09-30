#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
SITE='https://market.bb610.com.ua'
SITEMAP=ROOT/'sitemap.xml'
REPORT=ROOT/'docs/ai_sales/SITEMAP_INDEXABILITY_AUDIT_20260930.json'

def local_path(url:str):
    if not url.startswith(SITE):
        return None
    parsed=urlparse(url)
    rel=parsed.path.lstrip('/')
    if not rel:
        return ROOT/'index.html'
    if parsed.path.endswith('/'):
        return ROOT/rel/'index.html'
    return ROOT/rel

def main():
    raw=SITEMAP.read_text(encoding='utf-8')
    urls=re.findall(r'<loc>(.*?)</loc>',raw,re.S|re.I)
    errors=[]
    duplicates=sorted({u for u in urls if urls.count(u)>1})
    if duplicates:
        errors.extend('duplicate:'+u for u in duplicates)

    checked=0
    missing_local=[]
    noindex=[]
    for url in urls:
        p=local_path(url)
        if p is None:
            errors.append('external_url:'+url)
            continue
        if not p.is_file():
            missing_local.append(url)
            errors.append('missing_local:'+url)
            continue
        if p.suffix.lower() not in {'.html','.htm'}:
            checked+=1
            continue
        body=p.read_text(encoding='utf-8',errors='replace')
        m=re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)["\']',body,re.I)
        robots=(m.group(1).lower() if m else '')
        if 'noindex' in robots:
            noindex.append(url)
            errors.append('noindex_in_sitemap:'+url)
        checked+=1

    report={
        'status':'PASS' if not errors else 'FAIL',
        'sitemap_urls':len(urls),
        'local_targets_checked':checked,
        'duplicate_urls':duplicates,
        'missing_local_targets':missing_local,
        'noindex_urls':noindex,
        'errors':errors,
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if errors:
        raise SystemExit(1)

if __name__=='__main__':
    main()
