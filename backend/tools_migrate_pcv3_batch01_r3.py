from __future__ import annotations

import re

from backend import tools_migrate_pcv3_batch01_r2 as r2

m = r2.m


def _norm_pack(value: str) -> str:
    s = m._text(value).lower().replace(',', '.')
    s = s.replace('літрів', 'л').replace('літра', 'л').replace('літр', 'л')
    s = s.replace('литров', 'л').replace('литра', 'л').replace('литр', 'л')
    s = s.replace('мілілітрів', 'мл').replace('мілілітра', 'мл').replace('мілілітр', 'мл')
    s = s.replace('миллилитров', 'мл').replace('миллилитра', 'мл').replace('миллилитр', 'мл')
    s = s.replace('кілограмів', 'кг').replace('кілограма', 'кг').replace('кілограм', 'кг')
    s = s.replace('килограммов', 'кг').replace('килограмма', 'кг').replace('килограмм', 'кг')
    s = s.replace('грамів', 'г').replace('грама', 'г').replace('грам', 'г')
    s = s.replace('граммов', 'г').replace('грамма', 'г')
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[^0-9a-zа-яіїєґ.+-]', '', s)
    return s


def _legacy_rows_unique(legacy: dict) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for row in r2._legacy_sku_rows(legacy):
        label = m._text(row.get('variant') or row.get('label') or row.get('name') or row.get('pack') or row.get('package'))
        key = _norm_pack(label)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _build_r3(target: str, legacy: dict, catalog_row: dict, catalog: dict):
    # R2 already handles both cases safely:
    # - commerce SKUs exist -> exact bound SKUs
    # - no commerce SKUs -> structural legacy SKUs, no commerce bindings
    card, cmap, report = r2._build_r2(target, legacy, catalog_row, catalog)

    skus = card['sku_media']['skus']
    media = card['sku_media']['media']
    media_by_path = {x.get('path'): x.get('media_id') for x in media if x.get('path')}
    existing = {_norm_pack(x.get('label') or x.get('package') or '') for x in skus}
    fallback_image = m._product_image(legacy, catalog)

    added = []
    for row in _legacy_rows_unique(legacy):
        label = m._text(row.get('variant') or row.get('label') or row.get('name') or row.get('pack') or row.get('package'))
        key = _norm_pack(label)
        if not key or key in existing:
            continue

        package = m._text(row.get('package') or row.get('pack') or row.get('variant') or row.get('label')) or label
        path = m._sku_image(row) or fallback_image
        primary = None
        if path:
            if path not in media_by_path:
                entry = m._media_entry(path, card['content']['title'], len(media))
                media.append(entry)
                media_by_path[path] = entry['media_id']
            primary = media_by_path[path]

        sku_id = m._sha('sku_', card['product_id'] + '|legacy-unbound|' + key)
        skus.append({
            'sku_id': sku_id,
            'sku_code': '',
            'label': label,
            'package': package,
            'primary_media_id': primary,
            'gallery_media_ids': [],
            'sort_order': len(skus),
            'enabled': True,
        })
        existing.add(key)
        added.append(label)

    for i, sku in enumerate(skus):
        sku['sort_order'] = i

    m.validate(card)
    report['sku_count'] = len(skus)
    report['legacy_unbound_added'] = added
    report['commerce_binding_status'] = (
        'BOUND_COMMERCE_PLUS_LEGACY_UNBOUND' if cmap.get('skus') and added
        else report.get('commerce_binding_status', 'BOUND')
    )
    report['verification'] = 'GENERATED_AWAITING_MANUAL_VERIFY_R3'
    return card, cmap, report


m._build = _build_r3

if __name__ == '__main__':
    m.main()
