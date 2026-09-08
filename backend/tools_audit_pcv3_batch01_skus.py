from __future__ import annotations

from backend import tools_migrate_pcv3_batch01 as m
from backend.tools_migrate_pcv3_batch01_r2 import _legacy_sku_rows


def _label(row: dict) -> str:
    return m._text(
        row.get('variant')
        or row.get('label')
        or row.get('name')
        or row.get('pack')
        or row.get('package')
        or row.get('volume_weight')
        or row.get('id')
        or row.get('sku')
    )


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or '').strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def main() -> None:
    cards = m._legacy_cards()
    print('PCV3 BATCH01 SKU SOURCE AUDIT')
    print('target | commerce_skus | legacy_rows | factory_packs')
    for target in m.TARGETS:
        legacy = m._find_legacy(cards, target)
        _catalog_row, catalog = m._find_catalog_product(target, legacy)
        commerce_rows = [x for x in (catalog.get('skus') or []) if isinstance(x, dict)]
        legacy_rows = _legacy_sku_rows(legacy)
        factory_packs = catalog.get('factory_packs') or legacy.get('factory_packs') or []
        if not isinstance(factory_packs, list):
            factory_packs = [factory_packs] if factory_packs else []

        commerce_labels = _uniq([_label(x) for x in commerce_rows])
        legacy_labels = _uniq([_label(x) for x in legacy_rows])
        packs = _uniq([m._text(x) for x in factory_packs])

        print(f'\n{target}')
        print(f'  commerce: {len(commerce_rows)} -> {commerce_labels}')
        print(f'  legacy:   {len(legacy_rows)} -> {legacy_labels}')
        print(f'  packs:    {len(packs)} -> {packs}')


if __name__ == '__main__':
    main()
