from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db import DB_PATH, connect
from backend.services import product_cards_v3 as cards
from backend.tools_complete_pcv3_media_readiness import _pack_key
from backend.tools_import_organic_planet_full_price_v3 import _full_cards as _organic_full_cards, _match_product as _organic_match_product, _source as _organic_source

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'catalog_sources' / 'organic_planet_start_matrix_v1.json'
REPORT_ROOT = ROOT / 'var' / 'reports'
BACKUP_ROOT = ROOT / 'var' / 'release-backups'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _load_source() -> dict:
    obj = json.loads(SOURCE.read_text(encoding='utf-8'))
    rows = obj.get('items') or []
    if len(rows) != int(obj.get('expected_rows') or -1):
        raise RuntimeError('start matrix row count mismatch')
    counts = {'A': 0, 'B': 0}
    for row in rows:
        p = str(row.get('priority') or '')
        if p in counts:
            counts[p] += 1
        if not str(row.get('slug') or '').strip():
            raise RuntimeError('source row without slug')
        if not str(row.get('package') or '').strip():
            raise RuntimeError(f"{row.get('slug')}: source row without package")
        if not isinstance(row.get('rrp'), (int, float)) or float(row['rrp']) <= 0:
            raise RuntimeError(f"{row.get('slug')}/{row.get('package')}: invalid RRP")
    expected_counts = obj.get('priority_counts') or {}
    for key, value in counts.items():
        if int(expected_counts.get(key) or -1) != value:
            raise RuntimeError(f'priority {key} count mismatch: {value}')
    return obj


def _backup_db(stamp: str) -> Path:
    dest = BACKUP_ROOT / f'start-matrix-price-import-{stamp}'
    dest.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(DB_PATH))
    try:
        dst = sqlite3.connect(str(dest / DB_PATH.name))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def _cards_by_slug() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for summary in cards.list_cards():
        pid = str(summary.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            continue
        slug = str(card.get('slug') or '').strip().lower()
        if not slug:
            continue
        if slug in out:
            raise RuntimeError(f'duplicate PCV3 slug: {slug}')
        out[slug] = card
    return out


def _organic_by_slug() -> dict[str, dict]:
    return {
        str(row.get('slug') or '').strip().lower(): row
        for row in (_organic_source().get('products') or [])
        if isinstance(row, dict) and str(row.get('slug') or '').strip()
    }


def _resolve_card(src: dict, by_slug: dict[str, dict], organic_rows: dict[str, dict], all_cards: list[dict]) -> tuple[dict | None, str]:
    slug = str(src.get('slug') or '').strip().lower()
    direct = by_slug.get(slug)
    if direct:
        return direct, 'exact-v3-slug'
    organic = organic_rows.get(slug)
    if organic:
        matched = _organic_match_product(organic, all_cards)
        if matched:
            full = cards.get(str(matched.get('product_id') or ''))
            if isinstance(full, dict):
                return full, 'organic-source-match'
    return None, 'none'


def _mapping_by_pid() -> dict[str, dict]:
    cmap = cards.commerce_map()
    return {
        str(row.get('product_id') or ''): row
        for row in cmap.get('products', [])
        if isinstance(row, dict) and row.get('product_id')
    }


def _commerce_rows() -> dict[str, dict]:
    with connect() as con:
        return {
            str(row['sku']): dict(row)
            for row in con.execute('SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce').fetchall()
        }


def _find_v3_sku(card: dict, package: str) -> dict:
    key = _pack_key(package)
    hits = []
    for sku in (card.get('sku_media') or {}).get('skus') or []:
        if sku.get('enabled') is False:
            continue
        sku_key = _pack_key(sku.get('package') or sku.get('label') or '')
        if sku_key and sku_key == key:
            hits.append(sku)
    if len(hits) != 1:
        raise RuntimeError(f"{card.get('slug')}/{package}: expected 1 v3 SKU, found {len(hits)}")
    return hits[0]


def build_plan() -> dict:
    source = _load_source()
    by_slug = _cards_by_slug()
    organic_rows = _organic_by_slug()
    all_cards = _organic_full_cards()
    mappings = _mapping_by_pid()
    commerce = _commerce_rows()
    actions = []
    failures = []

    for src in source['items']:
        slug = str(src['slug']).strip().lower()
        card, match_method = _resolve_card(src, by_slug, organic_rows, all_cards)
        if not card:
            failures.append(f'{slug}/{src["package"]}: PCV3 card not found')
            continue
        pid = str(card.get('product_id') or '')
        mapping = mappings.get(pid)
        if not mapping:
            failures.append(f'{slug}/{src["package"]}: commerce product mapping missing')
            continue
        try:
            v3sku = _find_v3_sku(card, str(src['package']))
        except Exception as exc:
            failures.append(str(exc))
            continue
        links = {
            str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
            for x in mapping.get('skus') or [] if isinstance(x, dict)
        }
        sku_id = str(v3sku.get('sku_id') or '')
        commerce_key = links.get(sku_id, '')
        if not commerce_key:
            failures.append(f'{slug}/{src["package"]}: commerce SKU binding missing')
            continue
        current = commerce.get(commerce_key)
        if not current:
            failures.append(f'{slug}/{src["package"]}: commerce row missing {commerce_key}')
            continue
        current_price = current.get('sale_price') if current.get('sale_price') is not None else current.get('price')
        rrp = round(float(src['rrp']), 2)
        if isinstance(current_price, (int, float)) and float(current_price) > 0:
            if math.isclose(float(current_price), rrp, abs_tol=0.01):
                action = 'keep-equal-price'
            else:
                action = 'keep-existing-conflict'
        else:
            action = 'set-missing-price'
        actions.append({
            'priority': src['priority'],
            'slug': slug,
            'title': src['title'],
            'package': src['package'],
            'wholesale': float(src['wholesale']),
            'rrp': rrp,
            'start_qty': int(src['start_qty']),
            'decision': src['decision'],
            'product_id': pid,
            'resolved_v3_slug': str(card.get('slug') or ''),
            'match_method': match_method,
            'commerce_product': str(mapping.get('existing_product_key') or ''),
            'sku_id': sku_id,
            'commerce_sku': commerce_key,
            'current_price': current_price,
            'current_enabled': bool(current.get('enabled')),
            'current_availability': str(current.get('availability') or 'unknown'),
            'current_stock_qty': current.get('stock_qty'),
            'action': action,
        })

    if failures:
        raise RuntimeError('start matrix price plan failed:\n' + '\n'.join(failures[:100]))
    return {'source': source, 'actions': actions}


def _snapshot_nonprice() -> dict[str, tuple[Any, ...]]:
    with connect() as con:
        return {
            str(r['sku']): (r['sale_price'], r['availability'], r['stock_qty'], r['enabled'])
            for r in con.execute('SELECT sku,sale_price,availability,stock_qty,enabled FROM sku_commerce').fetchall()
        }


def apply_plan(plan: dict) -> dict:
    stamp = _stamp()
    backup = _backup_db(stamp)
    before_nonprice = _snapshot_nonprice()
    set_count = 0
    conflicts = 0
    with connect() as con:
        for row in plan['actions']:
            if row['action'] == 'set-missing-price':
                con.execute('UPDATE sku_commerce SET price=?, updated_at=? WHERE sku=?', (row['rrp'], datetime.now(timezone.utc).isoformat(), row['commerce_sku']))
                set_count += 1
            elif row['action'] == 'keep-existing-conflict':
                conflicts += 1
        con.commit()

    after_nonprice = _snapshot_nonprice()
    for sku, state in before_nonprice.items():
        if after_nonprice.get(sku) != state:
            raise RuntimeError(f'non-price commerce state changed for {sku}')

    return {'backup_dir': str(backup), 'prices_set': set_count, 'existing_price_conflicts': conflicts, 'nonprice_unchanged': True}


def audit(plan: dict) -> dict:
    commerce = _commerce_rows()
    covered = 0
    equal_source = 0
    conflicts = []
    missing = []
    priority = {'A': {'rows': 0, 'priced': 0}, 'B': {'rows': 0, 'priced': 0}}
    for row in plan['actions']:
        state = commerce.get(row['commerce_sku']) or {}
        value = state.get('sale_price') if state.get('sale_price') is not None else state.get('price')
        ok = isinstance(value, (int, float)) and float(value) > 0
        p = str(row['priority'])
        priority[p]['rows'] += 1
        priority[p]['priced'] += int(ok)
        if ok:
            covered += 1
            if math.isclose(float(value), float(row['rrp']), abs_tol=0.01):
                equal_source += 1
            else:
                conflicts.append({**row, 'live_price': value})
        else:
            missing.append(row)
    return {
        'rows': len(plan['actions']),
        'priced': covered,
        'source_equal': equal_source,
        'conflicts': conflicts,
        'missing': missing,
        'priority': priority,
    }


def write_reports(plan: dict, audit_result: dict, apply_result: dict | None, mode: str) -> tuple[Path, Path]:
    stamp = _stamp()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        'schema_version': '1.0',
        'mode': mode,
        'source': str(SOURCE.relative_to(ROOT)),
        'source_rows': len(plan['actions']),
        'audit': audit_result,
        'apply': apply_result,
        'safety': {
            'stock_written': False,
            'availability_written': False,
            'enabled_written': False,
            'publication_written': False,
            'positive_existing_price_overwritten': False,
        },
    }
    json_path = REPORT_ROOT / f'start-matrix-prices-{stamp}.json'
    csv_path = REPORT_ROOT / f'start-matrix-prices-{stamp}.csv'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with csv_path.open('w', newline='', encoding='utf-8-sig') as fh:
        fields = ['priority','title','slug','resolved_v3_slug','match_method','package','commerce_sku','wholesale','rrp','start_qty','decision','current_price','action']
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        for row in plan['actions']:
            wr.writerow({k: row.get(k) for k in fields})
    return json_path, csv_path


def main() -> None:
    ap = argparse.ArgumentParser(description='Import approved Organic Planet start-matrix RRP into missing commerce prices only.')
    ap.add_argument('--apply-safe', action='store_true', help='Set only missing positive prices. Never overwrite positive prices or touch stock/availability/enabled/publication.')
    args = ap.parse_args()
    plan = build_plan()
    before = audit(plan)
    result = apply_plan(plan) if args.apply_safe else None
    after = audit(plan)
    json_path, csv_path = write_reports(plan, after, result, 'APPLY_SAFE' if args.apply_safe else 'DRY_RUN')

    print('BB610 START MATRIX PRICE IMPORT')
    print('MODE:', 'APPLY_SAFE' if args.apply_safe else 'DRY_RUN')
    print('SOURCE ROWS:', len(plan['actions']))
    print('PRICED BEFORE:', f"{before['priced']}/{before['rows']}")
    if result:
        print('PRICES SET:', result['prices_set'])
        print('NON-PRICE COMMERCE UNCHANGED:', 'PASS' if result['nonprice_unchanged'] else 'FAIL')
        print('BACKUP:', result['backup_dir'])
    print('PRICED AFTER:', f"{after['priced']}/{after['rows']}")
    print('SOURCE-EQUAL PRICE:', f"{after['source_equal']}/{after['rows']}")
    print('EXISTING PRICE CONFLICTS:', len(after['conflicts']))
    print('MISSING PRICE:', len(after['missing']))
    print('PRIORITY A PRICED:', f"{after['priority']['A']['priced']}/{after['priority']['A']['rows']}")
    print('PRIORITY B PRICED:', f"{after['priority']['B']['priced']}/{after['priority']['B']['rows']}")
    print('STOCK WRITES: 0')
    print('AVAILABILITY WRITES: 0')
    print('ENABLED WRITES: 0')
    print('PUBLICATION WRITES: 0')
    print('JSON REPORT:', json_path)
    print('CSV REPORT:', csv_path)


if __name__ == '__main__':
    main()
