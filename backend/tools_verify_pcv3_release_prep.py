from __future__ import annotations

import json
from pathlib import Path

from backend.db import connect
from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import find_master_for_card, source_metadata

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'var' / 'reports'


def _latest_report() -> dict | None:
    paths = sorted(REPORT_ROOT.glob('pcv3-release-prep-*.json'))
    if not paths:
        return None
    try:
        return json.loads(paths[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def main() -> None:
    cmap = cards.commerce_map()
    map_by_pid = {
        str(x.get('product_id') or ''): x
        for x in cmap.get('products', [])
        if isinstance(x, dict)
    }

    with connect() as con:
        commerce_keys = {
            str(r['sku'])
            for r in con.execute('SELECT sku FROM sku_commerce').fetchall()
        }

    total = 0
    source_verified = 0
    mapped_products = 0
    enabled_skus = 0
    bound_skus = 0
    photo_skus = 0
    schema_errors: list[str] = []
    unmapped: list[str] = []
    unbound: list[str] = []
    missing_commerce_rows: list[str] = []

    for summary in cards.list_cards():
        pid = str(summary.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            schema_errors.append(f'{pid}: missing')
            continue
        total += 1
        try:
            cards.validate(card)
        except Exception as exc:
            schema_errors.append(f'{pid}: {exc}')
            continue

        if source_metadata(find_master_for_card(card)).get('verified'):
            source_verified += 1

        mapping = map_by_pid.get(pid)
        if not mapping:
            unmapped.append(pid)
            continue
        mapped_products += 1
        links = {
            str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
            for x in mapping.get('skus') or []
            if isinstance(x, dict)
        }
        media_ids = {
            str(x.get('media_id') or '')
            for x in (card.get('sku_media') or {}).get('media') or []
            if isinstance(x, dict)
        }
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if sku.get('enabled') is False:
                continue
            enabled_skus += 1
            sid = str(sku.get('sku_id') or '')
            key = links.get(sid)
            if key:
                bound_skus += 1
                if key not in commerce_keys:
                    missing_commerce_rows.append(f'{pid}/{sid}->{key}')
            else:
                unbound.append(f'{pid}/{sid}')
            if sku.get('primary_media_id') in media_ids:
                photo_skus += 1

    latest = _latest_report()
    safety_ok = bool(
        latest and
        latest.get('mode') == 'APPLY_SAFE' and
        isinstance(latest.get('apply'), dict) and
        latest['apply'].get('preexisting_commerce_unchanged') is True and
        latest['apply'].get('new_drafts_safe') is True
    )

    structural_ok = (
        total > 0 and
        source_verified == total and
        mapped_products == total and
        bound_skus == enabled_skus and
        not missing_commerce_rows
    )
    ok = structural_ok and safety_ok and not schema_errors

    print('BB610 PCV3 RELEASE PREP VERIFY')
    print('V3 TOTAL:', total)
    print('MASTER SOURCE VERIFIED:', f'{source_verified}/{total}')
    print('COMMERCE PRODUCT MAPPING:', f'{mapped_products}/{total}')
    print('SKU BINDINGS:', f'{bound_skus}/{enabled_skus}')
    print('SKU PRIMARY PHOTO:', f'{photo_skus}/{enabled_skus}')
    print('SCHEMA ERRORS:', len(schema_errors))
    print('UNMAPPED PRODUCTS:', len(unmapped))
    print('UNBOUND SKU:', len(unbound))
    print('MISSING COMMERCE ROWS:', len(missing_commerce_rows))
    print('SAFE APPLY EVIDENCE:', 'PASS' if safety_ok else 'FAIL')
    print('STRUCTURAL COMMERCE COVERAGE:', 'PASS' if structural_ok else 'FAIL')
    print('PHOTO REMAINDER:', enabled_skus - photo_skus)
    if schema_errors:
        for x in schema_errors[:20]:
            print('  SCHEMA:', x)
    if unmapped:
        for x in unmapped[:20]:
            print('  UNMAPPED:', x)
    if unbound:
        for x in unbound[:20]:
            print('  UNBOUND:', x)
    if missing_commerce_rows:
        for x in missing_commerce_rows[:20]:
            print('  COMMERCE ROW:', x)
    print('RESULT:', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
