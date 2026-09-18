from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
CONTENT_BATCH_DIR = ROOT / 'data' / 'content_batches'
MASTER_GLOB = 'stage22c_batch*.json'
ORGANIC_SOURCE = ROOT / 'data' / 'catalog_sources' / 'organic_planet_full_price_v1.json'


def _text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return '\n'.join(x for x in (_text(v) for v in value) if x)
    if isinstance(value, dict):
        for key in ('text', 'body', 'description', 'intro', 'note', 'value'):
            text = _text(value.get(key))
            if text:
                return text
    return ''


def normalize_name(value: Any) -> str:
    s = str(value or '').upper().replace('™', '').replace('®', '')
    s = s.replace('₂', '2').replace('₅', '5').replace('₃', '3')
    s = re.sub(r'[^A-Z0-9А-ЯІЇЄҐ+.-]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _loose_name(value: Any) -> str:
    s = normalize_name(value)
    s = re.sub(r'[+.-]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def identity_variants(value: Any) -> tuple[str, ...]:
    """Deterministic product identity variants.

    Only descriptive suffixes are removed. No fuzzy similarity is used.
    Ambiguity is resolved later by requiring a single MASTER candidate.
    """
    raw = str(value or '').strip()
    if not raw:
        return tuple()

    candidates = [raw]
    for sep in (' — ', ' – ', ','):
        if sep in raw:
            head = raw.split(sep, 1)[0].strip()
            if len(head) >= 3:
                candidates.append(head)

    # Common storefront form: "Kendal Root (Кендал Рут), опис...".
    if ' (' in raw:
        head = raw.split(' (', 1)[0].strip()
        if len(head) >= 3:
            candidates.append(head)

    # Also remove only a trailing parenthetical alias from already-short names.
    for item in list(candidates):
        stripped = re.sub(r'\\s*\\([^()]{2,80}\\)\\s*$', '', item).strip()
        if stripped and stripped != item:
            candidates.append(stripped)

    out: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        for key in (normalize_name(item), _loose_name(item)):
            if key and key not in seen:
                seen.add(key)
                out.append(key)
    return tuple(out)

def _load(path: Path) -> list[dict]:
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []
    return [x for x in obj if isinstance(x, dict)] if isinstance(obj, list) else []


@lru_cache(maxsize=1)
def master_rows() -> tuple[dict, ...]:
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(CONTENT_BATCH_DIR.glob(MASTER_GLOB)):
        for row in _load(path):
            name = _text(row.get('name'))
            key = (normalize_name(name), str(row.get('source_row') or ''))
            if not name or key in seen:
                continue
            seen.add(key)
            item = deepcopy(row)
            item['_master_file'] = path.name
            out.append(item)
    return tuple(out)


@lru_cache(maxsize=1)
def master_index() -> dict[str, tuple[dict, ...]]:
    grouped: dict[str, list[dict]] = {}
    for row in master_rows():
        for key in identity_variants(row.get('name')):
            grouped.setdefault(key, []).append(row)
    return {
        key: tuple(rows)
        for key, rows in grouped.items()
    }


@lru_cache(maxsize=1)
def master_source_row_index() -> dict[int, dict]:
    grouped: dict[int, list[dict]] = {}
    for row in master_rows():
        try:
            source_row = int(row.get('source_row'))
        except Exception:
            continue
        grouped.setdefault(source_row, []).append(row)
    return {source_row: rows[0] for source_row, rows in grouped.items() if len(rows) == 1}


@lru_cache(maxsize=1)
def organic_products() -> tuple[dict, ...]:
    try:
        obj = json.loads(ORGANIC_SOURCE.read_text(encoding='utf-8'))
    except Exception:
        return tuple()
    rows = obj.get('products') if isinstance(obj, dict) else None
    if not isinstance(rows, list):
        return tuple()
    out: list[dict] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        item = deepcopy(row)
        # The approved stage22c MASTER was built from the same ordered source matrix.
        # This row bridge is deterministic and avoids fuzzy product matching.
        item['_source_row'] = i
        out.append(item)
    return tuple(out)


@lru_cache(maxsize=1)
def organic_identity_index() -> dict[str, tuple[dict, ...]]:
    grouped: dict[str, list[dict]] = {}
    for row in organic_products():
        values: list[Any] = [row.get('title'), row.get('slug')]
        aliases = row.get('aliases')
        if isinstance(aliases, list):
            values.extend(aliases)
        for value in values:
            for key in identity_variants(value):
                grouped.setdefault(key, []).append(row)
    return {key: tuple(rows) for key, rows in grouped.items()}


def _annotated(row: dict, method: str, organic_title: str = '') -> dict:
    item = deepcopy(row)
    item['_match_method'] = method
    if organic_title:
        item['_organic_title'] = organic_title
    return item


def find_master_for_card(card: dict) -> Optional[dict]:
    content = card.get('content') or {}
    keys: list[str] = []
    seen_keys: set[str] = set()
    for value in (content.get('title'), card.get('slug')):
        for key in identity_variants(value):
            if key not in seen_keys:
                seen_keys.add(key)
                keys.append(key)

    direct_matches: list[dict] = []
    idx = master_index()
    for key in keys:
        if not key:
            continue
        for row in idx.get(key) or ():
            if row not in direct_matches:
                direct_matches.append(row)
    if len(direct_matches) == 1:
        return _annotated(direct_matches[0], 'direct_master_identity')

    # Imported Organic Planet cards can use a retail title/slug that differs from the
    # editorial MASTER title. Bridge through the shared source-row identity rather
    # than fuzzy text matching. Ambiguous retail aliases are refused.
    organic_matches: list[dict] = []
    organic_idx = organic_identity_index()
    for key in keys:
        if not key:
            continue
        for row in organic_idx.get(key) or ():
            if row not in organic_matches:
                organic_matches.append(row)
    if len(organic_matches) != 1:
        return None
    organic = organic_matches[0]
    try:
        source_row = int(organic.get('_source_row'))
    except Exception:
        return None
    master = master_source_row_index().get(source_row)
    if not master:
        return None
    return _annotated(master, 'organic_source_row', _text(organic.get('title')))


def source_metadata(row: Optional[dict]) -> dict:
    if not isinstance(row, dict):
        return {
            'matched': False,
            'verified': False,
            'verified_date': '',
            'source_count': 0,
            'master_file': '',
            'source_row': None,
            'match_method': '',
            'organic_title': '',
            'urls': [],
        }

    urls: list[str] = []
    origin = row.get('origin') if isinstance(row.get('origin'), dict) else {}
    sources = row.get('sources') if isinstance(row.get('sources'), dict) else {}
    documents = row.get('documents') if isinstance(row.get('documents'), list) else []
    for value in (origin.get('official_url'), sources.get('source_url'), sources.get('source_pdf')):
        url = _text(value)
        if url and url not in urls:
            urls.append(url)
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        url = _text(doc.get('url'))
        if url and url not in urls:
            urls.append(url)

    verified_date = _text(sources.get('verified_date'))
    revision = _text(sources.get('revision'))
    verified = bool(urls and (verified_date or 'ПЕРЕВІРЕНО' in revision.upper()))
    return {
        'matched': True,
        'verified': verified,
        'verified_date': verified_date,
        'revision': revision,
        'source_count': len(urls),
        'master_file': _text(row.get('_master_file')),
        'source_row': row.get('source_row'),
        'match_method': _text(row.get('_match_method')),
        'organic_title': _text(row.get('_organic_title')),
        'urls': urls,
    }


def _benefits(row: dict) -> list[dict]:
    src = row.get('why') or row.get('benefits') or []
    out: list[dict] = []
    if isinstance(src, list):
        for item in src:
            if isinstance(item, dict):
                title = _text(item.get('title'))
                text = _text(item.get('text') or item.get('body') or item.get('description'))
                if title or text:
                    out.append({'title': title, 'text': text})
            else:
                text = _text(item)
                if text:
                    out.append({'title': '', 'text': text})
    elif isinstance(src, dict):
        text = _text(src)
        if text:
            out.append({'title': _text(src.get('title')), 'text': text})
    return out


def _how(row: dict) -> str:
    value = row.get('how_it_works')
    if isinstance(value, dict):
        return _text(value.get('text') or value.get('body') or value.get('description'))
    return _text(value)


def _application(row: dict) -> str:
    value = row.get('application')
    if not isinstance(value, dict):
        return _text(value)
    chunks: list[str] = []
    intro = _text(value.get('intro') or value.get('text'))
    if intro:
        chunks.append(intro)
    rows = value.get('rows')
    if isinstance(rows, list):
        for item in rows:
            if isinstance(item, dict):
                subject = _text(item.get('label') or item.get('culture') or item.get('crop') or item.get('title'))
                period = _text(item.get('period') or item.get('stage') or item.get('timing'))
                dose = _text(item.get('value') or item.get('rate') or item.get('dose') or item.get('norm') or item.get('text'))
                head = ' — '.join(x for x in (subject, period) if x)
                line = f'{head}: {dose}' if head and dose else head or dose
                if line:
                    chunks.append(line)
            else:
                text = _text(item)
                if text:
                    chunks.append(text)
    note = _text(value.get('note') or value.get('market_note'))
    if note:
        chunks.append(note)
    return '\n'.join(chunks)


def _characteristics(row: dict) -> list[dict]:
    src = row.get('specs') or row.get('characteristics') or []
    out: list[dict] = []
    if isinstance(src, dict):
        src = src.get('rows') or []
    if not isinstance(src, list):
        return out
    for item in src:
        if not isinstance(item, dict):
            continue
        label = _text(item.get('label') or item.get('name') or item.get('title'))
        value = _text(item.get('value') or item.get('text') or item.get('description'))
        if label or value:
            out.append({'label': label, 'value': value})
    return out


def _composition(row: dict, characteristics: list[dict]) -> str:
    direct = _text(row.get('composition'))
    if direct:
        return direct
    wanted = (
        'формула', 'npk', 'азот', 'nitrogen', 'p2o5', 'p₂o₅', 'k2o', 'k₂o',
        'mgo', 'магній', 'magnesium', 'cao', 'кальцій', 'calcium', 'so3',
        'бор', 'boron', 'залізо', 'iron', 'марган', 'mangan', 'zinc', 'цинк',
        'мід', 'copper', 'моліб', 'molyb', 'активн', 'active ingredient', 'склад'
    )
    parts: list[str] = []
    for item in characteristics:
        label = _text(item.get('label'))
        value = _text(item.get('value'))
        low = label.lower()
        if label and value and any(token in low for token in wanted):
            parts.append(f'{label}: {value}')
    return '; '.join(parts)


def content_from_master(row: dict, current: Optional[dict] = None) -> dict:
    current = deepcopy(current or {})
    characteristics = _characteristics(row)
    benefits = _benefits(row)
    title = _text(row.get('name')) or _text(current.get('title'))
    short = _text(row.get('short_description') or row.get('lead') or row.get('subtitle'))
    description = _text(row.get('full_description') or row.get('description'))
    how = _how(row)
    application = _application(row)
    composition = _composition(row, characteristics)

    out = deepcopy(current)
    replacements = {
        'title': title,
        'brand': _text(row.get('brand')),
        'category': _text(row.get('category')),
        'short_description': short,
        'description': description,
        'how_it_works': how,
        'application': application,
        'composition': composition,
    }
    for key, value in replacements.items():
        if value:
            out[key] = value
    if benefits:
        out['benefits'] = benefits
    if characteristics:
        out['characteristics'] = characteristics

    seo = deepcopy(out.get('seo') or {'title': '', 'description': ''})
    if not _text(seo.get('title')) and title:
        seo['title'] = f'{title} | BB610 Market'
    if not _text(seo.get('description')) and short:
        seo['description'] = short[:320]
    out['seo'] = {'title': _text(seo.get('title')), 'description': _text(seo.get('description'))}
    return out
, '', item).strip()
        if stripped and stripped != item:
            candidates.append(stripped)

    out: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        for key in (normalize_name(item), _loose_name(item)):
            if key and key not in seen:
                seen.add(key)
                out.append(key)
    return tuple(out)


def _load(path: Path) -> list[dict]:
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []
    return [x for x in obj if isinstance(x, dict)] if isinstance(obj, list) else []


@lru_cache(maxsize=1)
def master_rows() -> tuple[dict, ...]:
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(CONTENT_BATCH_DIR.glob(MASTER_GLOB)):
        for row in _load(path):
            name = _text(row.get('name'))
            key = (normalize_name(name), str(row.get('source_row') or ''))
            if not name or key in seen:
                continue
            seen.add(key)
            item = deepcopy(row)
            item['_master_file'] = path.name
            out.append(item)
    return tuple(out)


@lru_cache(maxsize=1)
def master_index() -> dict[str, tuple[dict, ...]]:
    grouped: dict[str, list[dict]] = {}
    for row in master_rows():
        key = normalize_name(row.get('name'))
        if key:
            grouped.setdefault(key, []).append(row)
    return {key: tuple(rows) for key, rows in grouped.items()}


@lru_cache(maxsize=1)
def master_source_row_index() -> dict[int, dict]:
    grouped: dict[int, list[dict]] = {}
    for row in master_rows():
        try:
            source_row = int(row.get('source_row'))
        except Exception:
            continue
        grouped.setdefault(source_row, []).append(row)
    return {source_row: rows[0] for source_row, rows in grouped.items() if len(rows) == 1}


@lru_cache(maxsize=1)
def organic_products() -> tuple[dict, ...]:
    try:
        obj = json.loads(ORGANIC_SOURCE.read_text(encoding='utf-8'))
    except Exception:
        return tuple()
    rows = obj.get('products') if isinstance(obj, dict) else None
    if not isinstance(rows, list):
        return tuple()
    out: list[dict] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        item = deepcopy(row)
        # The approved stage22c MASTER was built from the same ordered source matrix.
        # This row bridge is deterministic and avoids fuzzy product matching.
        item['_source_row'] = i
        out.append(item)
    return tuple(out)


@lru_cache(maxsize=1)
def organic_identity_index() -> dict[str, tuple[dict, ...]]:
    grouped: dict[str, list[dict]] = {}
    for row in organic_products():
        values: list[Any] = [row.get('title'), row.get('slug')]
        aliases = row.get('aliases')
        if isinstance(aliases, list):
            values.extend(aliases)
        for value in values:
            key = normalize_name(value)
            if key:
                grouped.setdefault(key, []).append(row)
    return {key: tuple(rows) for key, rows in grouped.items()}


def _annotated(row: dict, method: str, organic_title: str = '') -> dict:
    item = deepcopy(row)
    item['_match_method'] = method
    if organic_title:
        item['_organic_title'] = organic_title
    return item


def find_master_for_card(card: dict) -> Optional[dict]:
    content = card.get('content') or {}
    keys = [normalize_name(content.get('title')), normalize_name(card.get('slug'))]

    direct_matches: list[dict] = []
    idx = master_index()
    for key in keys:
        if not key:
            continue
        for row in idx.get(key) or ():
            if row not in direct_matches:
                direct_matches.append(row)
    if len(direct_matches) == 1:
        return _annotated(direct_matches[0], 'direct_master_identity')

    # Imported Organic Planet cards can use a retail title/slug that differs from the
    # editorial MASTER title. Bridge through the shared source-row identity rather
    # than fuzzy text matching. Ambiguous retail aliases are refused.
    organic_matches: list[dict] = []
    organic_idx = organic_identity_index()
    for key in keys:
        if not key:
            continue
        for row in organic_idx.get(key) or ():
            if row not in organic_matches:
                organic_matches.append(row)
    if len(organic_matches) != 1:
        return None
    organic = organic_matches[0]
    try:
        source_row = int(organic.get('_source_row'))
    except Exception:
        return None
    master = master_source_row_index().get(source_row)
    if not master:
        return None
    return _annotated(master, 'organic_source_row', _text(organic.get('title')))


def source_metadata(row: Optional[dict]) -> dict:
    if not isinstance(row, dict):
        return {
            'matched': False,
            'verified': False,
            'verified_date': '',
            'source_count': 0,
            'master_file': '',
            'source_row': None,
            'match_method': '',
            'organic_title': '',
            'urls': [],
        }

    urls: list[str] = []
    origin = row.get('origin') if isinstance(row.get('origin'), dict) else {}
    sources = row.get('sources') if isinstance(row.get('sources'), dict) else {}
    documents = row.get('documents') if isinstance(row.get('documents'), list) else []
    for value in (origin.get('official_url'), sources.get('source_url'), sources.get('source_pdf')):
        url = _text(value)
        if url and url not in urls:
            urls.append(url)
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        url = _text(doc.get('url'))
        if url and url not in urls:
            urls.append(url)

    verified_date = _text(sources.get('verified_date'))
    revision = _text(sources.get('revision'))
    verified = bool(urls and (verified_date or 'ПЕРЕВІРЕНО' in revision.upper()))
    return {
        'matched': True,
        'verified': verified,
        'verified_date': verified_date,
        'revision': revision,
        'source_count': len(urls),
        'master_file': _text(row.get('_master_file')),
        'source_row': row.get('source_row'),
        'match_method': _text(row.get('_match_method')),
        'organic_title': _text(row.get('_organic_title')),
        'urls': urls,
    }


def _benefits(row: dict) -> list[dict]:
    src = row.get('why') or row.get('benefits') or []
    out: list[dict] = []
    if isinstance(src, list):
        for item in src:
            if isinstance(item, dict):
                title = _text(item.get('title'))
                text = _text(item.get('text') or item.get('body') or item.get('description'))
                if title or text:
                    out.append({'title': title, 'text': text})
            else:
                text = _text(item)
                if text:
                    out.append({'title': '', 'text': text})
    elif isinstance(src, dict):
        text = _text(src)
        if text:
            out.append({'title': _text(src.get('title')), 'text': text})
    return out


def _how(row: dict) -> str:
    value = row.get('how_it_works')
    if isinstance(value, dict):
        return _text(value.get('text') or value.get('body') or value.get('description'))
    return _text(value)


def _application(row: dict) -> str:
    value = row.get('application')
    if not isinstance(value, dict):
        return _text(value)
    chunks: list[str] = []
    intro = _text(value.get('intro') or value.get('text'))
    if intro:
        chunks.append(intro)
    rows = value.get('rows')
    if isinstance(rows, list):
        for item in rows:
            if isinstance(item, dict):
                subject = _text(item.get('label') or item.get('culture') or item.get('crop') or item.get('title'))
                period = _text(item.get('period') or item.get('stage') or item.get('timing'))
                dose = _text(item.get('value') or item.get('rate') or item.get('dose') or item.get('norm') or item.get('text'))
                head = ' — '.join(x for x in (subject, period) if x)
                line = f'{head}: {dose}' if head and dose else head or dose
                if line:
                    chunks.append(line)
            else:
                text = _text(item)
                if text:
                    chunks.append(text)
    note = _text(value.get('note') or value.get('market_note'))
    if note:
        chunks.append(note)
    return '\n'.join(chunks)


def _characteristics(row: dict) -> list[dict]:
    src = row.get('specs') or row.get('characteristics') or []
    out: list[dict] = []
    if isinstance(src, dict):
        src = src.get('rows') or []
    if not isinstance(src, list):
        return out
    for item in src:
        if not isinstance(item, dict):
            continue
        label = _text(item.get('label') or item.get('name') or item.get('title'))
        value = _text(item.get('value') or item.get('text') or item.get('description'))
        if label or value:
            out.append({'label': label, 'value': value})
    return out


def _composition(row: dict, characteristics: list[dict]) -> str:
    direct = _text(row.get('composition'))
    if direct:
        return direct
    wanted = (
        'формула', 'npk', 'азот', 'nitrogen', 'p2o5', 'p₂o₅', 'k2o', 'k₂o',
        'mgo', 'магній', 'magnesium', 'cao', 'кальцій', 'calcium', 'so3',
        'бор', 'boron', 'залізо', 'iron', 'марган', 'mangan', 'zinc', 'цинк',
        'мід', 'copper', 'моліб', 'molyb', 'активн', 'active ingredient', 'склад'
    )
    parts: list[str] = []
    for item in characteristics:
        label = _text(item.get('label'))
        value = _text(item.get('value'))
        low = label.lower()
        if label and value and any(token in low for token in wanted):
            parts.append(f'{label}: {value}')
    return '; '.join(parts)


def content_from_master(row: dict, current: Optional[dict] = None) -> dict:
    current = deepcopy(current or {})
    characteristics = _characteristics(row)
    benefits = _benefits(row)
    title = _text(row.get('name')) or _text(current.get('title'))
    short = _text(row.get('short_description') or row.get('lead') or row.get('subtitle'))
    description = _text(row.get('full_description') or row.get('description'))
    how = _how(row)
    application = _application(row)
    composition = _composition(row, characteristics)

    out = deepcopy(current)
    replacements = {
        'title': title,
        'brand': _text(row.get('brand')),
        'category': _text(row.get('category')),
        'short_description': short,
        'description': description,
        'how_it_works': how,
        'application': application,
        'composition': composition,
    }
    for key, value in replacements.items():
        if value:
            out[key] = value
    if benefits:
        out['benefits'] = benefits
    if characteristics:
        out['characteristics'] = characteristics

    seo = deepcopy(out.get('seo') or {'title': '', 'description': ''})
    if not _text(seo.get('title')) and title:
        seo['title'] = f'{title} | BB610 Market'
    if not _text(seo.get('description')) and short:
        seo['description'] = short[:320]
    out['seo'] = {'title': _text(seo.get('title')), 'description': _text(seo.get('description'))}
    return out
