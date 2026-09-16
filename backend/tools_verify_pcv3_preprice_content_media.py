from __future__ import annotations

import json
from pathlib import Path

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_media import _is_resolvable
from backend.services.product_cards_v3_preprice import preprice_report

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'var' / 'reports'


def _latest() -> dict | None:
    paths = sorted(REPORT_ROOT.glob('pcv3-preprice-content-media-*.json'))
    if not paths:
        return None
    try:
        return json.loads(paths[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def main() -> None:
    report = preprice_report()
    summary = report.get('summary') or {}
    issues = summary.get('issue_counts') or {}
    schema_errors = []
    alt_missing = []
    invalid_media = []
    media_total = 0

    for row in cards.list_cards():
        pid = str(row.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            schema_errors.append(f'{pid}: missing card')
            continue
        try:
            cards.validate(card)
        except Exception as exc:
            schema_errors.append(f'{pid}: {exc}')
            continue
        for media in (card.get('sku_media') or {}).get('media') or []:
            if not isinstance(media, dict):
                continue
            media_total += 1
            mid = str(media.get('media_id') or '')
            path = str(media.get('path') or '').strip()
            if not str(media.get('alt') or '').strip():
                alt_missing.append(f'{pid}/{mid}')
            if path and not _is_resolvable(path):
                invalid_media.append(f'{pid}/{mid}:{path}')

    latest = _latest()
    safety_ok = bool(
        latest and latest.get('mode') == 'APPLY_SAFE'
        and latest.get('commerce_db_unchanged') is True
        and latest.get('commerce_map_unchanged') is True
    )
    content_ok = int(issues.get('composition_missing', 0) or 0) == 0 and int(issues.get('seo_incomplete', 0) or 0) == 0
    media_meta_ok = not alt_missing and not invalid_media
    ok = safety_ok and content_ok and media_meta_ok and not schema_errors

    print('BB610 PCV3 PREPRICE CONTENT + MEDIA VERIFY')
    print('CARDS:', summary.get('cards_total'))
    print('SKU:', summary.get('skus_total'))
    print('COMPOSITION MISSING:', issues.get('composition_missing', 0))
    print('SEO INCOMPLETE:', issues.get('seo_incomplete', 0))
    print('PHOTO MISSING:', issues.get('photo_missing', 0))
    print('MEDIA TOTAL:', media_total)
    print('MEDIA ALT MISSING:', len(alt_missing))
    print('INVALID MEDIA:', len(invalid_media))
    print('SCHEMA ERRORS:', len(schema_errors))
    print('NON-PRICE CONTENT:', 'PASS' if content_ok else 'FAIL')
    print('MEDIA METADATA:', 'PASS' if media_meta_ok else 'FAIL')
    print('COMMERCE SAFETY:', 'PASS' if safety_ok else 'FAIL')
    print('PREPRICE CARDS:', f"{summary.get('cards_preprice_ready')}/{summary.get('cards_total')}")
    print('PREPRICE SKU:', f"{summary.get('skus_preprice_ready')}/{summary.get('skus_total')}")
    print('PREPRICE COMPLETE:', 'PASS' if summary.get('complete') else 'PENDING')
    if alt_missing:
        for x in alt_missing[:20]:
            print('  ALT:', x)
    if invalid_media:
        for x in invalid_media[:20]:
            print('  MEDIA:', x)
    if schema_errors:
        for x in schema_errors[:20]:
            print('  SCHEMA:', x)
    print('RESULT:', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
