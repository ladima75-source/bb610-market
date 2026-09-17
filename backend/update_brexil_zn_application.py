from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

SLUG = 'brexil-zn'
SOURCE_URL = 'https://www.syngenta.ua/product/crop-protection/mikroelementy/breksiltm-zn'

SHORT_DESCRIPTION = (
    'Спеціалізоване мікродобриво з 10% цинку у комплексі з LSA для '
    'позакореневого живлення культур, чутливих до дефіциту цинку.'
)

DESCRIPTION = '''Brexil Zn — спеціалізоване мікродобриво з високим вмістом цинку для профілактики та корекції його дефіциту. За даними Syngenta Україна, препарат містить 10% Zn у комплексі з LSA та призначений насамперед для позакореневого живлення.

Комплексоутворювач LSA (лігносульфонат амонію) природного походження сприяє проникненню мікроелемента через листкову поверхню та допомагає підвищити ефективність його засвоєння. Продукт орієнтований на кукурудзу, картоплю та садові культури, де нестача цинку може обмежувати ріст і якість урожаю.'''

BENEFITS = [
    {
        'title': '10% Zn у комплексі з LSA',
        'text': 'Висока концентрація цинку для цільової профілактики та корекції його дефіциту.',
    },
    {
        'title': 'Швидке листкове засвоєння',
        'text': 'LSA допомагає мікроелементу проходити через кутикулу та краще засвоюватися листком.',
    },
    {
        'title': 'Ефект ПАР',
        'text': 'Продукт зменшує поверхневий натяг робочого розчину та покращує змочування листкової поверхні.',
    },
    {
        'title': 'Підкислювальний ефект',
        'text': 'Допомагає знизити pH робочого розчину при використанні води з лужною реакцією.',
    },
    {
        'title': 'Без Na, Cl і важких металів',
        'text': 'За інформацією виробника, склад не містить натрію, хлору та важких металів.',
    },
]

HOW_IT_WORKS = '''Цинк у Brexil Zn комплексований природним носієм LSA — лігносульфонатом амонію. Така форма полегшує проходження поживної речовини через кутикулу листка та її поглинання клітинами.

LSA одночасно знижує поверхневий натяг робочого розчину, покращуючи змочування листкової поверхні, а також має підкислювальний ефект. Це особливо корисно при роботі з водою лужної реакції.'''

APPLICATION = '''Brexil Zn застосовують позакоренево для профілактики та усунення дефіциту цинку, а також для покращення якості продукції.

Кукурудза: обробка у фазі 3–9 справжніх листків. Норма витрати — 1–2,0 кг/га. Рекомендована кількість обробок — 1–2.

Картопля: обробка перед змиканням рослин у міжряддях та у фазі бутонізації. Норма витрати — 1–2,0 кг/га. Рекомендована кількість обробок — 1–2.

Садові культури: обробка у фазі відокремлення бутонів або одразу після збирання плодів. Норма витрати — 0,1 кг на 100 л робочого розчину. Рекомендована кількість обробок — 1.

Рекомендована витрата робочого розчину: 100–300 л/га для польових культур і 800–1200 л/га для садових культур.

Обприскування доцільно проводити профілактично. Не рекомендується працювати по вологій листовій поверхні або якщо протягом 1,5–2 годин очікуються опади. Обробку проводять у ранкові або вечірні години в безвітряну погоду. Оптимальна температура застосування — від +12 до +25 °C. Не застосовувати за температури вище +25 °C та за відносної вологості нижче 40%. Робочий розчин слід використати протягом 24 годин після приготування.

Препарат можна змішувати з іншими загальновживаними засобами захисту рослин на відповідній культурі, але перед баковим змішуванням у кожному конкретному випадку потрібно провести тест на сумісність.

''' + SOURCE_URL

COMPOSITION = '''Цинк (Zn): 10%
Комплексоутворювач: LSA (лігносульфонат амонію)
Не містить: Na, Cl та важких металів'''

SEO = {
    'title': 'Brexil Zn — цинк 10% у комплексі з LSA | BB610 Market',
    'description': (
        'Brexil Zn — мікродобриво з 10% Zn у комплексі з LSA. '
        'Офіційні норми застосування для кукурудзи, картоплі та садових культур.'
    ),
}

MASTER_FIELDS = {
    'short_description': SHORT_DESCRIPTION,
    'description': DESCRIPTION,
    'benefits': BENEFITS,
    'how_it_works': HOW_IT_WORKS,
    'application': APPLICATION,
    'composition': COMPOSITION,
    'seo': SEO,
}

MANAGED_CHARACTERISTICS = [
    {'label': 'Культури', 'value': 'Кукурудза; Картопля; Садові культури'},
    {'label': 'Призначення', 'value': 'Попередження й лікування дефіциту елементів живлення; покращення якості продукції'},
    {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове живлення'},
    {'label': 'Діюча речовина', 'value': 'Цинк (Zn) 10% у комплексі з LSA'},
    {'label': 'Хімічна група', 'value': 'Мікродобрива'},
    {'label': 'Препаративна форма', 'value': 'Водорозчинні гранули (ВГ)'},
    {'label': 'Клас токсичності', 'value': 'IV (класифікація ВООЗ)'},
    {'label': 'Реєстраційний номер', 'value': '13674, серія А 08553'},
    {'label': 'Реєстрант', 'value': 'ТОВ «Агрісол»'},
    {'label': 'Упаковка виробника', 'value': '5 кг'},
    {'label': 'Температура застосування', 'value': '+12…25 °C'},
]
MANAGED_LABELS = {row['label'].casefold() for row in MANAGED_CHARACTERISTICS}


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _products_dir() -> Path:
    return _root() / 'data' / 'product_cards_v3' / 'products'


def _load(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise SystemExit(f'Invalid Product Card JSON: {path}')
    return obj


def _find_card() -> tuple[Path, dict]:
    products = _products_dir()
    if not products.exists():
        raise SystemExit(f'Product Card v3 directory not found: {products}')
    matches: list[tuple[Path, dict]] = []
    for path in sorted(products.glob('prd_*.json')):
        try:
            card = _load(path)
        except Exception:
            continue
        if str(card.get('slug') or '').strip().lower() == SLUG:
            matches.append((path, card))
    if not matches:
        raise SystemExit(f'Product Card v3 with slug {SLUG!r} was not found in {products}')
    if len(matches) != 1:
        raise SystemExit(f'Expected exactly one {SLUG!r} card, found {len(matches)}')
    return matches[0]


def _backup(card: dict) -> Path:
    out_dir = _root() / 'var' / 'content_backups'
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = out_dir / f'{SLUG}-{stamp}.json'
    path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def _save_atomic(path: Path, card: dict) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(card, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def _merge_characteristics(existing) -> list[dict]:
    kept: list[dict] = []
    for row in existing if isinstance(existing, list) else []:
        if not isinstance(row, dict):
            continue
        label = str(row.get('label') or '').strip()
        if label.casefold() in MANAGED_LABELS or label.casefold() == 'npk':
            continue
        kept.append(deepcopy(row))
    return kept + deepcopy(MANAGED_CHARACTERISTICS)


def _without_managed_content(card: dict) -> dict:
    out = deepcopy(card)
    content = out.get('content')
    if isinstance(content, dict):
        for key in MASTER_FIELDS:
            content[key] = '__IGNORED__'
        content['characteristics'] = [
            row for row in (content.get('characteristics') or [])
            if isinstance(row, dict)
            and str(row.get('label') or '').strip().casefold() not in MANAGED_LABELS
            and str(row.get('label') or '').strip().casefold() != 'npk'
        ]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description='Finalize Brexil Zn as the BB610 Product Card v3 master reference.')
    parser.add_argument('--apply', action='store_true', help='Write the change. Without this flag only preview is printed.')
    args = parser.parse_args()

    path, current = _find_card()
    content = current.get('content')
    if not isinstance(content, dict):
        raise SystemExit('Invalid card: content must be an object')

    updated = deepcopy(current)
    for key, value in MASTER_FIELDS.items():
        updated['content'][key] = deepcopy(value)
    updated['content']['characteristics'] = _merge_characteristics(content.get('characteristics'))

    if _without_managed_content(current) != _without_managed_content(updated):
        raise SystemExit('SAFETY CHECK FAILED: fields outside the managed Brexil master content set would change')

    print(json.dumps({
        'product_id': updated.get('product_id'),
        'slug': updated.get('slug'),
        'title': (updated.get('content') or {}).get('title'),
        'file': str(path),
        'master_fields': list(MASTER_FIELDS),
        'source': SOURCE_URL,
        'apply': bool(args.apply),
        'description_characters': len(DESCRIPTION),
        'benefit_count': len(BENEFITS),
        'application_characters': len(APPLICATION),
        'composition': COMPOSITION,
        'managed_characteristics': MANAGED_CHARACTERISTICS,
    }, ensure_ascii=False, indent=2))

    if not args.apply:
        print('\nDRY RUN: no files changed. Re-run with --apply to write.')
        return 0

    backup = _backup(current)
    try:
        _save_atomic(path, updated)
        verify = _load(path)
        vcontent = verify.get('content') or {}
        for key, value in MASTER_FIELDS.items():
            if vcontent.get(key) != value:
                raise RuntimeError(f'{key} mismatch after write')
        got = {
            str(x.get('label') or ''): str(x.get('value') or '')
            for x in (vcontent.get('characteristics') or [])
            if isinstance(x, dict)
        }
        for row in MANAGED_CHARACTERISTICS:
            if got.get(row['label']) != row['value']:
                raise RuntimeError(f"characteristic mismatch: {row['label']}")
        if 'NPK' in got:
            raise RuntimeError('NPK placeholder must not be present in the finalized Brexil card')
        if _without_managed_content(verify) != _without_managed_content(current):
            raise RuntimeError('a field outside the managed Brexil master content set changed')
    except Exception as exc:
        _save_atomic(path, current)
        raise SystemExit(f'VERIFY FAILED: original card restored: {exc}')

    print(json.dumps({
        'status': 'APPLIED',
        'master': 'BB610 Product Card v1.0',
        'backup': str(backup),
        'product_id': updated.get('product_id'),
        'slug': updated.get('slug'),
        'sku_count': len(((updated.get('sku_media') or {}).get('skus') or [])),
        'commerce_changed': False,
        'media_changed': False,
        'sku_changed': False,
        'managed_content_changed': True,
        'other_content_changed': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
