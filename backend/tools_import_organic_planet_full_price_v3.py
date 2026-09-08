from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend.services import product_cards_v3 as svc

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'catalog_sources' / 'organic_planet_full_price_v1.json'
BACKUPS = ROOT / 'var' / 'pcv3-backups'


def _norm(value: object) -> str:
    s = str(value or '').strip().lower().replace('ё', 'е')
    s = s.replace('+', ' plus ')
    s = re.sub(r'[^0-9a-zа-яіїєґ]+', ' ', s, flags=re.I)
    return ' '.join(s.split())


def _pack_key(value: object) -> str:
    s = str(value or '').strip().lower().replace('*', '')
    s = s.replace(',', '.')
    s = re.sub(r'\s+', ' ', s)
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*(?:мл|ml)\b', 'ml'),
        (r'(\d+(?:\.\d+)?)\s*(?:кг|kg)\b', 'kg'),
        (r'(\d+(?:\.\d+)?)\s*(?:г|g)\b', 'g'),
        (r'(\d+(?:\.\d+)?)\s*(?:л|l)\b', 'l'),
        (r'(\d+(?:\.\d+)?)\s*(?:шт|pcs?|pieces?)\b', 'pcs'),
    ]
    for pat, unit in patterns:
        m = re.search(pat, s, flags=re.I)
        if m:
            num = m.group(1)
            if num.endswith('.0'):
                num = num[:-2]
            return f'{num}{unit}'
    return _norm(s)


def _sku_pack_keys(card: dict) -> set[str]:
    out: set[str] = set()
    for sku in (card.get('sku_media') or {}).get('skus') or []:
        for value in (sku.get('label'), sku.get('package'), sku.get('sku_code')):
            key = _pack_key(value)
            if key:
                out.add(key)
    return out


def _new_product_id(slug: str) -> str:
    token = hashlib.sha256(('organic-planet-full-price|' + slug).encode('utf-8')).hexdigest()[:16]
    return f'prd_op_{token}'


def _new_sku_id(slug: str, pack: str) -> str:
    token = hashlib.sha256((f'organic-planet-full-price|{slug}|{_pack_key(pack)}').encode('utf-8')).hexdigest()[:18]
    return f'sku_op_{token}'


def _source() -> dict:
    obj = json.loads(SOURCE.read_text(encoding='utf-8'))
    products = obj.get('products') or []
    if len(products) != int(obj.get('expected_products') or -1):
        raise RuntimeError('Source product count does not match expected_products')
    sku_count = sum(len(x.get('packs') or []) for x in products)
    if sku_count != int(obj.get('expected_skus') or -1):
        raise RuntimeError('Source SKU count does not match expected_skus')
    return obj


def _full_cards() -> list[dict]:
    out = []
    for row in svc.list_cards():
        card = svc.get(str(row.get('product_id') or ''))
        if isinstance(card, dict):
            out.append(card)
    return out


def _match_product(src: dict, cards: list[dict]) -> dict | None:
    slug = str(src.get('slug') or '').strip().lower()
    by_slug = [c for c in cards if str(c.get('slug') or '').strip().lower() == slug]
    if len(by_slug) == 1:
        return by_slug[0]
    if len(by_slug) > 1:
        raise RuntimeError(f'Duplicate v3 slug: {slug}')

    aliases = [src.get('title')] + list(src.get('aliases') or [])
    alias_norms = {_norm(x) for x in aliases if _norm(x)}

    exact = []
    for card in cards:
        title = _norm((card.get('content') or {}).get('title'))
        card_slug = _norm(card.get('slug'))
        if title in alias_norms or card_slug in alias_norms:
            exact.append(card)
    unique = {c['product_id']: c for c in exact}
    if len(unique) == 1:
        return next(iter(unique.values()))
    if len(unique) > 1:
        raise RuntimeError(f'Ambiguous exact match for {src.get("title")}: {list(unique)}')

    # Safe fuzzy fallback only for sufficiently distinctive aliases. Short names
    # such as Kendal/Viva/Sweet are intentionally not substring-matched.
    fuzzy_aliases = [a for a in alias_norms if len(a.replace(' ', '')) >= 7]
    fuzzy = []
    for card in cards:
        title = _norm((card.get('content') or {}).get('title'))
        if any(a in title or title in a for a in fuzzy_aliases if title):
            fuzzy.append(card)
    unique = {c['product_id']: c for c in fuzzy}
    if len(unique) == 1:
        return next(iter(unique.values()))
    if len(unique) > 1:
        raise RuntimeError(f'Ambiguous fuzzy match for {src.get("title")}: {list(unique)}')
    return None


def _make_card(src: dict) -> dict:
    slug = str(src['slug']).strip().lower()
    skus = []
    for i, pack in enumerate(src.get('packs') or []):
        skus.append({
            'sku_id': _new_sku_id(slug, str(pack)),
            'sku_code': '',
            'label': str(pack).replace('*', '').strip(),
            'package': str(pack).replace('*', '').strip(),
            'primary_media_id': None,
            'gallery_media_ids': [],
            'sort_order': i,
            'enabled': True,
        })
    return {
        'schema_version': '3.0',
        'product_id': _new_product_id(slug),
        'slug': slug,
        'enabled': True,
        'content': {
            'title': str(src['title']).strip(),
            'brand': '',
            'category': str(src.get('category') or '').strip(),
            'short_description': '',
            'description': '',
            'benefits': [],
            'how_it_works': '',
            'application': '',
            'composition': '',
            'characteristics': [],
            'seo': {'title': '', 'description': ''},
        },
        'sku_media': {'skus': skus, 'media': []},
    }


def _merge_packs(card: dict, src: dict) -> int:
    existing = _sku_pack_keys(card)
    added = 0
    skus = (card.get('sku_media') or {}).setdefault('skus', [])
    for pack in src.get('packs') or []:
        key = _pack_key(pack)
        if key in existing:
            continue
        clean = str(pack).replace('*', '').strip()
        skus.append({
            'sku_id': _new_sku_id(str(src['slug']), clean),
            'sku_code': '',
            'label': clean,
            'package': clean,
            'primary_media_id': None,
            'gallery_media_ids': [],
            'sort_order': len(skus),
            'enabled': True,
        })
        existing.add(key)
        added += 1
    for i, sku in enumerate(skus):
        sku['sort_order'] = i
    return added


def _backup() -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = BACKUPS / f'before-organic-full-price-{stamp}'
    shutil.copytree(svc.BASE, dest)
    return dest


def main() -> int:
    source = _source()
    products = source['products']
    cards = _full_cards()

    plan: list[tuple[dict, dict | None]] = []
    claimed: dict[str, str] = {}
    for src in products:
        matched = _match_product(src, cards)
        if matched:
            pid = str(matched['product_id'])
            previous = claimed.get(pid)
            if previous and previous != src['slug']:
                raise RuntimeError(f'Two source products resolve to one v3 card: {previous}, {src["slug"]} -> {pid}')
            claimed[pid] = src['slug']
        plan.append((src, matched))

    backup = _backup()
    created = 0
    matched_count = 0
    added_skus = 0

    for src, matched in plan:
        if matched is None:
            card = _make_card(src)
            svc.validate(card)
            svc.create(card)
            cards.append(card)
            created += 1
            print(f'CREATE  {src["title"]}: {len(src.get("packs") or [])} SKU')
            continue

        matched_count += 1
        card = svc.get(matched['product_id'])
        if not card:
            raise RuntimeError(f'Card disappeared during import: {matched["product_id"]}')
        n = _merge_packs(card, src)
        if n:
            svc.validate(card)
            svc.put(card['product_id'], card)
            added_skus += n
            print(f'UPDATE  {src["title"]}: +{n} SKU')
        else:
            print(f'OK      {src["title"]}')

    # Verify the source master against the resulting v3 store.
    cards = _full_cards()
    covered_products = 0
    covered_skus = 0
    failures: list[str] = []
    for src in products:
        card = _match_product(src, cards)
        if not card:
            failures.append(f'missing product: {src["title"]}')
            continue
        covered_products += 1
        have = _sku_pack_keys(card)
        for pack in src.get('packs') or []:
            if _pack_key(pack) in have:
                covered_skus += 1
            else:
                failures.append(f'missing SKU: {src["title"]} / {pack}')

    total_v3_skus = sum(len((c.get('sku_media') or {}).get('skus') or []) for c in cards)
    print('---')
    print(f'SOURCE PRODUCTS: {covered_products}/{source["expected_products"]}')
    print(f'SOURCE SKU:      {covered_skus}/{source["expected_skus"]}')
    print(f'V3 TOTAL CARDS:  {len(cards)}')
    print(f'V3 TOTAL SKU:    {total_v3_skus}')
    print(f'MATCHED CARDS:   {matched_count}')
    print(f'CREATED CARDS:   {created}')
    print(f'ADDED SKU:       {added_skus}')
    print(f'BACKUP:          {backup}')
    print('COMMERCE WRITES: 0')

    if failures:
        for item in failures:
            print('FAIL:', item)
        return 2

    print('ORGANIC PLANET FULL PRICE -> PCV3: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
