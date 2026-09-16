from __future__ import annotations

import json
from pathlib import Path

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_media import _is_resolvable
from backend.services.product_cards_v3_preprice import preprice_report

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'var' / 'reports'


def _latest() -> dict | None:
    paths = sorted(REPORT_ROOT.glob('pcv3-preprice-web-media-*.json'))
    if not paths:
        return None
    try:
        return json.loads(paths[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def main() -> None:
    report = preprice_report()
    summary = report.get('summary') or {}
    latest = _latest()

    total_cards = int(summary.get('cards_total') or 0)
    ready_cards = int(summary.get('cards_preprice_ready') or 0)
    total_skus = int(summary.get('skus_total') or 0)
    ready_skus = int(summary.get('skus_preprice_ready') or 0)
    gaps_total = int(summary.get('gaps_total') or 0)
    collisions = int(summary.get('identity_collision_groups') or 0)

    invalid_primary: list[str] = []
    missing_primary: list[str] = []
    empty_alt: list[str] = []
    for row in cards.list_cards():
        pid = str(row.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            continue
        media = {
            str(x.get('media_id') or ''): x
            for x in (card.get('sku_media') or {}).get('media') or []
            if isinstance(x, dict)
        }
        for sku in (card.get('sku_media') or {}).get('skus') or []:
            if not isinstance(sku, dict) or sku.get('enabled') is False:
                continue
            sid = str(sku.get('sku_id') or '')
            mid = str(sku.get('primary_media_id') or '')
            item = media.get(mid)
            if not item:
                missing_primary.append(f'{pid}/{sid}')
                continue
            path = str(item.get('path') or '').strip()
            if not path or not _is_resolvable(path):
                invalid_primary.append(f'{pid}/{sid}:{path}')
            if not str(item.get('alt') or '').strip():
                empty_alt.append(f'{pid}/{sid}:{mid}')

    evidence_ok = bool(
        latest
        and latest.get('mode') == 'APPLY_SAFE'
        and latest.get('commerce_unchanged') is True
        and latest.get('preprice_complete') is True
        and int(latest.get('photo_gaps_before') or 0) > 0
        and int(latest.get('sku_primary_media_assigned') or 0) == int(latest.get('photo_gaps_before') or -1)
    )
    current_ok = bool(
        summary.get('complete') is True
        and total_cards == ready_cards
        and total_skus == ready_skus
        and gaps_total == 0
        and collisions == 0
        and not missing_primary
        and not invalid_primary
        and not empty_alt
    )
    ok = evidence_ok and current_ok

    print('BB610 PCV3 FINAL PRE-PRICE VERIFY')
    print('CARDS PREPRICE READY:', f'{ready_cards}/{total_cards}')
    print('SKU PREPRICE READY:', f'{ready_skus}/{total_skus}')
    print('GAPS:', gaps_total)
    print('IDENTITY COLLISIONS:', collisions)
    print('MISSING PRIMARY MEDIA:', len(missing_primary))
    print('INVALID PRIMARY MEDIA:', len(invalid_primary))
    print('EMPTY MEDIA ALT:', len(empty_alt))
    print('PRICE GATE:', 'FROZEN / NOT EVALUATED')
    print('COMMERCE/PRICE SAFETY EVIDENCE:', 'PASS' if evidence_ok else 'FAIL')
    print('PRE-PRICE 100%:', 'PASS' if current_ok else 'FAIL')
    if missing_primary:
        for value in missing_primary[:20]:
            print('  MISSING:', value)
    if invalid_primary:
        for value in invalid_primary[:20]:
            print('  INVALID:', value)
    if empty_alt:
        for value in empty_alt[:20]:
            print('  ALT:', value)
    print('RESULT:', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
