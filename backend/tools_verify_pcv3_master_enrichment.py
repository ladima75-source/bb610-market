from __future__ import annotations

import json
from pathlib import Path

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import content_from_master, find_master_for_card, source_metadata
from backend.services.product_cards_v3_quality import quality_report

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / 'var' / 'reports'


def _latest_report() -> dict | None:
    paths = sorted(REPORT_DIR.glob('pcv3-master-enrich-*.json'))
    if not paths:
        return None
    try:
        return json.loads(paths[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def main() -> None:
    total = 0
    schema_errors: list[str] = []
    matched = 0
    verified = 0
    content_mismatches: list[str] = []

    for row in cards.list_cards():
        product_id = str(row.get('product_id') or '')
        card = cards.get(product_id)
        if not isinstance(card, dict):
            schema_errors.append(f'{product_id}: missing card')
            continue
        total += 1
        try:
            cards.validate(card)
        except Exception as exc:
            schema_errors.append(f'{product_id}: {exc}')
            continue

        master = find_master_for_card(card)
        source = source_metadata(master)
        if not master:
            continue
        matched += 1
        if not source.get('verified'):
            continue
        verified += 1
        expected = content_from_master(master, card.get('content') or {})
        # Rebuilding from the current card is idempotent after enrichment.
        if expected != (card.get('content') or {}):
            content_mismatches.append(product_id)

    qa = quality_report()
    summary = qa.get('summary') or {}
    latest = _latest_report()
    report_ok = True
    report_note = 'NO_REPORT'
    if latest:
        report_ok = bool(latest.get('commerce_unchanged'))
        report_note = latest.get('mode') or 'UNKNOWN'
        for item in latest.get('items') or []:
            before = item.get('protected_sha')
            after = item.get('protected_sha_after')
            if item.get('applied') and before and after and before != after:
                report_ok = False
                break

    ok = not schema_errors and not content_mismatches and report_ok
    print('BB610 PCV3 MASTER ENRICHMENT VERIFY')
    print('V3 TOTAL:', total)
    print('MASTER MATCHED:', matched)
    print('MASTER SOURCE VERIFIED:', verified)
    print('QA SOURCE VERIFIED:', summary.get('source_verified', 0))
    print('SCHEMA ERRORS:', len(schema_errors))
    print('CONTENT MISMATCHES:', len(content_mismatches))
    print('LATEST ENRICH REPORT:', report_note)
    print('PROTECTED/COMMERCE SAFETY:', 'PASS' if report_ok else 'FAIL')
    if schema_errors:
        for item in schema_errors[:20]:
            print('  SCHEMA:', item)
    if content_mismatches:
        for item in content_mismatches[:20]:
            print('  CONTENT:', item)
    print('RESULT:', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
