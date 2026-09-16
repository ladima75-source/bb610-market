from __future__ import annotations

from collections import Counter
from typing import Any

from . import product_cards_v3 as cards
from .product_cards_v3_master import find_master_for_card, source_metadata

SELLABLE_AVAILABILITY = {'in_stock', 'preorder', 'backorder'}


def _text(value: Any) -> str:
    return str(value or '').strip()


def _issue(items: list[dict], code: str, label: str, area: str, severity: str = 'review') -> None:
    items.append({'code': code, 'label': label, 'area': area, 'severity': severity})


def _card_quality(card: dict) -> dict:
    content = card.get('content') or {}
    sm = card.get('sku_media') or {}
    skus = sm.get('skus') or []
    media = sm.get('media') or []
    enabled_skus = [s for s in skus if s.get('enabled') is not False]
    media_ids = {m.get('media_id') for m in media if isinstance(m, dict)}
    issues: list[dict] = []
    checks: list[tuple[bool, int]] = []

    def check(ok: bool, weight: int, code: str, label: str, area: str, severity: str = 'review') -> bool:
        checks.append((bool(ok), weight))
        if not ok:
            _issue(issues, code, label, area, severity)
        return bool(ok)

    enabled = check(bool(card.get('enabled')), 4, 'card_disabled', 'Картка v3 вимкнена', 'card', 'blocker')
    brand_ok = check(bool(_text(content.get('brand'))), 5, 'brand_missing', 'Не вказано бренд', 'content', 'blocker')
    category_ok = check(bool(_text(content.get('category'))), 5, 'category_missing', 'Не вказано категорію', 'content', 'blocker')
    short_ok = check(len(_text(content.get('short_description'))) >= 30, 6, 'short_description_weak', 'Короткий опис відсутній або занадто короткий', 'content', 'blocker')
    description_ok = check(len(_text(content.get('description'))) >= 80, 10, 'description_weak', 'Повний опис відсутній або занадто короткий', 'content', 'blocker')
    application_ok = check(len(_text(content.get('application'))) >= 20, 7, 'application_missing', 'Немає повного способу застосування', 'content', 'blocker')
    composition_ok = check(len(_text(content.get('composition'))) >= 10, 6, 'composition_missing', 'Не заповнено склад / формулу', 'content', 'blocker')
    check(bool(content.get('benefits')), 4, 'benefits_missing', 'Не заповнено переваги', 'content')
    check(len(content.get('characteristics') or []) >= 2, 4, 'characteristics_weak', 'Менше двох характеристик', 'content')
    check(len(_text(content.get('how_it_works'))) >= 20, 4, 'how_it_works_missing', 'Не описано принцип дії', 'content')
    seo = content.get('seo') or {}
    check(bool(_text(seo.get('title'))) and len(_text(seo.get('description'))) >= 50, 4, 'seo_incomplete', 'SEO title / description не завершені', 'seo')

    master = find_master_for_card(card)
    source = source_metadata(master)
    source_verified = check(bool(source.get('verified')), 8, 'source_not_verified', 'Немає підтвердженої MASTER-картки з джерелом', 'source', 'blocker')

    sku_exists = check(bool(enabled_skus), 5, 'sku_missing', 'Немає активних SKU у картці', 'sku', 'blocker')
    sku_structure_ok = bool(enabled_skus) and all(_text(s.get('label')) and _text(s.get('package')) for s in enabled_skus)
    check(sku_structure_ok, 7, 'sku_structure_incomplete', 'У SKU не заповнено фасування / package', 'sku', 'blocker')
    media_ok = bool(enabled_skus) and all(s.get('primary_media_id') in media_ids for s in enabled_skus)
    check(media_ok, 10, 'sku_photo_missing', 'Не кожен активний SKU має основне фото', 'media', 'blocker')
    alt_ok = bool(media) and all(_text(m.get('alt')) for m in media if isinstance(m, dict))
    check(alt_ok, 3, 'media_alt_missing', 'У частини медіа відсутній alt', 'media')

    commerce = cards.commerce_view(card.get('product_id'))
    mapped = bool(commerce.get('mapped'))
    check(mapped, 5, 'commerce_unmapped', 'Картка не прив’язана до commerce-каталогу', 'commerce', 'blocker')
    detail = commerce.get('commerce') or {}
    published = mapped and bool(detail.get('published'))
    check(published, 4, 'commerce_unpublished', 'Товар не опублікований у commerce', 'commerce', 'blocker')
    commerce_skus = detail.get('skus') or []
    active_commerce = [s for s in commerce_skus if s.get('enabled')]
    priced = [s for s in active_commerce if isinstance(s.get('price'), (int, float)) and s.get('price') > 0]
    sellable = [s for s in priced if _text(s.get('availability')) in SELLABLE_AVAILABILITY]
    check(bool(priced), 3, 'commerce_price_missing', 'Немає активного SKU з ціною', 'commerce', 'blocker')
    check(bool(sellable), 4, 'commerce_not_sellable', 'Немає SKU, доступного до продажу', 'commerce', 'blocker')

    total_weight = sum(weight for _, weight in checks) or 1
    earned = sum(weight for ok, weight in checks if ok)
    score = round(earned * 100 / total_weight)

    core_complete = all((enabled, brand_ok, category_ok, short_ok, description_ok, application_ok, composition_ok, sku_exists, sku_structure_ok))
    publication_ready = core_complete and source_verified and media_ok and mapped and published and bool(sellable)
    if not core_complete:
        status = 'DRAFT'
    elif publication_ready and score >= 90:
        status = 'READY'
    else:
        status = 'REVIEW'

    enabled_media_count = sum(1 for s in enabled_skus if s.get('primary_media_id') in media_ids)
    return {
        'product_id': card.get('product_id'),
        'slug': card.get('slug'),
        'title': _text(content.get('title')),
        'brand': _text(content.get('brand')),
        'category': _text(content.get('category')),
        'status': status,
        'score': score,
        'publication_ready': publication_ready,
        'issues': issues,
        'issue_codes': [x['code'] for x in issues],
        'source_matched': bool(source.get('matched')),
        'source_verified': bool(source.get('verified')),
        'source_verified_date': _text(source.get('verified_date')),
        'source_count': int(source.get('source_count') or 0),
        'source_master_file': _text(source.get('master_file')),
        'source_row': source.get('source_row'),
        'sku_count': len(skus),
        'enabled_sku_count': len(enabled_skus),
        'sku_with_photo_count': enabled_media_count,
        'commerce_mapped': mapped,
        'commerce_published': published,
        'commerce_sku_count': len(commerce_skus),
        'commerce_active_sku_count': len(active_commerce),
        'commerce_sellable_sku_count': len(sellable),
    }


def quality_report() -> dict:
    evaluated: list[dict] = []
    for row in cards.list_cards():
        card = cards.get(str(row.get('product_id') or ''))
        if isinstance(card, dict):
            evaluated.append(_card_quality(card))

    status_rank = {'DRAFT': 0, 'REVIEW': 1, 'READY': 2}
    evaluated.sort(key=lambda x: (status_rank.get(str(x.get('status')), 9), int(x.get('score') or 0), (x.get('title') or '').lower()))
    status_counts = Counter(x['status'] for x in evaluated)
    issue_counts: Counter[str] = Counter()
    issue_labels: dict[str, str] = {}
    for item in evaluated:
        for issue in item.get('issues') or []:
            code = issue.get('code')
            if not code:
                continue
            issue_counts[code] += 1
            issue_labels[code] = issue.get('label') or code

    total = len(evaluated)
    sku_total = sum(int(x.get('enabled_sku_count') or 0) for x in evaluated)
    sku_with_photo = sum(int(x.get('sku_with_photo_count') or 0) for x in evaluated)
    mapped = sum(1 for x in evaluated if x.get('commerce_mapped'))
    published = sum(1 for x in evaluated if x.get('commerce_published'))
    sellable = sum(1 for x in evaluated if int(x.get('commerce_sellable_sku_count') or 0) > 0)
    source_matched = sum(1 for x in evaluated if x.get('source_matched'))
    source_verified = sum(1 for x in evaluated if x.get('source_verified'))
    average_score = round(sum(int(x.get('score') or 0) for x in evaluated) / total) if total else 0
    top_issues = [
        {'code': code, 'label': issue_labels.get(code, code), 'count': count}
        for code, count in issue_counts.most_common()
    ]

    return {
        'schema_version': '1.1',
        'summary': {
            'total': total,
            'draft': status_counts.get('DRAFT', 0),
            'review': status_counts.get('REVIEW', 0),
            'ready': status_counts.get('READY', 0),
            'average_score': average_score,
            'enabled_sku_total': sku_total,
            'sku_with_photo': sku_with_photo,
            'source_matched': source_matched,
            'source_verified': source_verified,
            'commerce_mapped': mapped,
            'commerce_published': published,
            'sellable_products': sellable,
            'issue_count': sum(len(x.get('issues') or []) for x in evaluated),
        },
        'top_issues': top_issues,
        'items': evaluated,
    }
