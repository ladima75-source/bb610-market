from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.services.product_cards_v3_master import (
    find_master_for_card,
    master_source_row_index,
    normalize_name,
    organic_products,
    source_metadata,
)
from backend.tools_canonicalize_pcv3_duplicate_identity import _groups, _load_cards, _sku_by_pack

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'var' / 'reports'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _identity_values(row: dict) -> set[str]:
    values = [row.get('title'), row.get('slug')]
    aliases = row.get('aliases')
    if isinstance(aliases, list):
        values.extend(aliases)
    return {normalize_name(x) for x in values if normalize_name(x)}


def main() -> None:
    full = _load_cards()
    groups = _groups(full)
    masters = master_source_row_index()
    organic = {int(x.get('_source_row')): x for x in organic_products() if x.get('_source_row') is not None}
    report_groups = []

    print('BB610 PCV3 IDENTITY COLLISION DIAGNOSTIC')
    print('CARDS:', len(full), '| COLLISION GROUPS:', len(groups))

    for source_row, members in sorted(groups.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 10**9):
        try:
            row_no = int(source_row)
        except Exception:
            row_no = -1
        master = masters.get(row_no) or {}
        org = organic.get(row_no) or {}
        master_name = str(master.get('name') or '')
        organic_title = str(org.get('title') or '')
        bridge_ok = bool(master_name and normalize_name(master_name) in _identity_values(org))

        item = {
            'source_row': row_no,
            'master_name': master_name,
            'organic_title': organic_title,
            'row_bridge_identity_ok': bridge_ok,
            'members': [],
        }
        print(f'ROW {row_no} | BRIDGE={"PASS" if bridge_ok else "FAIL"} | MASTER={master_name} | ORGANIC={organic_title}')

        for member in members:
            card = member['card']
            meta = source_metadata(find_master_for_card(card))
            try:
                packs = sorted(_sku_by_pack(card))
            except Exception as exc:
                packs = [f'ERROR:{exc}']
            row = {
                'product_id': str(card.get('product_id') or ''),
                'title': str((card.get('content') or {}).get('title') or ''),
                'slug': str(card.get('slug') or ''),
                'match_method': str(meta.get('match_method') or ''),
                'organic_title': str(meta.get('organic_title') or ''),
                'packages': packs,
            }
            item['members'].append(row)
            print(f"  {row['match_method']} | {row['title']} | {row['slug']} | packs={','.join(packs)}")
        report_groups.append(item)

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f'pcv3-identity-collisions-{_stamp()}.json'
    payload = {
        'schema_version': '1.0',
        'cards_total': len(full),
        'collision_groups': len(groups),
        'groups': report_groups,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('REPORT:', path)
    print('RESULT: PASS (READ-ONLY)')


if __name__ == '__main__':
    main()
