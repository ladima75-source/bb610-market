from __future__ import annotations

import argparse
import json

from backend.db import connect
from backend import tools_apply_pcv3_prices_20260916 as base


def _skip_manual_source(row: dict) -> bool:
    name = str(row.get('source_name') or '')
    n = base.norm(name)
    f = base.formula(name)
    return 'osmocote' in n and f in {('12','8','19'), ('16','9','12')}


def _is_manual_osmocote(target: dict) -> bool:
    title = str(target.get('title') or '')
    n = base.norm(title)
    f = base.formula(title)
    return (
        ('osmocote' in n and 'potassium' in n and f == ('12','8','19'))
        or ('osmocote' in n and 'landscape' in n and f == ('16','9','12'))
    )


def _is_pot(target: dict) -> bool:
    n = base.norm(' '.join(str(target.get(k) or '') for k in ('title','brand','category','package')))
    return any(k in n for k in ('plantlogic','container','pot','gorsh','konteiner'))


def _is_megafol_no_source(target: dict) -> bool:
    n = base.norm(str(target.get('title') or ''))
    return n == 'megafol' and base.pack_key(target.get('package')) in {'20ml','1000ml'}


def build_plan() -> dict:
    doc = base._load_json(base.PRICE_MANIFEST, {})
    source_rows = doc.get('rows') if isinstance(doc, dict) else None
    if not isinstance(source_rows, list) or len(source_rows) != 195:
        raise RuntimeError(f'price manifest must contain 195 rows; got {len(source_rows or [])}')

    skipped_source = []
    import_rows = []
    for row_no, row in enumerate(source_rows, start=2):
        if _skip_manual_source(row):
            skipped_source.append({'source_row': row_no, **row})
        else:
            import_rows.append((row_no, row))
    if len(skipped_source) != 4 or len(import_rows) != 191:
        raise RuntimeError(f'expected 4 manual rows + 191 import rows; got {len(skipped_source)} + {len(import_rows)}')

    targets = base.load_targets()
    if len(targets) != 197:
        raise RuntimeError(f'expected 197 active v3 SKU; got {len(targets)}')

    by_pack = {}
    for target in targets:
        by_pack.setdefault(target['pack_key'], []).append(target)

    plan = []
    problems = []
    for row_no, row in import_rows:
        src_name = str(row.get('source_name') or '').strip()
        package = str(row.get('package') or '').strip()
        price = row.get('price')
        if not isinstance(price, (int, float)) or price < 0:
            problems.append(f'row {row_no}: invalid price {price!r}')
            continue
        candidates = [(base.pair_score(src_name, t['aliases']), t) for t in by_pack.get(base.pack_key(package), [])]
        candidates.sort(key=lambda x: (x[0], x[1]['title']), reverse=True)
        if not candidates:
            problems.append(f'row {row_no}: no SKU with package {package} for {src_name}')
            continue
        top_score, top = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else -1
        if top_score < 430:
            problems.append(f'row {row_no}: weak match {top_score:.1f}: {src_name} / {package} -> {top["title"]}')
            continue
        if second_score >= top_score - 2.0 and candidates[1][1]['product_id'] != top['product_id']:
            problems.append(f'row {row_no}: ambiguous {src_name} / {package}: {top["title"]}={top_score:.1f}; {candidates[1][1]["title"]}={second_score:.1f}')
            continue
        if not top['commerce_key']:
            problems.append(f'row {row_no}: matched SKU has no commerce binding: {top["title"]} / {top["package"]}')
            continue
        plan.append({
            'source_row': row_no,
            'source_name': src_name,
            'source_package': package,
            'price': float(price),
            **{k: top[k] for k in ('product_id','title','brand','category','sku_id','sku_code','package','commerce_key')},
            'score': round(top_score, 2),
        })

    counts = {}
    for row in plan:
        counts[row['commerce_key']] = counts.get(row['commerce_key'], 0) + 1
    duplicates = [k for k,v in counts.items() if v != 1]
    if duplicates:
        problems.append('duplicate target commerce keys: ' + ', '.join(duplicates[:20]))
    if len(plan) != 191:
        problems.append(f'matched rows {len(plan)}/191')

    unmatched = [t for t in targets if t['commerce_key'] not in counts]
    manual = [t for t in unmatched if _is_manual_osmocote(t)]
    pots = [t for t in unmatched if _is_pot(t)]
    megafol = [t for t in unmatched if _is_megafol_no_source(t)]
    covered = {t['commerce_key'] for t in manual + pots + megafol}
    unexpected = [t for t in unmatched if t['commerce_key'] not in covered]

    if len(unmatched) != 8:
        problems.append(f'expected 8 unmatched v3 SKU (4 manual Osmocote + 2 pots + 2 Megafol without source price); got {len(unmatched)}')
    if len(manual) != 4:
        problems.append(f'expected 4 manual Osmocote SKU; got {len(manual)}')
    if len(pots) != 2:
        problems.append(f'expected 2 Plantlogic pot SKU; got {len(pots)}')
    if len(megafol) != 2:
        problems.append(f'expected 2 Megafol SKU absent from price source; got {len(megafol)}')
    for t in unexpected:
        problems.append(f'unexpected unmatched SKU: {t["title"]} / {t["package"]} / {t["commerce_key"]}')
    if problems:
        raise RuntimeError('PRICE PREFLIGHT FAILED:\n' + '\n'.join(problems[:100]))

    with connect() as con:
        existing = {str(r[0]) for r in con.execute('SELECT sku FROM sku_commerce').fetchall()}
    missing = [r['commerce_key'] for r in plan if r['commerce_key'] not in existing]
    if missing:
        raise RuntimeError('missing commerce rows: ' + ', '.join(missing[:30]))

    return {
        'source_file': doc.get('source_file'),
        'source_date': doc.get('source_date'),
        'currency': doc.get('currency','UAH'),
        'rows': plan,
        'manual_source_rows': skipped_source,
        'manual_v3_skus': manual,
        'unmatched_pot_skus': pots,
        'megafol_without_source_price': megafol,
        'zero_price_rows': [r for r in plan if r['price'] == 0],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description='Apply 191 unambiguous prices; leave 4 Osmocote manual, 2 pots, and 2 Megafol SKU without source price untouched.')
    ap.add_argument('--apply-safe', action='store_true')
    args = ap.parse_args()
    plan = build_plan()

    base.REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = base.REPORT_ROOT / f'pcv3-prices-r5-{base.stamp()}.json'
    report = {'mode': 'APPLY_SAFE' if args.apply_safe else 'DRY_RUN', **plan}

    print('BB610 PCV3 PRICE IMPORT R5')
    print('MATCHED PRICE ROWS:', len(plan['rows']), '/ 191')
    print('MANUAL OSMOCOTE SKU:', len(plan['manual_v3_skus']))
    print('MEGAFOL WITHOUT SOURCE PRICE:', len(plan['megafol_without_source_price']))
    for row in plan['megafol_without_source_price']:
        print('  NO SOURCE PRICE:', row['title'], '|', row['package'], '|', row['commerce_key'])
    print('UNMATCHED POT SKU:', len(plan['unmatched_pot_skus']))
    print('AVAILABILITY POLICY: IN_STOCK')
    print('STOCK QTY POLICY: NULL')

    if args.apply_safe:
        result = base.apply_plan(plan)
        report['apply'] = result
        print('UPDATED:', result['updated'])
        print('AVAILABILITY IN_STOCK:', result['availability_in_stock'])
        print('STOCK QTY NULL:', result['stock_qty_null'])
        print('BACKUP:', result['backup_dir'])
        print('RESULT: PASS')
    else:
        print('RESULT: PASS (DRY-RUN)')

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('REPORT:', report_path)


if __name__ == '__main__':
    main()
