from __future__ import annotations

from backend.services.product_cards_v3_preprice import preprice_report


def main() -> None:
    report = preprice_report()
    s = report['summary']
    print('BB610 PCV3 PRE-PRICE COMPLETENESS')
    print('PRICE GATE:', report['price_gate'])
    print('CARDS READY:', f"{s['cards_preprice_ready']}/{s['cards_total']}")
    print('SKU READY:', f"{s['skus_preprice_ready']}/{s['skus_total']}")
    print('GAPS:', s['gaps_total'])
    print('ISSUES:', s['issue_counts'])
    print('RESULT:', 'PASS' if s['complete'] else 'INCOMPLETE')
    if not s['complete']:
        for gap in report['gaps'][:100]:
            suffix = f" / {gap['package']}" if gap.get('package') else ''
            print(f"  {gap.get('title')}{suffix}: {','.join(gap.get('issues') or [])}")
    raise SystemExit(0 if s['complete'] else 2)


if __name__ == '__main__':
    main()
