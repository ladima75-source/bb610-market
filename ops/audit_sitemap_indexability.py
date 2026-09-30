#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
SITE='https://market.bb610.com.ua'
SITEMAP=ROOT/'sitemap.xml'
REPORT=ROOT/'docs/ai_sales/SITEMAP_INDEXABILITY_AUDIT_20260930.json'
INDEXABLE_CATEGORIES=('nutrition','biostimulation','containers')

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

    category_links_checked=0
    category_missing_targets=[]
    category_noindex_targets=[]
    category_canonical_mismatches=[]
    category_test_artifacts=[]
    for category in INDEXABLE_CATEGORIES:
        category_path=ROOT/'categories'/category/'index.html'
        if not category_path.is_file():
            errors.append('missing_category:'+category)
            continue
        body=category_path.read_text(encoding='utf-8',errors='replace')
        if re.search(r'BB610 TEST ORDER|bb610-order-test|example-product|EXAMPLE-',body,re.I):
            category_test_artifacts.append(category)
            errors.append('test_artifact_in_category:'+category)
        hrefs=sorted(set(re.findall(r'href=["\'](products/[^"\']+/index\.html)["\']',body,re.I)))
        for href in hrefs:
            category_links_checked+=1
            target=ROOT/href
            public_url=SITE+'/'+href[:-len('index.html')]
            if not target.is_file():
                category_missing_targets.append({'category':category,'href':href})
                errors.append('category_missing_target:'+category+':'+href)
                continue
            target_body=target.read_text(encoding='utf-8',errors='replace')
            rm=re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)["\']',target_body,re.I)
            target_robots=(rm.group(1).lower() if rm else '')
            if 'noindex' in target_robots:
                category_noindex_targets.append({'category':category,'href':href})
                errors.append('category_noindex_target:'+category+':'+href)
            cm=re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']',target_body,re.I)
            canonical=(cm.group(1).strip() if cm else '')
            if canonical and canonical!=public_url:
                category_canonical_mismatches.append({'category':category,'href':href,'canonical':canonical,'expected':public_url})
                errors.append('category_canonical_mismatch:'+category+':'+href)

    report={
        'status':'PASS' if not errors else 'FAIL',
        'sitemap_urls':len(urls),
        'local_targets_checked':checked,
        'duplicate_urls':duplicates,
        'missing_local_targets':missing_local,
        'noindex_urls':noindex,
        'category_product_links_checked':category_links_checked,
        'category_missing_targets':category_missing_targets,
        'category_noindex_targets':category_noindex_targets,
        'category_canonical_mismatches':category_canonical_mismatches,
        'category_test_artifacts':category_test_artifacts,
        'errors':errors,
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if errors:
        raise SystemExit(1)

if __name__=='__main__':
    main()
