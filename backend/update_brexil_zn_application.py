from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

SLUG = 'brexil-zn'
SOURCE_URL = 'https://www.syngenta.ua/product/crop-protection/mikroelementy/breksiltm-zn'
APPLICATION = '''Брексіл Zn застосовують позакоренево для профілактики та усунення дефіциту цинку, а також для покращення якості продукції.

Кукурудза: обробка у фазі 3–9 справжніх листків. Норма витрати — 1–2,0 кг/га. Рекомендована кількість обробок — 1–2.

Картопля: обробка перед змиканням рослин у міжряддях та у фазі бутонізації. Норма витрати — 1–2,0 кг/га. Рекомендована кількість обробок — 1–2.

Садові культури: обробка у фазі відокремлення бутонів або одразу після збирання плодів. Норма витрати — 0,1 кг на 100 л робочого розчину. Рекомендована кількість обробок — 1.

Рекомендована витрата робочого розчину: 100–300 л/га для польових культур і 800–1200 л/га для садових культур.

Обприскування доцільно проводити профілактично, до появи виражених симптомів дефіциту. Не обробляти вологу листову поверхню та не проводити обробку, якщо протягом 1,5–2 годин очікуються опади. Працювати у ранкові або вечірні години в безвітряну погоду. Не застосовувати за температури повітря вище +25 °C та за відносної вологості повітря нижче 40 %. Робочий розчин використати протягом 24 годин після приготування.

Препарат можна змішувати з іншими загальновживаними засобами захисту рослин на відповідній культурі, але перед баковим змішуванням у кожному конкретному випадку потрібно провести тест на сумісність.

''' + SOURCE_URL


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


def _without_application(card: dict) -> dict:
    out = deepcopy(card)
    content = out.get('content')
    if isinstance(content, dict):
        content['application'] = '__IGNORED__'
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description='Safely update only Brexil Zn application copy in Product Card v3.')
    parser.add_argument('--apply', action='store_true', help='Write the change. Without this flag only preview is printed.')
    args = parser.parse_args()

    path, current = _find_card()
    content = current.get('content')
    if not isinstance(content, dict):
        raise SystemExit('Invalid card: content must be an object')

    updated = deepcopy(current)
    updated['content']['application'] = APPLICATION

    if _without_application(current) != _without_application(updated):
        raise SystemExit('SAFETY CHECK FAILED: fields other than content.application would change')

    print(json.dumps({
        'product_id': updated.get('product_id'),
        'slug': updated.get('slug'),
        'title': (updated.get('content') or {}).get('title'),
        'file': str(path),
        'field': 'content.application',
        'source': SOURCE_URL,
        'apply': bool(args.apply),
        'characters_before': len(str(content.get('application') or '')),
        'characters_after': len(APPLICATION),
    }, ensure_ascii=False, indent=2))

    if not args.apply:
        print('\nDRY RUN: no files changed. Re-run with --apply to write.')
        return 0

    backup = _backup(current)
    try:
        _save_atomic(path, updated)
        verify = _load(path)
        if (verify.get('content') or {}).get('application') != APPLICATION:
            raise RuntimeError('application text mismatch after write')
        if _without_application(verify) != _without_application(current):
            raise RuntimeError('a field other than content.application changed')
    except Exception as exc:
        _save_atomic(path, current)
        raise SystemExit(f'VERIFY FAILED: original card restored: {exc}')

    print(json.dumps({
        'status': 'APPLIED',
        'backup': str(backup),
        'product_id': updated.get('product_id'),
        'slug': updated.get('slug'),
        'sku_count': len(((updated.get('sku_media') or {}).get('skus') or [])),
        'commerce_changed': False,
        'media_changed': False,
        'sku_changed': False,
        'other_content_changed': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
