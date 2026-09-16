from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import find_master_for_card, source_metadata
from backend.services.product_cards_v3_media import _is_resolvable
from backend.tools_complete_pcv3_media_readiness import _pack_key
from backend.tools_prepare_pcv3_release import _snapshot_tables

ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = ROOT / 'var' / 'release-backups'
REPORT_ROOT = ROOT / 'var' / 'reports'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _load_cards() -> list[dict]:
    out: list[dict] = []
    for row in cards.list_cards():
        card = cards.get(str(row.get('product_id') or ''))
        if isinstance(card, dict):
            out.append(card)
    return out


def _groups(full_cards: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for card in full_cards:
        meta = source_metadata(find_master_for_card(card))
        source_row = meta.get('source_row')
        if source_row is None:
            continue
        grouped.setdefault(str(source_row), []).append({'card': card, 'meta': meta})
    return {k: v for k, v in grouped.items() if len(v) > 1}


def _sku_by_pack(card: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sku in (card.get('sku_media') or {}).get('skus') or []:
        if not isinstance(sku, dict) or sku.get('enabled') is False:
            continue
        key = _pack_key(sku.get('package') or sku.get('label') or '')
        if not key:
            raise RuntimeError(f"{card.get('product_id')}: SKU without normalized package")
        if key in out:
            raise RuntimeError(f"{card.get('product_id')}: duplicate package {key}")
        out[key] = sku
    return out


def _media_by_id(card: dict) -> dict[str, dict]:
    return {
        str(row.get('media_id') or ''): row
        for row in (card.get('sku_media') or {}).get('media') or []
        if isinstance(row, dict) and row.get('media_id')
    }


def _valid_primary(card: dict, sku: dict) -> dict | None:
    mid = str(sku.get('primary_media_id') or '')
    media = _media_by_id(card).get(mid)
    if not media:
        return None
    path = str(media.get('path') or '').strip()
    if not path or not _is_resolvable(path):
        return None
    return media


def _new_media_id(path: str, used: set[str]) -> str:
    base = 'med_dedupe_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:18]
    value = base
    n = 2
    while value in used:
        value = f'{base}_{n}'
        n += 1
    return value


def build_plan() -> dict:
    full = _load_cards()
    groups = _groups(full)
    safe: list[dict] = []
    blocked: list[dict] = []

    for source_row, members in sorted(groups.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 10**9):
        direct = [x for x in members if x['meta'].get('match_method') == 'direct_master_identity']
        bridged = [x for x in members if x['meta'].get('match_method') == 'organic_source_row']
        reason = ''
        if len(direct) != 1:
            reason = f'expected one direct MASTER canonical, found {len(direct)}'
        elif len(bridged) != len(members) - 1:
            reason = 'non-canonical members are not all Organic source-row bridges'

        canonical = direct[0] if len(direct) == 1 else None
        canonical_packs: dict[str, dict] = {}
        if not reason and canonical:
            try:
                canonical_packs = _sku_by_pack(canonical['card'])
            except Exception as exc:
                reason = str(exc)

        duplicate_rows = []
        if not reason and canonical:
            for member in bridged:
                try:
                    packs = _sku_by_pack(member['card'])
                except Exception as exc:
                    reason = str(exc)
                    break
                if set(packs) != set(canonical_packs):
                    reason = (
                        f"package mismatch canonical={sorted(canonical_packs)} "
                        f"duplicate={sorted(packs)}"
                    )
                    break
                recoverable = []
                for pack, csku in canonical_packs.items():
                    if _valid_primary(canonical['card'], csku):
                        continue
                    dmedia = _valid_primary(member['card'], packs[pack])
                    if dmedia:
                        recoverable.append({'package_key': pack, 'path': str(dmedia.get('path') or '')})
                duplicate_rows.append({
                    'product_id': str(member['card'].get('product_id') or ''),
                    'slug': str(member['card'].get('slug') or ''),
                    'match_method': member['meta'].get('match_method'),
                    'packages': sorted(packs),
                    'recoverable_primary_media': recoverable,
                })

        item = {
            'source_row': int(source_row) if source_row.isdigit() else source_row,
            'canonical_product_id': str((canonical or {}).get('card', {}).get('product_id') or ''),
            'canonical_slug': str((canonical or {}).get('card', {}).get('slug') or ''),
            'canonical_title': str(((canonical or {}).get('card', {}).get('content') or {}).get('title') or ''),
            'canonical_packages': sorted(canonical_packs),
            'duplicates': duplicate_rows,
        }
        if reason:
            item['reason'] = reason
            item['members'] = [
                {
                    'product_id': str(x['card'].get('product_id') or ''),
                    'slug': str(x['card'].get('slug') or ''),
                    'match_method': x['meta'].get('match_method'),
                }
                for x in members
            ]
            blocked.append(item)
        else:
            safe.append(item)

    return {
        'cards_total': len(full),
        'collision_groups': len(groups),
        'safe_groups': safe,
        'blocked_groups': blocked,
    }


def _copy_primary(canonical: dict, duplicate: dict, package_key: str) -> bool:
    cpacks = _sku_by_pack(canonical)
    dpacks = _sku_by_pack(duplicate)
    csku = cpacks[package_key]
    if _valid_primary(canonical, csku):
        return False
    source_media = _valid_primary(duplicate, dpacks[package_key])
    if not source_media:
        return False

    sm = canonical.get('sku_media') or {}
    media = sm.setdefault('media', [])
    path = str(source_media.get('path') or '')
    existing = next((x for x in media if isinstance(x, dict) and str(x.get('path') or '') == path), None)
    if existing:
        mid = str(existing.get('media_id') or '')
    else:
        used = {str(x.get('media_id') or '') for x in media if isinstance(x, dict)}
        mid = _new_media_id(path, used)
        media.append({
            'media_id': mid,
            'path': path,
            'alt': str(source_media.get('alt') or '').strip() or f"{(canonical.get('content') or {}).get('title') or ''} {csku.get('package') or ''}".strip(),
            'kind': str(source_media.get('kind') or 'product'),
            'sort_order': len(media),
        })
    csku['primary_media_id'] = mid
    return True


def apply_plan(plan: dict) -> dict:
    if plan['blocked_groups']:
        raise RuntimeError(f"identity canonicalization blocked for {len(plan['blocked_groups'])} group(s); no writes performed")
    if not plan['safe_groups']:
        return {'archived_cards': 0, 'media_recovered': 0, 'backup_dir': '', 'db_unchanged': True}

    stamp = _stamp()
    backup = BACKUP_ROOT / f'pcv3-identity-dedupe-{stamp}'
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cards.BASE, backup / 'product_cards_v3')
    db_before = _snapshot_tables()

    cmap = cards.commerce_map()
    products = [x for x in cmap.get('products', []) if isinstance(x, dict)]
    duplicate_ids = {
        row['product_id']
        for group in plan['safe_groups']
        for row in group['duplicates']
    }
    existing_map_ids = {str(x.get('product_id') or '') for x in products}
    missing_map = sorted(x for x in duplicate_ids if x not in existing_map_ids)
    if missing_map:
        raise RuntimeError('duplicate commerce mapping missing before write: ' + ', '.join(missing_map))

    archive_root = cards.BASE / 'archive' / 'duplicates' / stamp
    archive_root.mkdir(parents=True, exist_ok=True)
    archived = 0
    recovered = 0
    archive_manifest = []

    for group in plan['safe_groups']:
        canonical_id = group['canonical_product_id']
        canonical = cards.get(canonical_id)
        if not isinstance(canonical, dict):
            raise RuntimeError(f'{canonical_id}: canonical card disappeared')

        for dup_info in group['duplicates']:
            duplicate_id = dup_info['product_id']
            duplicate = cards.get(duplicate_id)
            if not isinstance(duplicate, dict):
                raise RuntimeError(f'{duplicate_id}: duplicate card disappeared')
            if set(_sku_by_pack(canonical)) != set(_sku_by_pack(duplicate)):
                raise RuntimeError(f'{duplicate_id}: package set changed since preflight')
            for package_key in sorted(_sku_by_pack(canonical)):
                if _copy_primary(canonical, duplicate, package_key):
                    recovered += 1
            cards.validate(canonical)
            src = cards.PRODUCTS / f'{duplicate_id}.json'
            dest = archive_root / src.name
            if not src.exists():
                raise RuntimeError(f'{duplicate_id}: source file missing before archive')
            shutil.move(str(src), str(dest))
            archived += 1
            archive_manifest.append({
                'source_row': group['source_row'],
                'canonical_product_id': canonical_id,
                'archived_product_id': duplicate_id,
                'archived_slug': dup_info['slug'],
                'archive_path': str(dest.relative_to(cards.BASE)),
            })
        cards.put(canonical_id, canonical)

    cmap['products'] = [
        x for x in products
        if str(x.get('product_id') or '') not in duplicate_ids
    ]
    cards._save(cards.COMMERCE_MAP, cmap)
    cards._rebuild_index()
    (archive_root / 'manifest.json').write_text(json.dumps(archive_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    db_after = _snapshot_tables()
    if db_before != db_after:
        raise RuntimeError('commerce database changed during identity canonicalization')

    after_plan = build_plan()
    if after_plan['collision_groups']:
        raise RuntimeError(f"identity collisions remain after apply: {after_plan['collision_groups']}")

    return {
        'archived_cards': archived,
        'media_recovered': recovered,
        'backup_dir': str(backup),
        'archive_dir': str(archive_root),
        'db_unchanged': True,
        'cards_after': after_plan['cards_total'],
        'collision_groups_after': after_plan['collision_groups'],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description='Canonicalize duplicate PCV3 identities using exact approved MASTER source_row.')
    ap.add_argument('--apply-safe', action='store_true', help='Archive exact Organic bridge duplicates only after full preflight and backup.')
    args = ap.parse_args()

    plan = build_plan()
    result = apply_plan(plan) if args.apply_safe else None
    stamp = _stamp()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report = {'schema_version': '1.0', 'mode': 'APPLY_SAFE' if args.apply_safe else 'DRY_RUN', 'plan': plan, 'apply': result}
    path = REPORT_ROOT / f'pcv3-identity-dedupe-{stamp}.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('BB610 PCV3 CANONICAL IDENTITY')
    print('MODE:', report['mode'])
    print('CARDS BEFORE:', plan['cards_total'])
    print('COLLISION GROUPS:', plan['collision_groups'])
    print('SAFE GROUPS:', len(plan['safe_groups']))
    print('BLOCKED GROUPS:', len(plan['blocked_groups']))
    if plan['blocked_groups']:
        for item in plan['blocked_groups'][:20]:
            print('  BLOCKED:', item.get('source_row'), item.get('reason'))
    if result:
        print('ARCHIVED DUPLICATE CARDS:', result['archived_cards'])
        print('PRIMARY MEDIA RECOVERED:', result['media_recovered'])
        print('CARDS AFTER:', result['cards_after'])
        print('COLLISIONS AFTER:', result['collision_groups_after'])
        print('COMMERCE DB UNCHANGED:', 'PASS' if result['db_unchanged'] else 'FAIL')
        print('BACKUP:', result['backup_dir'])
        print('ARCHIVE:', result['archive_dir'])
    print('REPORT:', path)
    if plan['blocked_groups']:
        raise SystemExit(2)
    print('RESULT: PASS')


if __name__ == '__main__':
    main()
