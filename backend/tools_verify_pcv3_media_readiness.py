from __future__ import annotations

import json
from pathlib import Path

from backend.db import connect
from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import find_master_for_card, source_metadata
from backend.services.product_cards_v3_media import _is_resolvable

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'var' / 'reports'
SELLABLE = {'in_stock', 'preorder', 'backorder'}


def _latest() -> dict | None:
    paths = sorted(REPORT_ROOT.glob('pcv3-media-readiness-*.json'))
    if not paths:
        return None
    try:
        return json.loads(paths[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def main() -> None:
    latest = _latest()
    report_ok = bool(latest and latest.get('mode') == 'APPLY_MEDIA_SAFE' and latest.get('commerce_unchanged') is True)
    cmap = cards.commerce_map()
    map_by_pid = {str(x.get('product_id') or ''): x for x in cmap.get('products', []) if isinstance(x, dict)}

    with connect() as con:
        commerce = {str(r['sku']): dict(r) for r in con.execute('SELECT sku,price,sale_price,availability,stock_qty,enabled FROM sku_commerce').fetchall()}

    total_cards = source_verified = mapped = 0
    total_sku = bound = photo = resolvable_photo = priced = sellable = ready = 0
    schema_errors: list[str] = []
    missing_media: list[str] = []
    invalid_media: list[str] = []
    missing_binding: list[str] = []
    missing_commerce: list[str] = []

    for row in cards.list_cards():
        pid = str(row.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            schema_errors.append(f'{pid}: missing card')
            continue
        total_cards += 1
        try:
            cards.validate(card)
        except Exception as exc:
            schema_errors.append(f'{pid}: {exc}')
            continue
        if source_metadata(find_master_for_card(card)).get('verified'):
            source_verified += 1
        mapping = map_by_pid.get(pid)
        if mapping:
            mapped += 1
        links = {str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '') for x in (mapping or {}).get('skus') or [] if isinstance(x, dict)}
        media = {str(x.get('media_id') or ''): x for x in (card.get('sku_media') or {}).get('media') or [] if isinstance(x, dict)}
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if sku.get('enabled') is False:
                continue
            total_sku += 1
            sid = str(sku.get('sku_id') or '')
            key = links.get(sid, '')
            if key:
                bound += 1
                if key not in commerce:
                    missing_commerce.append(f'{pid}/{sid}->{key}')
            else:
                missing_binding.append(f'{pid}/{sid}')
            mid = str(sku.get('primary_media_id') or '')
            m = media.get(mid)
            has_photo = bool(m)
            if has_photo:
                photo += 1
                path = str(m.get('path') or '')
                if path and _is_resolvable(path):
                    resolvable_photo += 1
                else:
                    invalid_media.append(f'{pid}/{sid}:{path}')
            else:
                missing_media.append(f'{pid}/{sid}')
            crow = commerce.get(key) if key else None
            price = None
            if crow:
                price = crow.get('sale_price') if crow.get('sale_price') is not None else crow.get('price')
            has_price = isinstance(price, (int, float)) and price > 0
            is_sellable = bool(crow and crow.get('enabled')) and has_price and str(crow.get('availability') or '') in SELLABLE
            priced += int(has_price)
            sellable += int(is_sellable)
            ready += int(has_photo and source_metadata(find_master_for_card(card)).get('verified') and is_sellable)

    current = {
        'products': total_cards,
        'sku_total': total_sku,
        'sku_with_photo': photo,
        'photo_remainder': total_sku - photo,
        'sku_with_price': priced,
        'sku_sellable': sellable,
        'sku_release_ready': ready,
    }
    summary_match = bool(latest and all((latest.get('summary') or {}).get(k) == v for k, v in current.items()))
    structural_ok = source_verified == total_cards and mapped == total_cards and bound == total_sku and not missing_commerce
    media_integrity_ok = photo == resolvable_photo and not invalid_media
    ok = report_ok and summary_match and structural_ok and media_integrity_ok and not schema_errors

    print('BB610 PCV3 MEDIA + READINESS VERIFY')
    print('V3 TOTAL:', total_cards)
    print('MASTER VERIFIED:', f'{source_verified}/{total_cards}')
    print('COMMERCE MAPPED:', f'{mapped}/{total_cards}')
    print('SKU BOUND:', f'{bound}/{total_sku}')
    print('PHOTO COVERAGE:', f'{photo}/{total_sku}')
    print('PHOTO REMAINDER:', total_sku - photo)
    print('PHOTO RESOLVABLE:', f'{resolvable_photo}/{photo}')
    print('SKU WITH PRICE:', f'{priced}/{total_sku}')
    print('SKU SELLABLE:', f'{sellable}/{total_sku}')
    print('SKU RELEASE READY:', f'{ready}/{total_sku}')
    print('SCHEMA ERRORS:', len(schema_errors))
    print('MISSING BINDINGS:', len(missing_binding))
    print('MISSING COMMERCE ROWS:', len(missing_commerce))
    print('INVALID MEDIA PATHS:', len(invalid_media))
    print('SAFE MEDIA REPORT:', 'PASS' if report_ok else 'FAIL')
    print('REPORT/CURRENT MATCH:', 'PASS' if summary_match else 'FAIL')
    print('STRUCTURAL COVERAGE:', 'PASS' if structural_ok else 'FAIL')
    print('MEDIA INTEGRITY:', 'PASS' if media_integrity_ok else 'FAIL')
    print('RESULT:', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
