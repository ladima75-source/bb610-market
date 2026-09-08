from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from backend import tools_migrate_pcv3_batch01 as base
from backend import tools_migrate_pcv3_batch01_r3 as r3
from backend.services import product_cards_v3 as svc
from backend.services.catalog_cms import admin_detail as catalog_detail, admin_list_products

BATCH_SIZE = 15
EXCLUDED_IDS = {'bb610-order-test'}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identity(card: dict) -> set[str]:
    out: set[str] = set()
    for value in base._identity_values(card):
        n = base._norm(value)
        if n:
            out.add(n)
    return out


def _legacy_index(cards: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    exact: dict[str, list[dict]] = {}
    names: dict[str, list[dict]] = {}
    for card in cards:
        for key in ('id', 'product_id', 'slug'):
            raw = str(card.get(key) or '').strip().lower()
            if raw:
                exact.setdefault(raw, []).append(card)
        for key in ('name', 'official_name', 'title'):
            n = base._norm(card.get(key))
            if n:
                names.setdefault(n, []).append(card)
        v2 = card.get('product_card_v2')
        if isinstance(v2, dict):
            for key in ('name', 'display_name', 'title'):
                n = base._norm(v2.get(key))
                if n:
                    names.setdefault(n, []).append(card)
    return exact, names


def _richness(card: dict, catalog_id: str) -> int:
    score = 0
    for key in ('id', 'product_id', 'slug'):
        if str(card.get(key) or '').strip().lower() == catalog_id.lower():
            score += 1000
    v2 = card.get('product_card_v2')
    if isinstance(v2, dict):
        score += 500 + len(json.dumps(v2, ensure_ascii=False)) // 100
    for key in ('description', 'short_description', 'application', 'composition', 'characteristics', 'benefits'):
        value = card.get(key)
        if value:
            score += min(100, len(base._text(value)) // 20 + 1)
    return score


def _choose_legacy(catalog_id: str, detail: dict, exact: dict[str, list[dict]], names: dict[str, list[dict]]) -> tuple[dict, str]:
    candidates: list[dict] = []
    for raw in (catalog_id, detail.get('slug')):
        raw = str(raw or '').strip().lower()
        candidates.extend(exact.get(raw, []))
    if not candidates:
        for raw in (detail.get('name'), detail.get('official_name')):
            n = base._norm(raw)
            if n:
                candidates.extend(names.get(n, []))

    uniq: list[dict] = []
    seen: set[str] = set()
    for card in candidates:
        marker = json.dumps(card, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            uniq.append(card)

    if uniq:
        uniq.sort(key=lambda c: _richness(c, catalog_id), reverse=True)
        if len(uniq) > 1 and _richness(uniq[0], catalog_id) == _richness(uniq[1], catalog_id):
            raise RuntimeError(f'{catalog_id}: ambiguous legacy source ({len(uniq)} equal candidates)')
        return uniq[0], 'legacy'

    # Safe fallback: current catalog detail is already the canonical legacy/public source.
    # This never invents price/stock/availability; commerce still comes only from exact catalog SKUs.
    return deepcopy(detail), 'catalog-fallback'


def _eligible(row: dict, detail: dict) -> bool:
    pid = str(row.get('id') or detail.get('id') or '').strip()
    if not pid or pid in EXCLUDED_IDS:
        return False
    if detail.get('internal_only'):
        return False
    if str(detail.get('store_content_status') or '').lower() == 'internal-test':
        return False
    return True


def _save_commerce_map(obj: dict) -> None:
    base._save(svc.COMMERCE_MAP, obj)


def _manifest(previous: Any, batches: list[dict], totals: dict) -> dict:
    history: list[dict] = []
    if isinstance(previous, dict) and previous:
        history.append(previous)
    return {
        'schema_version': '1.1',
        'scope': 'ALL_REAL_CATALOG_PRODUCTS',
        'status': 'GENERATED_TECHNICAL_VERIFY_REQUIRED',
        'generated_at': _now(),
        'batch_size': BATCH_SIZE,
        'totals': totals,
        'batches': batches,
        'previous_manifest': history[-1] if history else None,
    }


def main() -> None:
    legacy_cards = base._legacy_cards()
    exact, names = _legacy_index(legacy_cards)
    rows = admin_list_products()

    existing_cards = svc.list_cards()
    existing_by_slug = {str(x.get('slug') or '').strip().lower(): x for x in existing_cards}
    cmap = svc.commerce_map()
    cmap.setdefault('schema_version', '1.0')
    cmap.setdefault('products', [])
    mapped_product_keys = {str(x.get('existing_product_key') or '').strip(): x for x in cmap['products'] if isinstance(x, dict)}
    mapped_product_ids = {str(x.get('product_id') or '').strip() for x in cmap['products'] if isinstance(x, dict)}

    created: list[dict] = []
    skipped_existing: list[dict] = []
    excluded: list[str] = []
    failures: list[str] = []

    for row in rows:
        pid = str(row.get('id') or '').strip()
        detail = catalog_detail(pid) if pid else None
        if not isinstance(detail, dict):
            failures.append(f'{pid or "?"}: catalog detail missing')
            continue
        if not _eligible(row, detail):
            excluded.append(pid)
            continue

        slug = str(row.get('slug') or detail.get('slug') or pid).strip().lower()
        if pid in mapped_product_keys or slug in existing_by_slug:
            card_row = existing_by_slug.get(slug)
            skipped_existing.append({'catalog_id': pid, 'slug': slug, 'product_id': (card_row or {}).get('product_id') or mapped_product_keys.get(pid, {}).get('product_id')})
            continue

        try:
            legacy, source_kind = _choose_legacy(pid, detail, exact, names)
            card, card_map, report = r3._build_r3(pid, legacy, row, detail)
            if card['product_id'] in mapped_product_ids:
                skipped_existing.append({'catalog_id': pid, 'slug': slug, 'product_id': card['product_id']})
                continue
            svc.create(card)
            cmap['products'].append(card_map)
            mapped_product_ids.add(card['product_id'])
            mapped_product_keys.add(pid)
            existing_by_slug[slug] = {'slug': slug, 'product_id': card['product_id']}
            report['catalog_id'] = pid
            report['source_kind'] = source_kind
            report['status'] = 'GENERATED'
            created.append(report)
        except Exception as exc:
            failures.append(f'{pid}: {exc}')

    _save_commerce_map(cmap)

    batches: list[dict] = []
    for i in range(0, len(created), BATCH_SIZE):
        items = created[i:i + BATCH_SIZE]
        batches.append({
            'batch': f'CATALOG-{2 + i // BATCH_SIZE:02d}',
            'status': 'GENERATED_TECHNICAL_VERIFY_REQUIRED',
            'count': len(items),
            'products': [
                {
                    'catalog_id': x.get('catalog_id'),
                    'name': x.get('name'),
                    'product_id': x.get('product_id'),
                    'slug': x.get('slug'),
                    'sku_count': x.get('sku_count'),
                    'commerce_binding_status': x.get('commerce_binding_status'),
                    'source_kind': x.get('source_kind'),
                }
                for x in items
            ],
        })

    previous_manifest = base._load(svc.MIGRATION_MANIFEST, {})
    totals = {
        'eligible_catalog_products': len(created) + len(skipped_existing),
        'created_now': len(created),
        'already_v3': len(skipped_existing),
        'excluded_internal': len(excluded),
        'failures': len(failures),
        'v3_total_after_run': len(svc.list_cards()),
    }
    base._save(svc.MIGRATION_MANIFEST, _manifest(previous_manifest, batches, totals))

    print('PCV3 ALL-REMAINING MIGRATION')
    print(f'CREATED={len(created)} ALREADY_V3={len(skipped_existing)} EXCLUDED={len(excluded)} FAILURES={len(failures)}')
    for batch in batches:
        print(f"{batch['batch']}: {batch['count']}")
        for item in batch['products']:
            print(f"  GENERATED {item['catalog_id']} | SKU={item['sku_count']} | {item['commerce_binding_status']} | {item['source_kind']}")
    for item in skipped_existing:
        print(f"  EXISTING {item['catalog_id']} | {item['slug']}")
    for pid in excluded:
        print(f'  EXCLUDED {pid}')
    if failures:
        print('FAILURES:')
        for line in failures:
            print('  ' + line)
        raise SystemExit(2)
    print('PCV3 ALL-REMAINING GENERATED PASS')
    print('No commerce write API was called by this tool.')


if __name__ == '__main__':
    main()
