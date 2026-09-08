from __future__ import annotations

from typing import Any

from backend import tools_migrate_pcv3_batch01 as m


def _legacy_sku_rows(legacy: dict) -> list[dict]:
    """Read legacy SKU/pack information only as structure/media source.
    No legacy identifier is assumed to be a commerce key.
    """
    candidates: list[Any] = []
    for key in ('skus', 'variants', 'offers', 'sku_photo'):
        value = legacy.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            candidates.extend(value.values())
    v2 = legacy.get('product_card_v2')
    if isinstance(v2, dict):
        for key in ('skus', 'variants', 'sku_photo'):
            value = v2.get(key)
            if isinstance(value, list):
                candidates.extend(value)
            elif isinstance(value, dict):
                candidates.extend(value.values())
    return [x for x in candidates if isinstance(x, dict)]


def _unbound_build(target: str, legacy: dict, catalog_row: dict, catalog: dict):
    v2 = legacy.get('product_card_v2') if isinstance(legacy.get('product_card_v2'), dict) else {}
    product_id = m._sha('prd_', 'pcv3|batch01|' + target)
    title = m._text(v2.get('name') or v2.get('display_name') or legacy.get('official_name') or legacy.get('name') or catalog.get('official_name') or catalog.get('name')) or target
    slug = str(catalog_row.get('slug') or catalog.get('slug') or legacy.get('slug') or m._slug(target)).strip().lower()
    brand = m._text(v2.get('brand') or legacy.get('brand') or catalog.get('brand'))
    category = m._text(legacy.get('category_label') or legacy.get('category') or catalog.get('category_label') or catalog.get('category_id'))
    short = m._text(v2.get('short_description') or v2.get('lead') or v2.get('subtitle') or legacy.get('short_description') or catalog.get('short_description'))
    description = m._text(v2.get('full_description') or legacy.get('description') or catalog.get('description'))

    fallback_image = m._product_image(legacy, catalog)
    media: list[dict] = []
    media_by_path: dict[str, str] = {}
    skus: list[dict] = []

    legacy_rows = _legacy_sku_rows(legacy)
    if legacy_rows:
        for i, row in enumerate(legacy_rows):
            path = m._sku_image(row) or fallback_image
            primary = None
            if path:
                if path not in media_by_path:
                    entry = m._media_entry(path, title, len(media))
                    media.append(entry)
                    media_by_path[path] = entry['media_id']
                primary = media_by_path[path]
            label = m._text(row.get('variant') or row.get('label') or row.get('name') or row.get('pack') or row.get('package')) or f'Фасування {i + 1}'
            package = m._text(row.get('package') or row.get('pack') or row.get('variant') or row.get('label')) or label
            sku_id = m._sha('sku_', product_id + '|unbound|' + str(i) + '|' + label)
            skus.append({
                'sku_id': sku_id,
                'sku_code': '',
                'label': label,
                'package': package,
                'primary_media_id': primary,
                'gallery_media_ids': [],
                'sort_order': i,
                'enabled': True,
            })
    else:
        packs = catalog.get('factory_packs') or legacy.get('factory_packs') or []
        if not isinstance(packs, list):
            packs = [packs] if packs else []
        clean_packs = [m._text(x) for x in packs if m._text(x)]
        if not clean_packs:
            clean_packs = ['Фасування не налаштовано']
        for i, label in enumerate(clean_packs):
            primary = None
            if fallback_image:
                if fallback_image not in media_by_path:
                    entry = m._media_entry(fallback_image, title, len(media))
                    media.append(entry)
                    media_by_path[fallback_image] = entry['media_id']
                primary = media_by_path[fallback_image]
            sku_id = m._sha('sku_', product_id + '|unbound|' + str(i) + '|' + label)
            skus.append({
                'sku_id': sku_id,
                'sku_code': '',
                'label': label,
                'package': label,
                'primary_media_id': primary,
                'gallery_media_ids': [],
                'sort_order': i,
                'enabled': True,
            })

    card = {
        'schema_version': '3.0',
        'product_id': product_id,
        'slug': slug,
        'enabled': True,
        'content': {
            'title': title,
            'brand': brand,
            'category': category,
            'short_description': short,
            'description': description,
            'benefits': m._benefits(legacy, v2),
            'how_it_works': m._how(legacy, v2),
            'application': m._application(legacy, v2),
            'composition': m._composition(legacy, v2, catalog),
            'characteristics': m._characteristics(legacy, v2),
            'seo': {
                'title': m._text((v2.get('seo') or {}).get('title') if isinstance(v2.get('seo'), dict) else ''),
                'description': m._text((v2.get('seo') or {}).get('description') if isinstance(v2.get('seo'), dict) else ''),
            },
        },
        'sku_media': {'skus': skus, 'media': media},
    }
    m.validate(card)

    existing_product_key = str(catalog_row.get('id') or catalog.get('id') or '').strip()
    cmap = {
        'product_id': product_id,
        'existing_product_key': existing_product_key,
        'skus': [],
    }
    report = {
        'name': target,
        'product_id': product_id,
        'slug': slug,
        'legacy_identity': {
            'id': legacy.get('id'),
            'product_id': legacy.get('product_id'),
            'slug': legacy.get('slug'),
            'source_row': (legacy.get('import_meta') or {}).get('organic_planet_source_row') if isinstance(legacy.get('import_meta'), dict) else None,
        },
        'existing_product_key': existing_product_key,
        'sku_count': len(skus),
        'commerce_sku_keys': [],
        'commerce_binding_status': 'UNMAPPED_NO_EXISTING_COMMERCE_SKU',
        'media_paths': [x['path'] for x in media],
        'verification': 'GENERATED_AWAITING_MANUAL_VERIFY',
    }
    return card, cmap, report


_original_build = m._build


def _build_r2(target: str, legacy: dict, catalog_row: dict, catalog: dict):
    try:
        return _original_build(target, legacy, catalog_row, catalog)
    except RuntimeError as exc:
        if 'catalog product has no SKU' not in str(exc):
            raise
        # Important: absence of a commerce SKU is preserved as absence.
        # We create only v3 structural SKU(s) from existing legacy pack/media data.
        # commerce_map.skus remains empty; no price/stock/availability guess is made.
        return _unbound_build(target, legacy, catalog_row, catalog)


m._build = _build_r2

if __name__ == '__main__':
    m.main()
