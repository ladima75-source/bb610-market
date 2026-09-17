from __future__ import annotations

import csv
import io
import json
from copy import deepcopy
from typing import Any

from . import product_cards_v3 as pcv3
from . import product_cards_v3_catalog_import as base
from .catalog_import_xlsx import write_xlsx

FILTER_FIELDS = {
    'filter_cultures': 'Культури',
    'filter_purposes': 'Призначення',
    'filter_application_methods': 'Спосіб застосування',
    'filter_npk': 'NPK',
    'filter_active_ingredient': 'Діюча речовина',
}
FILTER_HEADERS = list(FILTER_FIELDS)
HEADERS = [*base.HEADERS[:-len(base.COMMERCE_HEADERS)], *FILTER_HEADERS, *base.COMMERCE_HEADERS]
CLEAR_VALUES = {'__clear__', 'clear', 'null', 'none'}


def _txt(value: Any) -> str:
    return '' if value is None else str(value).strip()


def _norm(value: Any) -> str:
    return ' '.join(_txt(value).lower().replace('ё', 'е').split())


def _parse_characteristics(value: Any, fallback: list[dict] | None = None) -> list[dict]:
    raw = _txt(value)
    if not raw:
        return deepcopy(fallback or [])
    try:
        obj = json.loads(raw)
    except Exception as exc:
        raise ValueError(f'Некоректний characteristics_json: {exc}') from exc
    if not isinstance(obj, list):
        raise ValueError('characteristics_json має бути JSON-масивом')
    out: list[dict] = []
    for item in obj:
        if not isinstance(item, dict):
            raise ValueError('Кожна характеристика має бути об’єктом label/value')
        out.append({'label': _txt(item.get('label')), 'value': _txt(item.get('value'))})
    return out


def _current_characteristics(row: dict) -> list[dict]:
    pid = _txt(row.get('product_id'))
    if not pid:
        return []
    card = pcv3.get(pid)
    content = card.get('content') if isinstance(card, dict) else None
    chars = content.get('characteristics') if isinstance(content, dict) else None
    return deepcopy(chars) if isinstance(chars, list) else []


def _upsert(rows: list[dict], label: str, value: str) -> list[dict]:
    target = _norm(label)
    rows = [dict(x) for x in rows if isinstance(x, dict)]
    matches = [i for i, x in enumerate(rows) if _norm(x.get('label')) == target]
    if value.lower() in CLEAR_VALUES:
        return [x for i, x in enumerate(rows) if i not in matches]
    item = {'label': label, 'value': value}
    if matches:
        rows[matches[0]] = item
        for i in reversed(matches[1:]):
            rows.pop(i)
    else:
        rows.append(item)
    return rows


def enrich_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for source in rows:
        row = {str(k).strip(): v for k, v in source.items()}
        supplied = [(column, _txt(row.get(column))) for column in FILTER_HEADERS if _txt(row.get(column))]
        if supplied:
            chars = _parse_characteristics(row.get('characteristics_json'), _current_characteristics(row))
            for column, value in supplied:
                chars = _upsert(chars, FILTER_FIELDS[column], value)
            row['characteristics_json'] = json.dumps(chars, ensure_ascii=False, separators=(',', ':'))
        out.append(row)
    return out


def _characteristic_value(raw: Any, label: str) -> str:
    try:
        rows = json.loads(_txt(raw) or '[]')
    except Exception:
        return ''
    target = _norm(label)
    for item in rows if isinstance(rows, list) else []:
        if isinstance(item, dict) and _norm(item.get('label')) == target:
            return _txt(item.get('value'))
    return ''


def _csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=HEADERS, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, '') for key in HEADERS})
    return ('\ufeff' + buf.getvalue()).encode('utf-8')


def template_rows() -> list[dict]:
    rows = [dict(x) for x in base.template_rows()]
    examples = {
        'filter_cultures': 'лохина; полуниця; овочі',
        'filter_purposes': 'живлення; корекція дефіциту',
        'filter_application_methods': 'Листова / внекоренева',
        'filter_npk': '',
        'filter_active_ingredient': 'Цинк (Zn) 10%',
    }
    for row in rows:
        row.update(examples)
        # Demonstrates the detailed composition block while remaining editable
        # as ordinary spreadsheet text.
        if not _txt(row.get('composition')):
            row['composition'] = 'Діюча речовина: Цинк (Zn) 10%; Комплексоутворювач: LSA; pH 1% розчину: 3,5; Розчинність: повна'
    return rows


def template_csv() -> bytes:
    return _csv_bytes(template_rows())


def template_xlsx() -> bytes:
    return write_xlsx(template_rows(), HEADERS)


def export_rows() -> list[dict]:
    out: list[dict] = []
    for source in base.export_rows():
        row = dict(source)
        raw = row.get('characteristics_json')
        for column, label in FILTER_FIELDS.items():
            row[column] = _characteristic_value(raw, label)
        out.append(row)
    return out


def export_csv() -> bytes:
    return _csv_bytes(export_rows())


def export_xlsx() -> bytes:
    return write_xlsx(export_rows(), HEADERS)


def preview(filename: str, raw: bytes) -> dict:
    rows = enrich_rows(base.parse_upload(filename, raw))
    # The base importer consumes its established schema; filter convenience
    # columns have already been converted to characteristics_json above.
    normalized = base._csv_bytes(rows)
    return base.preview('product-catalog-v3-filtered.csv', normalized)


def apply(token: str) -> dict:
    return base.apply(token)


def history() -> list[dict]:
    return base.history()


def rollback(backup_id: str) -> dict:
    return base.rollback(backup_id)
