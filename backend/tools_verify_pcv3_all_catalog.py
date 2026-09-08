from __future__ import annotations

from pathlib import Path

from backend.services import product_cards_v3 as svc
from backend.services.catalog_cms import admin_detail as catalog_detail, admin_list_products

EXCLUDED_IDS = {'bb610-order-test'}
ROOT = Path(__file__).resolve().parents[1]


def _eligible(row: dict, detail: dict) -> bool:
    pid = str(row.get('id') or detail.get('id') or '').strip()
    if not pid or pid in EXCLUDED_IDS:
        return False
    if detail.get('internal_only'):
        return False
    if str(detail.get('store_content_status') or '').lower() == 'internal-test':
        return False
    return True


def main() -> None:
    cards = svc.list_cards()
    cards_by_slug = {str(x.get('slug') or '').strip().lower(): x for x in cards}
    cmap = svc.commerce_map()
    map_rows = [x for x in cmap.get('products', []) if isinstance(x, dict)]
    map_by_catalog = {str(x.get('existing_product_key') or '').strip(): x for x in map_rows}

    failures: list[str] = []
    checked = 0
    full = partial = none = 0

    # Validate every stored v3 card and all media references inside the card.
    for row in cards:
        pid = str(row.get('product_id') or '')
        card = svc.get(pid)
        if not card:
            failures.append(f'{pid}: card file missing')
            continue
        try:
            svc.validate(card)
        except Exception as exc:
            failures.append(f'{pid}: schema invalid: {exc}')
            continue
        mids = {x.get('media_id') for x in (card.get('sku_media') or {}).get('media', []) if isinstance(x, dict)}
        for sku in (card.get('sku_media') or {}).get('skus', []):
            primary = sku.get('primary_media_id')
            if primary is not None and primary not in mids:
                failures.append(f'{pid}: SKU {sku.get("sku_id")} has unknown media {primary}')

    for row in admin_list_products():
        catalog_id = str(row.get('id') or '').strip()
        detail = catalog_detail(catalog_id) if catalog_id else None
        if not isinstance(detail, dict) or not _eligible(row, detail):
            continue
        checked += 1
        slug = str(row.get('slug') or detail.get('slug') or catalog_id).strip().lower()
        card_row = cards_by_slug.get(slug)
        mapping = map_by_catalog.get(catalog_id)
        if not card_row or not mapping:
            failures.append(f'{catalog_id}: missing v3 card or commerce map')
            continue
        if mapping.get('product_id') != card_row.get('product_id'):
            failures.append(f'{catalog_id}: product_id mismatch between card and commerce map')
            continue

        detail_skus = [x for x in (detail.get('skus') or []) if isinstance(x, dict)]
        real_keys = {str(x.get('id') or x.get('sku') or '').strip() for x in detail_skus if str(x.get('id') or x.get('sku') or '').strip()}
        bound = [x for x in mapping.get('skus', []) if isinstance(x, dict) and str(x.get('existing_commerce_sku_key') or '').strip()]
        bound_keys = {str(x.get('existing_commerce_sku_key') or '').strip() for x in bound}
        if not bound_keys.issubset(real_keys):
            failures.append(f'{catalog_id}: invented/unknown commerce SKU binding(s): {sorted(bound_keys - real_keys)}')
            continue

        card = svc.get(card_row['product_id']) or {}
        v3_skus = (card.get('sku_media') or {}).get('skus', [])
        if not v3_skus:
            failures.append(f'{catalog_id}: no v3 SKU')
            continue
        if real_keys and bound_keys == real_keys:
            full += 1
            status = 'FULL'
        elif bound_keys:
            partial += 1
            status = 'PARTIAL'
        else:
            none += 1
            status = 'NONE'
        print(f'PASS {catalog_id} | v3SKU={len(v3_skus)} | bound={len(bound_keys)}/{len(real_keys)} | {status}')

    # Ensure no duplicate catalog bindings or v3 ids exist.
    keys = [str(x.get('existing_product_key') or '').strip() for x in map_rows if str(x.get('existing_product_key') or '').strip()]
    if len(keys) != len(set(keys)):
        failures.append('commerce_map: duplicate existing_product_key')
    pids = [str(x.get('product_id') or '').strip() for x in map_rows if str(x.get('product_id') or '').strip()]
    if len(pids) != len(set(pids)):
        failures.append('commerce_map: duplicate product_id')

    print('PCV3 COMPLETE CATALOG VERIFY')
    print(f'ELIGIBLE={checked} V3_TOTAL={len(cards)} FULL={full} PARTIAL={partial} NONE={none}')
    if failures:
        print(f'FAILURES={len(failures)}')
        for line in failures:
            print('FAIL ' + line)
        raise SystemExit(2)
    print('SCHEMA/ALIASES: PASS')
    print('CATALOG COVERAGE: PASS')
    print('COMMERCE BINDINGS EXACT-ONLY: PASS')
    print('PCV3 COMPLETE CATALOG VERIFY PASS')


if __name__ == '__main__':
    main()
