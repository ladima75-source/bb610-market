from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from backend.services import product_cards_v3 as pcv3

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


def _find_card() -> tuple[str, dict]:
    for row in pcv3.list_cards():
        if str(row.get('slug') or '').strip().lower() == SLUG:
            product_id = str(row.get('product_id') or '').strip()
            card = pcv3.get(product_id)
            if isinstance(card, dict):
                return product_id, card
    raise SystemExit(f'Product Card v3 with slug {SLUG!r} was not found')


def _backup(card: dict) -> Path:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / 'var' / 'content_backups'
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = out_dir / f'{SLUG}-{stamp}.json'
    path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description='Safely update only Brexil Zn application copy in Product Card v3.')
    parser.add_argument('--apply', action='store_true', help='Write the change. Without this flag only preview is printed.')
    args = parser.parse_args()

    product_id, current = _find_card()
    updated = deepcopy(current)
    updated.setdefault('content', {})['application'] = APPLICATION
    pcv3.validate(updated)

    print(json.dumps({
        'product_id': product_id,
        'slug': updated.get('slug'),
        'title': (updated.get('content') or {}).get('title'),
        'field': 'content.application',
        'source': SOURCE_URL,
        'apply': bool(args.apply),
        'characters_before': len(str((current.get('content') or {}).get('application') or '')),
        'characters_after': len(APPLICATION),
    }, ensure_ascii=False, indent=2))

    if not args.apply:
        print('\nDRY RUN: no files changed. Re-run with --apply to write.')
        return 0

    backup = _backup(current)
    saved = pcv3.put(product_id, updated)
    verify = pcv3.get(product_id)
    if not isinstance(verify, dict) or (verify.get('content') or {}).get('application') != APPLICATION:
        pcv3.put(product_id, current)
        raise SystemExit('VERIFY FAILED: original card restored')

    print(json.dumps({
        'status': 'APPLIED',
        'backup': str(backup),
        'product_id': saved.get('product_id'),
        'slug': saved.get('slug'),
        'sku_count': len((saved.get('sku_media') or {}).get('skus') or []),
        'commerce_changed': False,
        'media_changed': False,
        'sku_changed': False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
