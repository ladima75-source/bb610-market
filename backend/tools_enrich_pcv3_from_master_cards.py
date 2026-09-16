from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import content_from_master, find_master_for_card, source_metadata

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / 'var' / 'reports'
BACKUP_ROOT = ROOT / 'var' / 'pcv3-backups'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _json_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _file_sha(path: Path) -> str:
    if not path.exists():
        return ''
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protected(card: dict) -> dict:
    return {
        'schema_version': card.get('schema_version'),
        'product_id': card.get('product_id'),
        'slug': card.get('slug'),
        'enabled': card.get('enabled'),
        'sku_media': deepcopy(card.get('sku_media')),
    }


def _backup(backup_dir: Path, product_ids: list[str]) -> None:
    products_dir = backup_dir / 'products'
    products_dir.mkdir(parents=True, exist_ok=True)
    for product_id in product_ids:
        src = cards.PRODUCTS / f'{product_id}.json'
        if src.exists():
            shutil.copy2(src, products_dir / src.name)
    for src in (cards.INDEX, cards.COMMERCE_MAP, cards.MIGRATION_MANIFEST):
        if src.exists():
            shutil.copy2(src, backup_dir / src.name)


def build_plan() -> list[dict]:
    plan: list[dict] = []
    for summary in cards.list_cards():
        product_id = str(summary.get('product_id') or '')
        card = cards.get(product_id)
        if not isinstance(card, dict):
            continue
        master = find_master_for_card(card)
        source = source_metadata(master)
        if not master or not source.get('verified'):
            continue

        new_card = deepcopy(card)
        new_card['content'] = content_from_master(master, card.get('content') or {})
        cards.validate(new_card)
        protected_before = _json_sha(_protected(card))
        protected_after = _json_sha(_protected(new_card))
        if protected_before != protected_after:
            raise RuntimeError(f'{product_id}: protected Product Card v3 fields changed during plan build')
        plan.append({
            'product_id': product_id,
            'title': (card.get('content') or {}).get('title') or '',
            'master_title': master.get('name') or '',
            'master_file': source.get('master_file'),
            'source_row': source.get('source_row'),
            'verified_date': source.get('verified_date'),
            'source_count': source.get('source_count'),
            'match_method': source.get('match_method') or '',
            'organic_title': source.get('organic_title') or '',
            'before_content_sha': _json_sha(card.get('content') or {}),
            'after_content_sha': _json_sha(new_card.get('content') or {}),
            'protected_sha': protected_before,
            'changed': _json_sha(card.get('content') or {}) != _json_sha(new_card.get('content') or {}),
            '_new_card': new_card,
        })
    return plan


def main() -> None:
    ap = argparse.ArgumentParser(description='Safely enrich Product Card v3 content from approved stage22c MASTER cards.')
    ap.add_argument('--apply', action='store_true', help='Write content changes after full preflight. Default is dry-run.')
    args = ap.parse_args()

    stamp = _stamp()
    summaries = cards.list_cards()
    plan = build_plan()
    commerce_before = _file_sha(cards.COMMERCE_MAP)
    matched_ids = {x['product_id'] for x in plan}
    unmatched = [
        {
            'product_id': str(row.get('product_id') or ''),
            'title': str(row.get('title') or ''),
            'slug': str(row.get('slug') or ''),
        }
        for row in summaries
        if str(row.get('product_id') or '') not in matched_ids
    ]
    changed_ids = [x['product_id'] for x in plan if x['changed']]
    backup_dir = BACKUP_ROOT / f'master-enrich-{stamp}'

    if args.apply and changed_ids:
        _backup(backup_dir, changed_ids)
        for item in plan:
            if not item['changed']:
                continue
            product_id = item['product_id']
            before = cards.get(product_id)
            if not isinstance(before, dict):
                raise RuntimeError(f'{product_id}: disappeared before write')
            cards.put(product_id, item['_new_card'])
            after = cards.get(product_id)
            if not isinstance(after, dict):
                raise RuntimeError(f'{product_id}: missing after write')
            cards.validate(after)
            if _json_sha(_protected(before)) != _json_sha(_protected(after)):
                raise RuntimeError(f'{product_id}: protected fields changed after write')

    commerce_after = _file_sha(cards.COMMERCE_MAP)
    if commerce_before != commerce_after:
        raise RuntimeError('commerce_map.json changed; enrichment aborted as unsafe')

    report_items = []
    for item in plan:
        clean = {k: v for k, v in item.items() if k != '_new_card'}
        if args.apply:
            current = cards.get(item['product_id']) or {}
            clean['current_content_sha'] = _json_sha(current.get('content') or {})
            clean['protected_sha_after'] = _json_sha(_protected(current)) if current else ''
            clean['applied'] = bool(item['changed'])
        else:
            clean['applied'] = False
        report_items.append(clean)

    match_methods = Counter(str(x.get('match_method') or 'unknown') for x in plan)
    report = {
        'schema_version': '1.1',
        'tool': 'tools_enrich_pcv3_from_master_cards',
        'timestamp_utc': stamp,
        'mode': 'APPLY' if args.apply else 'DRY_RUN',
        'master_source': 'data/content_batches/stage22c_batch*.json',
        'identity_bridge_source': 'data/catalog_sources/organic_planet_full_price_v1.json',
        'matched_verified_cards': len(plan),
        'match_methods': dict(match_methods),
        'unmatched_cards': unmatched,
        'changed_cards': len(changed_ids),
        'unchanged_cards': len(plan) - len(changed_ids),
        'total_v3_cards': len(summaries),
        'commerce_map_sha_before': commerce_before,
        'commerce_map_sha_after': commerce_after,
        'commerce_unchanged': commerce_before == commerce_after,
        'backup_dir': str(backup_dir) if args.apply and changed_ids else '',
        'items': report_items,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f'pcv3-master-enrich-{stamp}.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('BB610 PCV3 MASTER ENRICHMENT')
    print('MODE:', report['mode'])
    print('V3 TOTAL:', report['total_v3_cards'])
    print('MASTER VERIFIED MATCHES:', report['matched_verified_cards'])
    print('MATCH DIRECT:', match_methods.get('direct_master_identity', 0))
    print('MATCH ORGANIC SOURCE ROW:', match_methods.get('organic_source_row', 0))
    print('UNMATCHED MASTER:', len(unmatched))
    for item in unmatched:
        print('  UNMATCHED:', item['title'], '|', item['slug'])
    print('CONTENT CHANGES:', report['changed_cards'])
    print('COMMERCE WRITES: 0')
    print('COMMERCE UNCHANGED:', 'PASS' if report['commerce_unchanged'] else 'FAIL')
    print('REPORT:', report_path)
    if report['backup_dir']:
        print('BACKUP:', report['backup_dir'])


if __name__ == '__main__':
    main()
