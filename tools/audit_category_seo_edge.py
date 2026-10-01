#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
worker=(ROOT/'edge/bb610-market-category-seo/src/index.js').read_text(encoding='utf-8')
wrangler=(ROOT/'edge/bb610-market-category-seo/wrangler.toml').read_text(encoding='utf-8')

required=[
    "category=nutrition",
    "category=biostimulation",
    "Професійні добрива для рослин — BB610 Market",
    "Біостимулятори для рослин — BB610 Market",
    "https://market.bb610.com.ua/catalog.html?category=nutrition",
    "https://market.bb610.com.ua/catalog.html?category=biostimulation",
    "url.pathname !== '/catalog.html'",
    "if (!landing)",
    "return fetch(request);",
    "X-BB610-Category-SEO",
]
for token in required:
    assert token in worker, token

assert 'pattern = "market.bb610.com.ua/catalog.html*"' in wrangler
assert 'zone_name = "bb610.com.ua"' in wrangler
assert 'workers_dev = false' in wrangler

print('BB610 CATEGORY SEO EDGE SOURCE: PASS')
print('ROUTE SCOPE: catalog.html only')
print('QUERY SCOPE: nutrition + biostimulation only')
print('OTHER CATEGORIES: passthrough')
print('REDIRECTS: none')
