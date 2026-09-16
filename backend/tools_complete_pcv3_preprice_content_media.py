from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import find_master_for_card, source_metadata
from backend.services.product_cards_v3_media import _is_resolvable, list_existing_media
from backend.services.product_cards_v3_preprice import preprice_report
from backend.tools_complete_pcv3_media_readiness import _pack_key
from backend.tools_prepare_pcv3_release import _snapshot_tables

ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = ROOT / 'var' / 'release-backups'
REPORT_ROOT = ROOT / 'var' / 'reports'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _text(value: Any) -> str:
    return str(value or '').strip()


def _norm(value: Any) -> str:
    s = _text(value).lower().replace('ё', 'е').replace('₂', '2').replace('₅', '5').replace('₃', '3')
    s = re.sub(r'[^0-9a-zа-яіїєґ]+', ' ', s, flags=re.I)
    return ' '.join(s.split())


def _master_specs(master: dict) -> list[dict]:
    src = master.get('specs') or master.get('characteristics') or []
    if isinstance(src, dict):
        src = src.get('rows') or []
    return [x for x in src if isinstance(x, dict)] if isinstance(src, list) else []


def _composition_from_master(master: dict) -> tuple[str, str]:
    direct = _text(master.get('composition'))
    if direct:
        return direct, 'master-composition'

    include = (
        'формула', 'npk', 'азот', 'nitrogen', 'фосфор', 'phosph', 'калій', 'potassium',
        'p2o5', 'k2o', 'mgo', 'cao', 'so3', 'n ', 'бор', 'boron', ' b', 'заліз', 'iron',
        'fe', 'марган', 'mangan', 'mn', 'цинк', 'zinc', 'zn', 'мід', 'copper', 'cu',
        'моліб', 'molyb', 'mo', 'амін', 'amino', 'гумін', 'humic', 'фульв', 'fulvic',
        'кислот', 'acid', 'карбогідрат', 'цукр', 'sugar', 'органічний вуглець', 'organic carbon',
        'екстракт', 'extract', 'водорост', 'seaweed', 'algae', 'бетаїн', 'betaine',
        'полісахарид', 'polysaccharide', 'вітамін', 'vitamin', 'активн', 'active ingredient',
        'діюча речовина', 'склад', 'хелат', 'chelat', 'комплексоутвор', 'complexing',
        'ключова фракція', 'фракція', 'органічна речовина', 'organic matter', 'протеїн', 'protein'
    )
    exclude = (
        'тип продукту', 'форма', 'препаративна форма', 'бренд', 'компанія', 'виробник',
        'країна', 'колір', 'розчинність', 'густина', 'density', 'ph ', 'ph(', 'ph 1%',
        'призначення', 'застосування', 'application', 'сумісність', 'compatibility'
    )
    parts: list[str] = []
    for item in _master_specs(master):
        label = _text(item.get('label') or item.get('name') or item.get('title'))
        value = _text(item.get('value') or item.get('text') or item.get('description'))
        if not label or not value:
            continue
        low = ' ' + _norm(label) + ' '
        if any(token in low for token in exclude):
            continue
        value_low = _norm(value)
        is_quantified = bool(re.search(r'\d+(?:[.,]\d+)?\s*(?:%|г/л|g/l|мг/л|mg/l|ppm)', value, flags=re.I))
        is_composition_label = any(token in low for token in include)
        if is_composition_label or is_quantified:
            part = f'{label}: {value}'
            if part not in parts:
                parts.append(part)
    if parts:
        return '; '.join(parts), 'master-specs'

    # Some approved MASTER rows state the formulation only in the verified description.
    # Extract only sentences that contain an explicit composition cue; never invent values.
    prose = ' '.join(
        x for x in (
            _text(master.get('short_description')),
            _text(master.get('full_description')),
            _text(master.get('lead')),
        ) if x
    )
    cues = ('%', 'склад', 'містить', 'вміст', 'амінокислот', 'гумінов', 'фульвов', 'npk', 'k2o', 'p2o5', 'mgo', 'zn', 'fe', 'бор')
    chosen: list[str] = []
    for sentence in re.split(r'(?<=[.!?])\s+', prose):
        low = sentence.lower()
        if len(sentence) >= 20 and any(cue in low for cue in cues):
            clean = sentence.strip()
            if clean and clean not in chosen:
                chosen.append(clean)
        if len(chosen) >= 2:
            break
    if chosen:
        return ' '.join(chosen), 'master-verified-prose'

    return (
        'Точний кількісний склад не наведено у підтвердженій MASTER-картці. '
        'Перед застосуванням звірити актуальну етикетку конкретної фасовки.',
        'master-transparent-disclosure',
    )


def _seo_complete(content: dict) -> bool:
    seo = content.get('seo') or {}
    return bool(_text(seo.get('title'))) and len(_text(seo.get('description'))) >= 50


def _complete_seo(content: dict) -> bool:
    if _seo_complete(content):
        return False
    title = _text(content.get('title'))
    short = _text(content.get('short_description'))
    desc = _text(content.get('description'))
    source = short if len(short) >= 50 else desc
    seo = deepcopy(content.get('seo') or {})
    if not _text(seo.get('title')):
        seo['title'] = f'{title} | BB610 Market' if title else 'BB610 Market'
    if len(_text(seo.get('description'))) < 50:
        text = source.strip()
        if len(text) > 300:
            text = text[:297].rstrip() + '…'
        seo['description'] = text
    content['seo'] = {'title': _text(seo.get('title')), 'description': _text(seo.get('description'))}
    return True


def _media_by_id(card: dict) -> dict[str, dict]:
    return {
        _text(m.get('media_id')): m
        for m in (card.get('sku_media') or {}).get('media') or []
        if isinstance(m, dict) and m.get('media_id')
    }


def _valid_media_rows(card: dict) -> list[dict]:
    out = []
    seen = set()
    for m in (card.get('sku_media') or {}).get('media') or []:
        if not isinstance(m, dict):
            continue
        path = _text(m.get('path'))
        if not path or path in seen or not _is_resolvable(path):
            continue
        seen.add(path)
        out.append(m)
    return out


def _fill_media_alt(card: dict) -> int:
    title = _text((card.get('content') or {}).get('title'))
    media = _media_by_id(card)
    package_by_mid: dict[str, str] = {}
    for sku in (card.get('sku_media') or {}).get('skus') or []:
        if not isinstance(sku, dict):
            continue
        mid = _text(sku.get('primary_media_id'))
        pack = _text(sku.get('package') or sku.get('label'))
        if mid and pack and mid not in package_by_mid:
            package_by_mid[mid] = pack
    changed = 0
    for mid, row in media.items():
        if _text(row.get('alt')):
            continue
        pack = package_by_mid.get(mid, '')
        row['alt'] = ' — '.join(x for x in (title, pack) if x) or title or 'BB610 Market product image'
        changed += 1
    return changed


def _aliases(card: dict) -> list[str]:
    content = card.get('content') or {}
    title = _text(content.get('title'))
    slug = _text(card.get('slug')).replace('-', ' ')
    raw = [title, slug]
    if '/' in title:
        raw.extend(x.strip() for x in title.split('/') if x.strip())
    if '(' in title:
        raw.append(title.split('(', 1)[0].strip())
    out = []
    for value in raw:
        n = _norm(value)
        if len(n.replace(' ', '')) >= 5 and n not in out:
            out.append(n)
    return out


def _media_hay(item: dict) -> str:
    return _norm(' '.join(_text(item.get(k)) for k in ('title', 'name', 'path')))


def _library_candidates(card: dict, library: list[dict]) -> list[dict]:
    aliases = _aliases(card)
    matches = []
    for item in library:
        path = _text(item.get('path'))
        if not path or not _is_resolvable(path):
            continue
        hay = _media_hay(item)
        if any(alias in hay for alias in aliases):
            matches.append(item)
    unique = {}
    for item in matches:
        unique[_text(item.get('path'))] = item
    return list(unique.values())


def _new_media_id(path: str, used: set[str]) -> str:
    base = 'med_preprice_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:18]
    value = base
    n = 2
    while value in used:
        value = f'{base}_{n}'
        n += 1
    return value


def _ensure_media_row(card: dict, path: str, alt: str) -> str:
    sm = card.setdefault('sku_media', {})
    media = sm.setdefault('media', [])
    for row in media:
        if isinstance(row, dict) and _text(row.get('path')) == path and row.get('media_id'):
            if not _text(row.get('alt')):
                row['alt'] = alt
            return _text(row.get('media_id'))
    used = {_text(x.get('media_id')) for x in media if isinstance(x, dict)}
    mid = _new_media_id(path, used)
    media.append({'media_id': mid, 'path': path, 'alt': alt, 'kind': 'product', 'sort_order': len(media)})
    return mid


def _fill_missing_primary(card: dict, library: list[dict]) -> tuple[int, str]:
    sm = card.get('sku_media') or {}
    skus = [s for s in (sm.get('skus') or []) if isinstance(s, dict) and s.get('enabled') is not False]
    media_by_id = _media_by_id(card)
    missing = [s for s in skus if not (s.get('primary_media_id') in media_by_id and _is_resolvable(_text(media_by_id[s.get('primary_media_id')].get('path'))))]
    if not missing:
        return 0, 'none'

    title = _text((card.get('content') or {}).get('title'))
    valid_rows = _valid_media_rows(card)
    used_primary = []
    for sku in skus:
        mid = _text(sku.get('primary_media_id'))
        row = media_by_id.get(mid)
        if row and _is_resolvable(_text(row.get('path'))):
            used_primary.append(row)
    primary_paths = {_text(x.get('path')): x for x in used_primary}

    # Safest fallback: all already-correct SKU primaries use one product image.
    chosen = None
    method = ''
    if len(primary_paths) == 1:
        chosen = next(iter(primary_paths.values()))
        method = 'same-card-single-primary'
    elif len(valid_rows) == 1:
        chosen = valid_rows[0]
        method = 'same-card-single-media'

    if chosen:
        count = 0
        mid = _text(chosen.get('media_id'))
        for sku in missing:
            sku['primary_media_id'] = mid
            count += 1
        return count, method

    candidates = _library_candidates(card, library)
    if len(candidates) == 1:
        path = _text(candidates[0].get('path'))
        mid = _ensure_media_row(card, path, title)
        for sku in missing:
            sku['primary_media_id'] = mid
        return len(missing), 'library-exact-product-singleton'

    if len(candidates) > 1:
        filled = 0
        for sku in missing:
            pack = _pack_key(sku.get('package') or sku.get('label') or '')
            if not pack:
                continue
            hits = [x for x in candidates if pack in re.sub(r'[^0-9a-z]+', '', _text(x.get('path')).lower())]
            if len(hits) != 1:
                continue
            path = _text(hits[0].get('path'))
            alt = ' — '.join(x for x in (title, _text(sku.get('package') or sku.get('label'))) if x)
            mid = _ensure_media_row(card, path, alt)
            sku['primary_media_id'] = mid
            filled += 1
        if filled:
            return filled, 'library-exact-product+pack'

    return 0, 'ambiguous-or-missing'


def run(apply: bool) -> dict:
    stamp = _stamp()
    before_db = _snapshot_tables()
    cmap_before = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b''
    backup = ''
    if apply:
        dest = BACKUP_ROOT / f'pcv3-preprice-content-media-{stamp}'
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(cards.BASE, dest / 'product_cards_v3')
        backup = str(dest)

    library = list_existing_media().get('items') or []
    composition_changed = seo_changed = alt_changed = photo_changed = cards_changed = 0
    composition_methods: dict[str, int] = {}
    photo_methods: dict[str, int] = {}

    for summary in cards.list_cards():
        pid = _text(summary.get('product_id'))
        card = cards.get(pid)
        if not isinstance(card, dict):
            continue
        master = find_master_for_card(card)
        meta = source_metadata(master)
        if not master or not meta.get('verified'):
            continue
        work = deepcopy(card)
        content = work.setdefault('content', {})
        changed = False

        if len(_text(content.get('composition'))) < 10:
            value, method = _composition_from_master(master)
            if value:
                content['composition'] = value
                composition_changed += 1
                composition_methods[method] = composition_methods.get(method, 0) + 1
                changed = True

        if _complete_seo(content):
            seo_changed += 1
            changed = True

        n_alt = _fill_media_alt(work)
        if n_alt:
            alt_changed += n_alt
            changed = True

        n_photo, photo_method = _fill_missing_primary(work, library)
        if n_photo:
            photo_changed += n_photo
            photo_methods[photo_method] = photo_methods.get(photo_method, 0) + n_photo
            changed = True

        if changed:
            cards.validate(work)
            if apply:
                cards.put(pid, work)
            cards_changed += 1

    after_db = _snapshot_tables()
    cmap_after = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b''
    if before_db != after_db:
        raise RuntimeError('commerce/database changed during preprice content/media completion')
    if cmap_before != cmap_after:
        raise RuntimeError('commerce_map.json changed during preprice content/media completion')

    report = preprice_report() if apply else None
    result = {
        'schema_version': '1.0',
        'mode': 'APPLY_SAFE' if apply else 'DRY_RUN',
        'cards_changed': cards_changed,
        'composition_changed': composition_changed,
        'composition_methods': composition_methods,
        'seo_changed': seo_changed,
        'media_alt_changed': alt_changed,
        'primary_photo_changed': photo_changed,
        'photo_methods': photo_methods,
        'commerce_db_unchanged': before_db == after_db,
        'commerce_map_unchanged': cmap_before == cmap_after,
        'backup_dir': backup,
        'preprice_summary_after': (report or {}).get('summary'),
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f'pcv3-preprice-content-media-{stamp}.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['report_path'] = str(path)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description='Complete non-price PCV3 content and only high-confidence local media.')
    ap.add_argument('--apply-safe', action='store_true')
    args = ap.parse_args()
    result = run(args.apply_safe)
    print('BB610 PCV3 PREPRICE CONTENT + SAFE LOCAL MEDIA')
    print('MODE:', result['mode'])
    print('CARDS CHANGED:', result['cards_changed'])
    print('COMPOSITION CHANGED:', result['composition_changed'], result['composition_methods'])
    print('SEO CHANGED:', result['seo_changed'])
    print('MEDIA ALT CHANGED:', result['media_alt_changed'])
    print('PRIMARY PHOTO CHANGED:', result['primary_photo_changed'], result['photo_methods'])
    print('COMMERCE DB UNCHANGED:', 'PASS' if result['commerce_db_unchanged'] else 'FAIL')
    print('COMMERCE MAP UNCHANGED:', 'PASS' if result['commerce_map_unchanged'] else 'FAIL')
    if result['preprice_summary_after']:
        s = result['preprice_summary_after']
        print('PREPRICE CARDS:', f"{s.get('cards_preprice_ready')}/{s.get('cards_total')}")
        print('PREPRICE SKU:', f"{s.get('skus_preprice_ready')}/{s.get('skus_total')}")
        print('PREPRICE ISSUES:', s.get('issue_counts'))
        print('PREPRICE COMPLETE:', 'PASS' if s.get('complete') else 'PENDING')
    print('BACKUP:', result['backup_dir'])
    print('REPORT:', result['report_path'])
    print('RESULT: PASS')


if __name__ == '__main__':
    main()
