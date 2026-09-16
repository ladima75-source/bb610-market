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
from backend.services.product_cards_v3_master import find_master_for_card, normalize_name, source_metadata
from backend.services.product_cards_v3_media import _is_resolvable
from backend.tools_complete_pcv3_media_readiness import _pack_key
from backend.tools_prepare_pcv3_release import _snapshot_tables

ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = ROOT / 'var' / 'release-backups'
REPORT_ROOT = ROOT / 'var' / 'reports'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _full_cards() -> list[dict]:
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


def _media_by_id(card: dict) -> dict[str, dict]:
    return {
        str(x.get('media_id') or ''): x
        for x in (card.get('sku_media') or {}).get('media') or []
        if isinstance(x, dict) and x.get('media_id')
    }


def _valid_media(card: dict, media_id: Any) -> dict | None:
    row = _media_by_id(card).get(str(media_id or ''))
    if not row:
        return None
    path = str(row.get('path') or '').strip()
    return row if path and _is_resolvable(path) else None


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


def _mapping_index() -> dict[str, dict]:
    return {
        str(x.get('product_id') or ''): x
        for x in cards.commerce_map().get('products', [])
        if isinstance(x, dict)
    }


def _card_score(card: dict, mapping: dict | None) -> tuple[int, int, int, int]:
    links = [x for x in (mapping or {}).get('skus') or [] if isinstance(x, dict)]
    real_links = sum(
        1 for x in links
        if str(x.get('existing_commerce_sku_key') or '')
        and not str(x.get('existing_commerce_sku_key') or '').startswith('BB610-')
    )
    photo_count = 0
    code_count = 0
    sku_count = 0
    for sku in (card.get('sku_media') or {}).get('skus') or []:
        if not isinstance(sku, dict) or sku.get('enabled') is False:
            continue
        sku_count += 1
        code_count += int(bool(str(sku.get('sku_code') or '').strip()))
        photo_count += int(_valid_media(card, sku.get('primary_media_id')) is not None)
    return real_links, photo_count, sku_count, code_count


def _choose_canonical(members: list[dict], mappings: dict[str, dict]) -> tuple[dict | None, str]:
    non_op = [m for m in members if not str(m['card'].get('product_id') or '').startswith('prd_op_')]
    if len(non_op) == 1:
        return non_op[0], 'single-non-organic-import-id'

    pool = non_op if non_op else members
    scored = []
    for member in pool:
        pid = str(member['card'].get('product_id') or '')
        scored.append((_card_score(member['card'], mappings.get(pid)), member))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return None, 'no-candidates'
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None, f'canonical score tie {scored[0][0]}'
    return scored[0][1], f'unique-quality-score={scored[0][0]}'


def _copy_media(canonical: dict, source: dict, source_media_id: Any) -> str | None:
    src = _valid_media(source, source_media_id)
    if not src:
        return None
    path = str(src.get('path') or '').strip()
    sm = canonical.get('sku_media') or {}
    media = sm.setdefault('media', [])
    existing = next((x for x in media if isinstance(x, dict) and str(x.get('path') or '') == path), None)
    if existing:
        return str(existing.get('media_id') or '')

    used = {str(x.get('media_id') or '') for x in media if isinstance(x, dict)}
    base = 'med_merge_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:18]
    mid = base
    n = 2
    while mid in used:
        mid = f'{base}_{n}'
        n += 1
    media.append({
        'media_id': mid,
        'path': path,
        'alt': str(src.get('alt') or '').strip(),
        'kind': str(src.get('kind') or 'product'),
        'sort_order': len(media),
    })
    return mid


def _merge_duplicate_into(canonical: dict, duplicate: dict) -> dict:
    cpacks = _sku_by_pack(canonical)
    dpacks = _sku_by_pack(duplicate)
    added_skus = 0
    recovered_primary = 0
    copied_gallery = 0

    for pack, dsku in dpacks.items():
        csku = cpacks.get(pack)
        if csku is not None:
            if _valid_media(canonical, csku.get('primary_media_id')) is None:
                mid = _copy_media(canonical, duplicate, dsku.get('primary_media_id'))
                if mid:
                    csku['primary_media_id'] = mid
                    recovered_primary += 1
            gallery = csku.setdefault('gallery_media_ids', [])
            for gid in dsku.get('gallery_media_ids') or []:
                mid = _copy_media(canonical, duplicate, gid)
                if mid and mid not in gallery:
                    gallery.append(mid)
                    copied_gallery += 1
            continue

        new_sku = deepcopy(dsku)
        existing_ids = {
            str(x.get('sku_id') or '')
            for x in (canonical.get('sku_media') or {}).get('skus') or []
            if isinstance(x, dict)
        }
        sid = str(new_sku.get('sku_id') or '')
        if not sid or sid in existing_ids:
            token = hashlib.sha1(
                f"{canonical.get('product_id')}|{pack}|{duplicate.get('product_id')}".encode('utf-8')
            ).hexdigest()[:18]
            new_sku['sku_id'] = f'sku_merge_{token}'
        # The duplicate commerce product is being archived from v3 mapping. Do not
        # carry its commerce sku_code into the canonical product. Release-prep R2
        # will create/bind the correct safe draft under the canonical commerce parent.
        new_sku['sku_code'] = ''
        primary = _copy_media(canonical, duplicate, dsku.get('primary_media_id'))
        new_sku['primary_media_id'] = primary
        new_gallery: list[str] = []
        for gid in dsku.get('gallery_media_ids') or []:
            mid = _copy_media(canonical, duplicate, gid)
            if mid and mid not in new_gallery:
                new_gallery.append(mid)
        new_sku['gallery_media_ids'] = new_gallery
        new_sku['sort_order'] = len((canonical.get('sku_media') or {}).get('skus') or [])
        (canonical.get('sku_media') or {}).setdefault('skus', []).append(new_sku)
        cpacks[pack] = new_sku
        added_skus += 1
        recovered_primary += int(bool(primary))
        copied_gallery += len(new_gallery)

    for i, sku in enumerate((canonical.get('sku_media') or {}).get('skus') or []):
        if isinstance(sku, dict):
            sku['sort_order'] = i

    return {
        'added_skus': added_skus,
        'recovered_primary': recovered_primary,
        'copied_gallery': copied_gallery,
    }


def build_plan() -> dict:
    full = _full_cards()
    groups = _groups(full)
    mappings = _mapping_index()
    safe: list[dict] = []
    blocked: list[dict] = []

    for source_row, members in sorted(groups.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 10**9):
        reason = ''
        for member in members:
            meta = member['meta']
            if not meta.get('verified'):
                reason = 'member has unverified MASTER source'
                break
            card = member['card']
            title = normalize_name((card.get('content') or {}).get('title'))
            master = find_master_for_card(card) or {}
            master_title = normalize_name(master.get('name'))
            if not title or not master_title or title != master_title:
                reason = 'member title no longer equals its verified MASTER identity'
                break
            try:
                _sku_by_pack(card)
            except Exception as exc:
                reason = str(exc)
                break

        canonical, selection = _choose_canonical(members, mappings) if not reason else (None, '')
        if not reason and canonical is None:
            reason = 'cannot choose canonical safely: ' + selection

        item = {
            'source_row': int(source_row) if source_row.isdigit() else source_row,
            'selection': selection,
            'members': [
                {
                    'product_id': str(x['card'].get('product_id') or ''),
                    'slug': str(x['card'].get('slug') or ''),
                    'title': str((x['card'].get('content') or {}).get('title') or ''),
                    'packages': sorted(_sku_by_pack(x['card'])) if not reason else [],
                    'score': list(_card_score(x['card'], mappings.get(str(x['card'].get('product_id') or '')))),
                }
                for x in members
            ],
        }
        if reason:
            item['reason'] = reason
            blocked.append(item)
            continue

        canonical_id = str(canonical['card'].get('product_id') or '')
        item['canonical_product_id'] = canonical_id
        item['duplicates'] = [
            str(x['card'].get('product_id') or '') for x in members
            if str(x['card'].get('product_id') or '') != canonical_id
        ]
        union_packs = set()
        for x in members:
            union_packs.update(_sku_by_pack(x['card']))
        item['union_packages'] = sorted(union_packs)
        safe.append(item)

    return {
        'cards_total': len(full),
        'collision_groups': len(groups),
        'safe_groups': safe,
        'blocked_groups': blocked,
    }


def _restore_backup(backup: Path) -> None:
    saved = backup / 'product_cards_v3'
    if not saved.is_dir():
        raise RuntimeError(f'identity backup missing: {saved}')
    if cards.BASE.exists():
        shutil.rmtree(cards.BASE)
    shutil.copytree(saved, cards.BASE)


def apply_plan(plan: dict) -> dict:
    if plan['blocked_groups']:
        raise RuntimeError(
            f"identity R2 blocked for {len(plan['blocked_groups'])} group(s); no writes performed"
        )
    if not plan['safe_groups']:
        return {
            'archived_cards': 0,
            'added_skus': 0,
            'recovered_primary': 0,
            'backup_dir': '',
            'db_unchanged': True,
            'cards_after': plan['cards_total'],
            'collision_groups_after': 0,
        }

    stamp = _stamp()
    backup = BACKUP_ROOT / f'pcv3-identity-r2-{stamp}'
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cards.BASE, backup / 'product_cards_v3')
    db_before = _snapshot_tables()

    archive_root = cards.BASE / 'archive' / 'duplicates' / stamp
    archive_root.mkdir(parents=True, exist_ok=True)
    cmap = cards.commerce_map()
    map_rows = [x for x in cmap.get('products', []) if isinstance(x, dict)]

    archived = added_skus = recovered_primary = copied_gallery = 0
    manifest: list[dict] = []
    duplicate_ids: set[str] = set()

    try:
        for group in plan['safe_groups']:
            canonical_id = group['canonical_product_id']
            canonical = cards.get(canonical_id)
            if not isinstance(canonical, dict):
                raise RuntimeError(f'{canonical_id}: canonical card disappeared')

            group_log = {
                'source_row': group['source_row'],
                'canonical_product_id': canonical_id,
                'selection': group['selection'],
                'archived': [],
            }
            for duplicate_id in group['duplicates']:
                duplicate = cards.get(duplicate_id)
                if not isinstance(duplicate, dict):
                    raise RuntimeError(f'{duplicate_id}: duplicate card disappeared')
                merged = _merge_duplicate_into(canonical, duplicate)
                added_skus += merged['added_skus']
                recovered_primary += merged['recovered_primary']
                copied_gallery += merged['copied_gallery']

                src = cards.PRODUCTS / f'{duplicate_id}.json'
                if not src.is_file():
                    raise RuntimeError(f'{duplicate_id}: product file missing before archive')
                dest = archive_root / src.name
                shutil.move(str(src), str(dest))
                duplicate_ids.add(duplicate_id)
                archived += 1
                group_log['archived'].append({
                    'product_id': duplicate_id,
                    'slug': duplicate.get('slug'),
                    'archive_path': str(dest.relative_to(cards.BASE)),
                    'packages': sorted(_sku_by_pack(duplicate)),
                })

            cards.validate(canonical)
            cards.put(canonical_id, canonical)
            manifest.append(group_log)

        cmap['products'] = [
            x for x in map_rows
            if str(x.get('product_id') or '') not in duplicate_ids
        ]
        cards._save(cards.COMMERCE_MAP, cmap)
        cards._rebuild_index()
        (archive_root / 'manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

        if _snapshot_tables() != db_before:
            raise RuntimeError('commerce database changed during identity R2 canonicalization')
        after = build_plan()
        if after['collision_groups']:
            raise RuntimeError(f"identity collisions remain after R2: {after['collision_groups']}")
    except Exception:
        _restore_backup(backup)
        print('AUTO ROLLBACK:', backup)
        print('AUTO ROLLBACK RESULT: PASS')
        raise

    return {
        'archived_cards': archived,
        'added_skus': added_skus,
        'recovered_primary': recovered_primary,
        'copied_gallery': copied_gallery,
        'backup_dir': str(backup),
        'archive_dir': str(archive_root),
        'db_unchanged': True,
        'cards_after': len(cards.list_cards()),
        'collision_groups_after': 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description='PCV3 identity canonicalization R2: preserve one verified MASTER card per source row and merge SKU/media safely.'
    )
    ap.add_argument('--apply-safe', action='store_true')
    args = ap.parse_args()

    plan = build_plan()
    result = apply_plan(plan) if args.apply_safe else None
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f'pcv3-identity-r2-{_stamp()}.json'
    payload = {
        'schema_version': '2.0',
        'mode': 'APPLY_SAFE' if args.apply_safe else 'DRY_RUN',
        'plan': plan,
        'apply': result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('BB610 PCV3 CANONICAL IDENTITY R2')
    print('MODE:', payload['mode'])
    print('CARDS BEFORE:', plan['cards_total'])
    print('COLLISION GROUPS:', plan['collision_groups'])
    print('SAFE GROUPS:', len(plan['safe_groups']))
    print('BLOCKED GROUPS:', len(plan['blocked_groups']))
    for item in plan['blocked_groups'][:20]:
        print('  BLOCKED:', item.get('source_row'), item.get('reason'))
    if result:
        print('ARCHIVED DUPLICATE CARDS:', result['archived_cards'])
        print('MERGED UNIQUE SKU:', result['added_skus'])
        print('PRIMARY MEDIA RECOVERED:', result['recovered_primary'])
        print('GALLERY MEDIA COPIED:', result['copied_gallery'])
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
