#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

CASES={
    "catalog.html":{
        "title":"Каталог · BB610 Market",
        "description":"Каталог BB610 Market: професійне живлення, біостимуляція та контейнери.",
        "h1":"Каталог",
        "canonical":"https://market.bb610.com.ua/catalog.html",
        "fixed":None,
    },
    "catalog-nutrition.html":{
        "title":"Професійні добрива для рослин — BB610 Market",
        "description":"Професійні добрива для рослин у BB610 Market. Ціни, фасування, характеристики та дані виробника. Доставка по Україні та самовивіз у Дніпрі.",
        "h1":"Професійні добрива для рослин",
        "canonical":"https://market.bb610.com.ua/catalog.html?category=nutrition",
        "fixed":"nutrition",
    },
    "catalog-biostimulation.html":{
        "title":"Біостимулятори для рослин — BB610 Market",
        "description":"Біостимулятори для рослин у BB610 Market. Ціни, фасування, характеристики та дані виробника. Доставка по Україні та самовивіз у Дніпрі.",
        "h1":"Біостимулятори для рослин",
        "canonical":"https://market.bb610.com.ua/catalog.html?category=biostimulation",
        "fixed":"biostimulation",
    },
}

for name,cfg in CASES.items():
    text=(ROOT/name).read_text(encoding="utf-8")
    assert f"<title>{cfg['title']}</title>" in text, name
    assert f'<meta name="description" content="{cfg["description"]}">' in text, name
    assert f'<link rel="canonical" href="{cfg["canonical"]}">' in text, name
    assert re.search(r"<h1[^>]*>"+re.escape(cfg["h1"])+r"</h1>",text), name
    if cfg["fixed"]:
        assert f"window.BB610_CATEGORY_ID=\"{cfg['fixed']}\";" in text, name
    else:
        assert "window.BB610_CATEGORY_ID=" not in text, name
    assert "js/catalog.js?v=20261001-category-seo-1" in text, name

js=(ROOT/"js/catalog.js").read_text(encoding="utf-8")
assert "const categoryLandingMeta={" in js
assert "categoryLandingMeta[initialCategory]||null" in js
assert "categoryLandingMeta[initialCategory]||null" in js
assert "category=nutrition" in js
assert "category=biostimulation" in js

robots=(ROOT/"robots.txt").read_text(encoding="utf-8")
assert "Disallow: /catalog-nutrition.html" in robots
assert "Disallow: /catalog-biostimulation.html" in robots

print("CATALOG CATEGORY SEO SOURCE: PASS")
print("GENERAL CATALOG META: PASS")
print("NUTRITION TEMPLATE META/H1/CANONICAL: PASS")
print("BIOSTIMULATION TEMPLATE META/H1/CANONICAL: PASS")
print("QUERY CATEGORY FILTER CONTRACT: PRESERVED")
