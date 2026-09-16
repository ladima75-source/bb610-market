from __future__ import annotations

from typing import Any

from . import product_cards_v3 as cards
from .product_cards_v3_master import find_master_for_card, source_metadata
from .product_cards_v3_media import _is_resolvable


def _text(v: Any) -> str:
    return str(v or '').strip()


def preprice_report() -> dict:
    cmap = cards.commerce_map()
    map_by_pid = {
        str(x.get('product_id') or ''): x
        for x in cmap.get('products', [])
        if isinstance(x, dict)
    }

    total_cards = ready_cards = total_skus = ready_skus = 0
    issue_counts: dict[str, int] = {}
    gaps: list[dict] = []

    def add_issue(code: str) -> None:
        issue_counts[code] = issue_counts.get(code, 0) + 1

    for summary in cards.list_cards():
        pid = str(summary.get('product_id') or '')
        card = cards.get(pid)
        if not isinstance(card, dict):
            continue
        total_cards += 1
        card_issues: list[str] = []
        try:
            cards.validate(card)
        except Exception:
            card_issues.append('schema')
        if not source_metadata(find_master_for_card(card)).get('verified'):
            card_issues.append('source')

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
            if issues:
                for code in issues:
                    add_issue(code)
                gaps.append({
                    'product_id': pid,
                    'title': _text((card.get('content') or {}).get('title')),
                    'brand': _text((card.get('content') or {}).get('brand')),
                    'slug': _text(card.get('slug')),
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
                'sku_id': '',
                'sku_code': '',
                'package': '',
                'issues': sorted(set(card_issues)),
            })

        if not card_issues and enabled_skus and card_sku_ready == len(enabled_skus):
            ready_cards += 1

    gaps.sort(key=lambda x: (x.get('brand','').lower(), x.get('title','').lower(), x.get('package','')))
    return {
        'schema_version': '1.0',
        'price_gate': 'FROZEN_NOT_PART_OF_THIS_GATE',
        'summary': {
            'cards_total': total_cards,
            'cards_preprice_ready': ready_cards,
            'skus_total': total_skus,
            'skus_preprice_ready': ready_skus,
            'gaps_total': len(gaps),
            'issue_counts': dict(sorted(issue_counts.items())),
            'complete': bool(total_cards and ready_cards == total_cards and ready_skus == total_skus),
        },
        'gaps': gaps,
    }
