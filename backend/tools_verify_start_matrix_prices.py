from __future__ import annotations

import json
from pathlib import Path

from backend.tools_import_start_matrix_prices import REPORT_ROOT, _load_source, build_plan, audit


def _latest_report() -> dict | None:
    paths = sorted(REPORT_ROOT.glob('start-matrix-prices-*.json'))
    if not paths:
        return None
    try:
        return json.loads(paths[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def main() -> None:
    source = _load_source()
    plan = build_plan()
    state = audit(plan)
    report = _latest_report()

    evidence_ok = bool(
        report and
        report.get('mode') == 'APPLY_SAFE' and
        isinstance(report.get('apply'), dict) and
        report['apply'].get('nonprice_unchanged') is True and
        (report.get('safety') or {}).get('stock_written') is False and
        (report.get('safety') or {}).get('availability_written') is False and
        (report.get('safety') or {}).get('enabled_written') is False and
        (report.get('safety') or {}).get('publication_written') is False and
        (report.get('safety') or {}).get('positive_existing_price_overwritten') is False
    )
    source_ok = len(source.get('items') or []) == 40 and state['rows'] == 40
    priced_ok = state['priced'] == state['rows'] and not state['missing']
    priority_ok = (
        state['priority']['A']['rows'] == 29 and
        state['priority']['B']['rows'] == 11 and
        state['priority']['A']['priced'] == 29 and
        state['priority']['B']['priced'] == 11
    )
    ok = source_ok and priced_ok and priority_ok and evidence_ok

    print('BB610 START MATRIX PRICE VERIFY')
    print('SOURCE ROWS:', state['rows'])
    print('PRICED:', f"{state['priced']}/{state['rows']}")
    print('SOURCE-EQUAL:', f"{state['source_equal']}/{state['rows']}")
    print('EXISTING PRICE CONFLICTS (PRESERVED):', len(state['conflicts']))
    print('MISSING PRICE:', len(state['missing']))
    print('PRIORITY A:', f"{state['priority']['A']['priced']}/{state['priority']['A']['rows']}")
    print('PRIORITY B:', f"{state['priority']['B']['priced']}/{state['priority']['B']['rows']}")
    print('SAFE APPLY EVIDENCE:', 'PASS' if evidence_ok else 'FAIL')
    print('NO STOCK/AVAILABILITY/ENABLE/PUBLISH WRITES:', 'PASS' if evidence_ok else 'FAIL')
    if state['conflicts']:
        print('PRESERVED PRICE CONFLICTS:')
        for row in state['conflicts'][:20]:
            print(f"  {row['title']} / {row['package']} | live={row.get('live_price')} | source RRP={row.get('rrp')}")
    print('RESULT:', 'PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
