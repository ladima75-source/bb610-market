from __future__ import annotations

from collections import Counter

from backend.db import connect
from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import find_master_for_card, master_rows, source_metadata


def main() -> None:
    full: list[dict] = []
    schema_errors: list[str] = []
    source_rows: list[int] = []
    source_unverified: list[str] = []

    for row in cards.list_cards():
        pid = str(row.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            schema_errors.append(f'{pid}: missing card')
            continue
        full.append(card)
        try:
            cards.validate(card)
        except Exception as exc:
            schema_errors.append(f'{pid}: {exc}')
        meta = source_metadata(find_master_for_card(card))
        if not meta.get('verified'):
            source_unverified.append(pid)
            continue
        try:
            source_rows.append(int(meta.get('source_row')))
        except Exception:
            source_unverified.append(pid)

    expected_rows = sorted({int(x.get('source_row')) for x in master_rows() if x.get('source_row') is not None})
    actual_counter = Counter(source_rows)
    duplicates = sorted(row for row, n in actual_counter.items() if n > 1)
    missing_master_rows = sorted(set(expected_rows) - set(actual_counter))
    extra_source_rows = sorted(set(actual_counter) - set(expected_rows))

    cmap = cards.commerce_map()
    map_rows = [x for x in cmap.get('products', []) if isinstance(x, dict)]
    map_by_pid = {str(x.get('product_id') or ''): x for x in map_rows}
    active_ids = {str(x.get('product_id') or '') for x in full}
    orphan_mappings = sorted(pid for pid in map_by_pid if pid not in active_ids)
    unmapped = sorted(pid for pid in active_ids if pid not in map_by_pid)

    with connect() as con:
        commerce_keys = {str(r['sku']) for r in con.execute('SELECT sku FROM sku_commerce').fetchall()}

    enabled_skus = bound_skus = 0
    unbound: list[str] = []
    missing_commerce: list[str] = []
    duplicate_sku_ids: list[str] = []
    global_sku_ids: set[str] = set()

    for card in full:
        pid = str(card.get('product_id') or '')
        mapping = map_by_pid.get(pid) or {}
        links = {
            str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
            for x in mapping.get('skus') or [] if isinstance(x, dict)
        }
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if not isinstance(sku, dict) or sku.get('enabled') is False:
                continue
            enabled_skus += 1
            sid = str(sku.get('sku_id') or '')
            if sid in global_sku_ids:
                duplicate_sku_ids.append(sid)
            global_sku_ids.add(sid)
            key = links.get(sid, '')
            if not key:
                unbound.append(f'{pid}/{sid}')
                continue
            bound_skus += 1
            if key not in commerce_keys:
                missing_commerce.append(f'{pid}/{sid}->{key}')

    unique_identity_ok = (
        len(full) == len(expected_rows)
        and not duplicates
        and not missing_master_rows
        and not extra_source_rows
        and not source_unverified
    )
    commerce_ok = (
        len(map_by_pid) == len(full)
        and not orphan_mappings
        and not unmapped
        and bound_skus == enabled_skus
        and not unbound
        and not missing_commerce
    )
    ok = unique_identity_ok and commerce_ok and not schema_errors and not duplicate_sku_ids

    print('BB610 PCV3 IDENTITY R2 VERIFY')
    print('ACTIVE CARDS:', len(full))
    print('EXPECTED MASTER IDENTITIES:', len(expected_rows))
    print('VERIFIED SOURCE ROWS:', f'{len(source_rows)}/{len(full)}')
    print('DUPLICATE SOURCE ROWS:', len(duplicates))
    print('MISSING MASTER ROWS:', len(missing_master_rows))
    print('EXTRA SOURCE ROWS:', len(extra_source_rows))
    print('SCHEMA ERRORS:', len(schema_errors))
    print('COMMERCE PRODUCT MAPPING:', f'{len(map_by_pid)}/{len(full)}')
    print('ORPHAN V3 MAPPINGS:', len(orphan_mappings))
    print('SKU BINDINGS:', f'{bound_skus}/{enabled_skus}')
    print('MISSING COMMERCE ROWS:', len(missing_commerce))
    print('DUPLICATE ACTIVE SKU IDS:', len(duplicate_sku_ids))
    print('UNIQUE MASTER IDENTITY:', 'PASS' if unique_identity_ok else 'FAIL')
    print('STRUCTURAL COMMERCE COVERAGE:', 'PASS' if commerce_ok else 'FAIL')
    if duplicates:
        print('  DUP SOURCE ROWS:', ','.join(map(str, duplicates[:20])))
    if missing_master_rows:
        print('  MISSING MASTER ROWS:', ','.join(map(str, missing_master_rows[:20])))
    if orphan_mappings:
        for x in orphan_mappings[:20]:
            print('  ORPHAN MAP:', x)
    if unbound:
        for x in unbound[:20]:
            print('  UNBOUND:', x)
    print('RESULT:', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
