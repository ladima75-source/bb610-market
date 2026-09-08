from __future__ import annotations

import json
from pathlib import Path

from backend import tools_migrate_pcv3_batch01 as m
from backend.services.product_cards_v3 import validate

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / 'data' / 'product_cards_v3'
PRODUCTS = V3 / 'products'
COMMERCE_MAP = V3 / 'commerce_map.json'
MANIFEST = V3 / 'migration_manifest.json'


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def save(path: Path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def main() -> None:
    manifest = load(MANIFEST, {})
    if manifest.get('batch') != 'VALAGRO-01':
        raise RuntimeError('VALAGRO-01 migration manifest not found')

    cmap = load(COMMERCE_MAP, {'products': []})
    by_product = {
        x.get('product_id'): x
        for x in cmap.get('products', [])
        if isinstance(x, dict) and x.get('product_id')
    }

    rows = []
    for report in manifest.get('products', []):
        if not isinstance(report, dict):
            continue
        product_id = report.get('product_id')
        path = PRODUCTS / f'{product_id}.json'
        card = load(path, None)
        if not isinstance(card, dict):
            raise RuntimeError(f'{report.get("name")}: v3 card file missing')
        validate(card)

        skus = (card.get('sku_media') or {}).get('skus') or []
        media = (card.get('sku_media') or {}).get('media') or []
        media_ids = {x.get('media_id') for x in media if isinstance(x, dict)}
        for sku in skus:
            mid = sku.get('primary_media_id')
            if mid is not None and mid not in media_ids:
                raise RuntimeError(f'{report.get("name")}: broken media ref {mid}')

        mapping = by_product.get(product_id, {})
        bound = [x for x in mapping.get('skus', []) if isinstance(x, dict) and x.get('existing_commerce_sku_key')]
        total = len(skus)
        bound_count = len(bound)
        unbound = total - bound_count
        if total and bound_count == total:
            status = 'FULL'
        elif bound_count:
            status = 'PARTIAL'
        else:
            status = 'NONE'

        report['sku_count'] = total
        report['commerce_bound_sku_count'] = bound_count
        report['commerce_unbound_sku_count'] = unbound
        report['commerce_binding_status_final'] = status
        report['technical_verification'] = 'PASS'
        rows.append((report.get('name', ''), total, bound_count, unbound, status))

    if len(rows) != len(m.TARGETS):
        raise RuntimeError(f'Expected {len(m.TARGETS)} products, found {len(rows)}')

    manifest['status'] = 'TECHNICAL_PASS_VISUAL_REVIEW_PENDING'
    manifest['count'] = len(rows)
    manifest['technical_verification'] = 'PASS'
    manifest['visual_review'] = 'PENDING_ALL_14'
    manifest['notes'] = [
        'Kendal SKU/Photo UI manually reviewed after R3 and showed 3 SKUs with media.',
        'Commerce values are not written by PRODUCT CARD v3 migration/finalizer.',
        'Final freeze requires visual review of remaining cards and storefront behavior.',
    ]
    save(MANIFEST, manifest)

    print('PCV3 BATCH 01 FINAL STATUS')
    print(f'Cards: {len(rows)}/{len(m.TARGETS)}')
    print('Technical verification: PASS')
    print('Commerce binding:')
    for name, total, bound, unbound, status in rows:
        print(f'  {name}: {status} | SKU={total} | bound={bound} | unbound={unbound}')
    print('Manifest status: TECHNICAL_PASS_VISUAL_REVIEW_PENDING')
    print('No commerce write API was called by this tool.')


if __name__ == '__main__':
    main()
