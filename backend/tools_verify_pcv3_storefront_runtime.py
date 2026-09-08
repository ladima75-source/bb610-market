from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from backend import tools_migrate_pcv3_batch01 as migration
from backend.services import product_cards_v3 as v3
from backend.services.product_cards_v3_runtime import storefront_runtime

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    before_map = deepcopy(v3.commerce_map())
    before_manifest = (ROOT / 'data' / 'product_cards_v3' / 'migration_manifest.json').read_text(encoding='utf-8')

    cards = {x['slug']: x for x in v3.list_cards() if x.get('slug')}
    if len(cards) < len(migration.TARGETS):
        raise RuntimeError(f'Expected at least {len(migration.TARGETS)} v3 cards, got {len(cards)}')

    checked = []
    for row in v3.list_cards():
        slug = str(row.get('slug') or '')
        if not slug:
            continue
        runtime = storefront_runtime(slug)
        if not runtime:
            raise RuntimeError(f'{slug}: runtime returned no card (check publication/mapping)')
        if runtime.get('runtime_version') != '3.0' or runtime.get('source') != 'product-card-v3':
            raise RuntimeError(f'{slug}: wrong runtime identity')
        persisted = v3.get(str(row.get('product_id') or '')) or {}
        persisted_skus = [x for x in ((persisted.get('sku_media') or {}).get('skus') or []) if isinstance(x, dict) and x.get('enabled', True)]
        if len(runtime.get('skus') or []) != len(persisted_skus):
            raise RuntimeError(f'{slug}: runtime SKU count differs from persisted v3')
        for sku in runtime.get('skus') or []:
            if sku.get('commerce_bound'):
                if not sku.get('commerce') or not sku.get('commerce_key'):
                    raise RuntimeError(f'{slug}: bound SKU missing live commerce')
            else:
                if sku.get('commerce') is not None:
                    raise RuntimeError(f'{slug}: unbound SKU unexpectedly has commerce')
        b = runtime.get('commerce_binding') or {}
        if int(b.get('total') or 0) != len(runtime.get('skus') or []):
            raise RuntimeError(f'{slug}: binding totals inconsistent')
        checked.append((slug, len(runtime.get('skus') or []), int(b.get('bound') or 0), int(b.get('unbound') or 0)))

    after_map = v3.commerce_map()
    after_manifest = (ROOT / 'data' / 'product_cards_v3' / 'migration_manifest.json').read_text(encoding='utf-8')
    if before_map != after_map:
        raise RuntimeError('commerce_map changed during read-only verification')
    if before_manifest != after_manifest:
        raise RuntimeError('migration_manifest changed during read-only verification')

    js = (ROOT / 'assets' / 'js' / 'product-card-v2.js').read_text(encoding='utf-8')
    for needle in ('/api/v1/storefront/product-card-v3/', '/api/v1/storefront/product-card-v2/', 'commerce_bound'):
        if needle not in js:
            raise RuntimeError(f'frontend bridge marker missing: {needle}')

    print('PCV3-02 STOREFRONT RUNTIME VERIFY PASS')
    print(f'Cards checked: {len(checked)}')
    for slug, total, bound, unbound in checked:
        print(f'PASS | {slug} | SKU={total} | bound={bound} | unbound={unbound}')
    print('Commerce map unchanged: PASS')
    print('Migration manifest unchanged: PASS')
    print('Legacy v2 fallback marker: PASS')


if __name__ == '__main__':
    main()
