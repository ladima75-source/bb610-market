from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy

from backend.services import product_cards_v3 as svc
from backend.services.catalog_cms import admin_detail as catalog_detail
from backend.services.product_cards_v3_media import _is_resolvable

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data' / 'product_cards_v3'
PRODUCTS = BASE / 'products'
CMAP = BASE / 'commerce_map.json'
MANIFEST = BASE / 'migration_manifest.json'

EXPECTED = {
    'Kendal','Megafol','MASTER 15-5-30+2','MASTER 13-40-13','MASTER 20-20-20',
    'MASTER 3-11-38','MASTER 18-18-18','MASTER 17-6-18','PLANTAFOL 30-10-10',
    'PLANTAFOL 10-54-10','PLANTAFOL 20-20-20','PLANTAFOL 5-15-45','PLANTAFOL 0-25-50',
    'Nova PeKacid 0-60-20'
}


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def fail(msg: str):
    raise SystemExit('FAIL: ' + msg)


def commerce_snapshot(product_key: str):
    d = catalog_detail(product_key)
    if not d:
        return None
    return {
        'published': d.get('published'),
        'skus': [
            {
                'id': s.get('id') or s.get('sku'),
                'base_price': s.get('base_price'),
                'sale_price': s.get('sale_price'),
                'price': s.get('price'),
                'availability': s.get('availability'),
                'stock_qty': s.get('stock_qty'),
                'enabled': s.get('enabled'),
            }
            for s in (d.get('skus') or []) if isinstance(s, dict)
        ]
    }


def main():
    manifest = load(MANIFEST)
    rows = manifest.get('products') or []
    names = {str(x.get('name')) for x in rows if isinstance(x, dict)}
    if names != EXPECTED or len(rows) != 14:
        fail(f'manifest set mismatch: {len(rows)} rows')

    cmap = load(CMAP)
    map_by_pid = {x.get('product_id'): x for x in cmap.get('products', []) if isinstance(x, dict)}

    for row in rows:
        name = row['name']
        pid = row['product_id']
        path = PRODUCTS / f'{pid}.json'
        if not path.exists():
            fail(f'{name}: missing v3 file')
        card = load(path)
        svc.validate(card)
        if card.get('content', {}).get('title') is None:
            fail(f'{name}: missing title')
        mapping = map_by_pid.get(pid)
        if not mapping:
            fail(f'{name}: missing commerce map row')
        product_key = str(mapping.get('existing_product_key') or '')
        if not product_key:
            fail(f'{name}: missing existing_product_key')

        before = commerce_snapshot(product_key)
        if before is None:
            fail(f'{name}: existing product not found: {product_key}')

        sku_ids = {s.get('sku_id') for s in card.get('sku_media', {}).get('skus', [])}
        for sm in mapping.get('skus', []):
            if sm.get('sku_id') not in sku_ids:
                fail(f'{name}: commerce map references unknown v3 sku')
            key = str(sm.get('existing_commerce_sku_key') or '')
            if key:
                existing = {str(s.get('id')) for s in (catalog_detail(product_key) or {}).get('skus', [])}
                if key not in existing:
                    fail(f'{name}: mapped commerce SKU not found: {key}')

        for m in card.get('sku_media', {}).get('media', []):
            p = str(m.get('path') or '')
            if p and not _is_resolvable(p):
                fail(f'{name}: media path not resolvable: {p}')

        original = deepcopy(card)
        svc.put(pid, card)
        reopened = svc.get(pid)
        if reopened != original:
            fail(f'{name}: save/reopen mismatch')

        after = commerce_snapshot(product_key)
        if before != after:
            fail(f'{name}: commerce changed during v3 save/reopen')

        print(f'PASS | {name} | SKU={len(card["sku_media"]["skus"])} | MEDIA={len(card["sku_media"]["media"])}')

    print('PCV3 BATCH 01 TECHNICAL VERIFY PASS: 14/14')
    print('Schema/aliases: PASS')
    print('Save/reopen: PASS')
    print('Media refs: PASS')
    print('Commerce unchanged during verification: PASS')
    print('NOTE: UI visual/manual review is still required before final freeze.')


if __name__ == '__main__':
    main()
