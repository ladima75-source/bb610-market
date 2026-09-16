from __future__ import annotations

from collections import defaultdict
from typing import Any

from . import product_cards_v3 as cards
from .product_cards_v3_master import find_master_for_card, source_metadata
from .product_cards_v3_media import _is_resolvable


def _text(v: Any) -> str:
    return str(v or '').strip()


def _identity_groups(full_cards: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for card in full_cards:
        meta = source_metadata(find_master_for_card(card))
        source_row = meta.get('source_row')
        if source_row is None:
            continue
        key = str(source_row)
        groups[key].append({
            'product_id': _text(card.get('product_id')),
            'slug': _text(card.get('slug')),
            'title': _text((card.get('content') or {}).get('title')),
            'brand': _text((card.get('content') or {}).get('brand')),
            'match_method': _text(meta.get('match_method')),
            'source_row': source_row,
        })
    collisions = []
    for source_row, members in sorted(groups.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 10**9):
        if len(members) > 1:
            collisions.append({'source_row': int(source_row) if source_row.isdigit() else source_row, 'members': members})
    return groups, collisions


def _content_issues(card: dict) -> list[str]:
    content = card.get('content') or {}
    issues: list[str] = []
    if not card.get('enabled'):
        issues.append('card_disabled')
    if not _text(content.get('brand')):
        issues.append('brand_missing')
    if not _text(content.get('category')):
        issues.append('category_missing')
    if len(_text(content.get('short_description'))) < 30:
        issues.append('short_description_weak')
    if len(_text(content.get('description'))) < 80:
        issues.append('description_weak')
    if not content.get('benefits'):
        issues.append('benefits_missing')
    if len(_text(content.get('how_it_works'))) < 20:
        issues.append('how_it_works_missing')
    if len(_text(content.get('application'))) < 20:
        issues.append('application_missing')
    if len(_text(content.get('composition'))) < 10:
        issues.append('composition_missing')
    if len(content.get('characteristics') or []) < 2:
        issues.append('characteristics_weak')
    seo = content.get('seo') or {}
    if not _text(seo.get('title')) or len(_text(seo.get('description'))) < 50:
        issues.append('seo_incomplete')
    return issues


def preprice_report() -> dict:
    cmap = cards.commerce_map()
    map_by_pid = {
        str(x.get('product_id') or ''): x
        for x in cmap.get('products', [])
        if isinstance(x, dict)
    }

    full_cards: list[dict] = []
    for summary in cards.list_cards():
        card = cards.get(str(summary.get('product_id') or ''))
        if isinstance(card, dict):
            full_cards.append(card)

    _, collisions = _identity_groups(full_cards)
    duplicate_pids = {
        str(member.get('product_id') or '')
        for group in collisions
        for member in group.get('members') or []
        if member.get('product_id')
    }

    total_cards = ready_cards = total_skus = ready_skus = 0
    issue_counts: dict[str, int] = {}
    gaps: list[dict] = []

    def add_issue(code: str) -> None:
        issue_counts[code] = issue_counts.get(code, 0) + 1

    for card in full_cards:
        pid = str(card.get('product_id') or '')
        total_cards += 1
        card_issues: list[str] = []
        try:
            cards.validate(card)
        except Exception:
            card_issues.append('schema')
        card_issues.extend(_content_issues(card))
        master_meta = source_metadata(find_master_for_card(card))
        if not master_meta.get('verified'):
            card_issues.append('source')
        if pid in duplicate_pids:
            card_issues.append('identity_duplicate')

        mapping = map_by_pid.get(pid)
        if not mapping:
            card_issues.append('commerce_mapping')
            links = {}
        else:
            links = {
                str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
                for x in mapping.get('skus') or []
                if isinstance(x, dict)
            }

        sm = card.get('sku_media') or {}
        media_rows = [m for m in (sm.get('media') or []) if isinstance(m, dict)]
        media_by_id = {str(m.get('media_id') or ''): m for m in media_rows}
        enabled_skus = [s for s in (sm.get('skus') or []) if isinstance(s, dict) and s.get('enabled') is not False]
        if not enabled_skus:
            card_issues.append('sku_missing')

        card_sku_ready = 0
        for sku in enabled_skus:
            total_skus += 1
            sid = str(sku.get('sku_id') or '')
            package = _text(sku.get('package') or sku.get('label'))
            issues: list[str] = []
            if not _text(sku.get('sku_code')):
                issues.append('sku_code')
            if not links.get(sid):
                issues.append('sku_binding')
            mid = str(sku.get('primary_media_id') or '')
            media = media_by_id.get(mid)
            if not media:
                issues.append('photo_missing')
            else:
                path = _text(media.get('path'))
                if not path or not _is_resolvable(path):
                    issues.append('photo_invalid')
                if not _text(media.get('alt')):
                    issues.append('photo_alt')
            if pid in duplicate_pids and 'identity_duplicate' not in issues:
                issues.append('identity_duplicate')
            if issues:
                for code in issues:
                    add_issue(code)
                gaps.append({
                    'product_id': pid,
                    'title': _text((card.get('content') or {}).get('title')),
                    'brand': _text((card.get('content') or {}).get('brand')),
                    'slug': _text(card.get('slug')),
                    'source_row': master_meta.get('source_row'),
                    'source_match_method': _text(master_meta.get('match_method')),
                    'sku_id': sid,
                    'sku_code': _text(sku.get('sku_code')),
                    'package': package,
                    'issues': issues,
                })
            else:
                ready_skus += 1
                card_sku_ready += 1

        for code in set(card_issues):
            add_issue(code)
        if card_issues:
            gaps.append({
                'product_id': pid,
                'title': _text((card.get('content') or {}).get('title')),
                'brand': _text((card.get('content') or {}).get('brand')),
                'slug': _text(card.get('slug')),
                'source_row': master_meta.get('source_row'),
                'source_match_method': _text(master_meta.get('match_method')),
                'sku_id': '',
                'sku_code': '',
                'package': '',
                'issues': sorted(set(card_issues)),
            })

        if not card_issues and enabled_skus and card_sku_ready == len(enabled_skus):
            ready_cards += 1

    gaps.sort(key=lambda x: (x.get('brand','').lower(), x.get('title','').lower(), x.get('package','')))
    complete = bool(
        total_cards and
        ready_cards == total_cards and
        ready_skus == total_skus and
        not collisions
    )
    return {
        'schema_version': '1.2',
        'price_gate': 'FROZEN_NOT_PART_OF_THIS_GATE',
        'summary': {
            'cards_total': total_cards,
            'cards_preprice_ready': ready_cards,
            'skus_total': total_skus,
            'skus_preprice_ready': ready_skus,
            'identity_collision_groups': len(collisions),
            'identity_duplicate_cards': len(duplicate_pids),
            'canonical_source_rows': len({
                str(source_metadata(find_master_for_card(card)).get('source_row'))
                for card in full_cards
                if source_metadata(find_master_for_card(card)).get('source_row') is not None
            }),
            'gaps_total': len(gaps),
            'issue_counts': dict(sorted(issue_counts.items())),
            'complete': complete,
        },
        'identity_collisions': collisions,
        'gaps': gaps,
    }
