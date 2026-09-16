from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from backend.services import product_cards_v3 as cards

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'var' / 'reports'


def _text(v) -> str:
    return str(v or '').strip()


def _norm_package(v) -> str:
    return ' '.join(_text(v).lower().replace(',', '.').split())


def main() -> None:
    affected_products = []
    affected_skus = 0
    total_products = 0
    total_skus = 0

    for summary in cards.list_cards():
        card = cards.get(str(summary.get('product_id') or ''))
        if not isinstance(card, dict):
            continue
        total_products += 1
        content = card.get('content') or {}
        sm = card.get('sku_media') or {}
        media = [m for m in (sm.get('media') or []) if isinstance(m, dict)]
        media_by_id = {str(m.get('media_id') or ''): m for m in media}
        skus = [s for s in (sm.get('skus') or []) if isinstance(s, dict) and s.get('enabled') is not False]
        total_skus += len(skus)

        groups = defaultdict(list)
        for sku in skus:
            mid = _text(sku.get('primary_media_id'))
            if not mid:
                continue
            row = media_by_id.get(mid) or {}
            path = _text(row.get('path'))
            key = path or mid
            groups[key].append({
                'sku_id': _text(sku.get('sku_id')),
                'sku_code': _text(sku.get('sku_code')),
                'package': _text(sku.get('package') or sku.get('label')),
                'package_norm': _norm_package(sku.get('package') or sku.get('label')),
                'media_id': mid,
                'path': path,
                'alt': _text(row.get('alt')),
            })

        collisions = []
        for key, members in groups.items():
            packages = {m['package_norm'] for m in members if m['package_norm']}
            if len(packages) <= 1:
                continue
            collisions.append({
                'media_key': key,
                'packages': sorted({m['package'] for m in members}),
                'skus': members,
            })
            affected_skus += len(members)

        if collisions:
            affected_products.append({
                'product_id': card.get('product_id'),
                'slug': card.get('slug'),
                'title': _text(content.get('title')),
                'brand': _text(content.get('brand')),
                'collisions': collisions,
            })

    result = {
        'schema_version': '1.0',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'rule': 'Different SKU packages of the same product must not share the same primary image/path.',
        'products_total': total_products,
        'skus_total': total_skus,
        'affected_products': len(affected_products),
        'affected_skus': affected_skus,
        'products': affected_products,
    }

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / 'pcv3-sku-photo-integrity-latest.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('BB610 PCV3 SKU PHOTO INTEGRITY AUDIT')
    print('PRODUCTS TOTAL:', total_products)
    print('SKU TOTAL:', total_skus)
    print('AFFECTED PRODUCTS:', len(affected_products))
    print('AFFECTED SKU:', affected_skus)
    print('--- AFFECTED PRODUCTS ---')
    for product in affected_products:
        print(f"{product['title']} | {product['slug']} | {product['product_id']}")
        for collision in product['collisions']:
            packages = ', '.join(collision['packages'])
            print(f"  SAME PRIMARY PHOTO -> {packages}")
            for sku in collision['skus']:
                print(f"    {sku['package']} | {sku['sku_id']} | {sku['path'] or sku['media_id']}")
    print('REPORT:', path)
    print('RESULT:', 'PASS' if not affected_products else 'REVIEW')


if __name__ == '__main__':
    main()
