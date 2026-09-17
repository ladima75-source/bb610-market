from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

BATCH = 'BB610 Product Card v3 / Valagro-Syngenta batch v2'
CATALOGUE_2019 = 'https://www.valagro.com/media/media_articles/attachments/ValagroCatalogue2019_1J0QPe9.pdf'
CATALOGUE_2020 = 'https://www.valagro.com/media/media_articles/attachments/Valagro_Farm_Catalogue_2020.pdf'
MASTER_PAGE = 'https://www.valagro.com/en/products/farm/water-soluble-nutrition/master-line/'
MEGAFOL_PAGE = 'https://www.valagro.com/en/products/farm/bionutritionals/megafol-usa/'
VIVA_PAGE = 'https://www.valagro.com/en/products/farm/plant-biostimulants/viva/'

CONTENT_KEYS = (
    'short_description', 'description', 'benefits', 'how_it_works',
    'application', 'composition', 'seo',
)
FILTER_LABELS = {'Культури', 'Призначення', 'Спосіб застосування', 'NPK', 'Діюча речовина'}


def benefit(title: str, text: str) -> dict:
    return {'title': title, 'text': text}


def master_spec(formula: str, composition: str, focus: str) -> dict:
    title_formula = formula.replace('+', ' + ')
    return {
        'source': CATALOGUE_2019,
        'short_description': f'Водорозчинне мікрокристалічне добриво MASTER {formula} для фертигації з повною та швидкою розчинністю.',
        'description': f'''MASTER {formula} — водорозчинне мікрокристалічне добриво лінійки Valagro MASTER для систем фертигації. Лінійка розроблена для повного й миттєвого розчинення та може використовуватися в різних системах фертигації й з різними типами води завдяки кислотній реакції.\n\nФормула {formula} має {focus}. Лінійка MASTER також містить необхідні мікроелементи; за інформацією виробника, вони представлені у хелатованій формі EDTA.''',
        'benefits': [
            benefit('Повна розчинність', 'Мікрокристалічна формуляція повністю та швидко розчиняється у воді.'),
            benefit(f'NPK {formula}', f'Співвідношення макроелементів підібране як формула {formula}.'),
            benefit('Для фертигації', 'Лінійка MASTER призначена для використання у системах фертигації.'),
            benefit('Хелатовані мікроелементи', 'Лінійка доповнена необхідними мікроелементами у хелатованій формі EDTA.'),
        ],
        'how_it_works': f'''MASTER {formula} подає азот, фосфор і калій у водорозчинній формі безпосередньо через поливну систему. Кислотна реакція лінійки допомагає підтримувати повне розчинення продукту та роботу з різними типами поливної води.\n\nЗміна співвідношення N:P:K між формулами MASTER дозволяє підбирати живлення під конкретну фазу та потребу культури, тоді як мікроелементи доповнюють базове макроживлення.''',
        'application': f'''MASTER {formula} застосовують через системи фертигації. Лінійка придатна для різних культур і типів поливної води.\n\nКонкретну концентрацію маточного та робочого розчину, добову або тижневу норму і співвідношення з іншими добривами слід визначати за культурою, фазою розвитку, аналізом води та субстрату/ґрунту. У використаному офіційному каталозі немає універсальної числової норми саме для цієї формули, тому BB610 її не вигадує.\n\n{CATALOGUE_2019}''',
        'composition': composition,
        'seo': {
            'title': f'MASTER {title_formula} — водорозчинне добриво для фертигації | BB610 Market',
            'description': f'Valagro MASTER {formula}: водорозчинне мікрокристалічне добриво для фертигації. Склад, призначення та офіційне джерело.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Овочеві культури; Ягідні культури; Польові культури; Декоративні культури'},
            {'label': 'Призначення', 'value': 'Основне мінеральне живлення; керування співвідношенням NPK у фертигації'},
            {'label': 'Спосіб застосування', 'value': 'Фертигація; внесення через систему поливу'},
            {'label': 'NPK', 'value': formula.split('+')[0].strip()},
            {'label': 'Діюча речовина', 'value': f'Комплекс макроелементів NPK {formula}'},
            {'label': 'Хімічна група', 'value': 'Водорозчинні комплексні мінеральні добрива'},
            {'label': 'Препаративна форма', 'value': 'Розчинні мікрокристали'},
        ],
    }


def plantafol_spec(formula: str, composition: str, focus: str) -> dict:
    return {
        'source': CATALOGUE_2019,
        'short_description': f'Водорозчинне листкове добриво PLANTAFOL {formula} для позакореневого живлення.',
        'description': f'''PLANTAFOL {formula} — водорозчинне кристалічне добриво Valagro для позакореневого живлення. Формула поєднує азот, фосфор і калій у співвідношенні {formula} та призначена для швидкого надходження поживних елементів через листкову поверхню.\n\nЦя формула має {focus}. Вибір конкретної формули PLANTAFOL дає змогу змінювати акцент листкового живлення відповідно до потреб культури і фази розвитку.''',
        'benefits': [
            benefit(f'NPK {formula}', f'Чітко визначене співвідношення макроелементів {formula}.'),
            benefit('Позакореневе живлення', 'Продукт розрахований на внесення по листку.'),
            benefit('Водорозчинні кристали', 'Формуляція придатна для приготування однорідного робочого розчину.'),
            benefit('Керування фазовим живленням', 'Різні формули PLANTAFOL дають можливість змінювати акцент N, P або K.'),
        ],
        'how_it_works': f'''PLANTAFOL {formula} доставляє N, P і K безпосередньо на листкову поверхню у водорозчинній формі. Після нанесення поживні елементи стають доступними для швидкого позакореневого засвоєння.\n\nФормула {formula} дозволяє доповнювати кореневе живлення тоді, коли потрібна оперативна корекція балансу макроелементів або підтримка культури у відповідній фазі розвитку.''',
        'application': f'''PLANTAFOL {formula} застосовують позакоренево. За офіційним каталогом Valagro для лінійки PLANTAFOL наведені такі орієнтовні норми: плодові культури — 2,5–4,0 кг/га; овочеві — 2,5–3,5 кг/га; польові — 3,0–3,5 кг/га; квіткові культури — 150–250 г на 100 л робочого розчину.\n\nКонкретну фазу, кратність і бакову сумісність потрібно звіряти з актуальною етикеткою та технологією конкретної культури.\n\n{CATALOGUE_2019}''',
        'composition': composition,
        'seo': {
            'title': f'PLANTAFOL {formula} — добриво для позакореневого живлення | BB610 Market',
            'description': f'Valagro PLANTAFOL {formula}: водорозчинне листкове NPK-добриво. Склад, норми внесення та офіційне джерело.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Овочеві культури; Польові культури; Квіткові культури'},
            {'label': 'Призначення', 'value': 'Позакореневе NPK-живлення; оперативне коригування мінерального живлення'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове живлення'},
            {'label': 'NPK', 'value': formula},
            {'label': 'Діюча речовина', 'value': f'Комплекс макроелементів NPK {formula}'},
            {'label': 'Хімічна група', 'value': 'Водорозчинні комплексні мінеральні добрива'},
            {'label': 'Препаративна форма', 'value': 'Водорозчинні кристали'},
        ],
    }


PRODUCTS: dict[str, dict] = {
    'master-13-40-13': master_spec(
        '13-40-13',
        '''Загальний азот (N): 13%\nНітратний азот (N): 3,7%\nАмонійний азот (N): 9,3%\nФосфор (P₂O₅): 40%\nКалій (K₂O): 13%''',
        'високу частку фосфору порівняно з азотом і калієм',
    ),
    'master-20-20-20': master_spec(
        '20-20-20',
        '''Загальний азот (N): 20%\nКарбамідний азот (N): 10,4%\nНітратний азот (N): 5,6%\nАмонійний азот (N): 4,0%\nФосфор (P₂O₅): 20%\nКалій (K₂O): 20%''',
        'збалансоване співвідношення азоту, фосфору та калію',
    ),
    'master-15-5-30': master_spec(
        '15-5-30+2 MgO',
        '''Загальний азот (N): 15%\nКарбамідний азот (N): 3,0%\nНітратний азот (N): 8,4%\nАмонійний азот (N): 3,6%\nФосфор (P₂O₅): 5%\nКалій (K₂O): 30%\nМагній (MgO): 2%''',
        'підвищену частку калію та додатково містить магній',
    ),
    'master-3-11-38': master_spec(
        '3-11-38+4 MgO+25 SO₃',
        '''Загальний азот (N): 3%\nНітратний азот (N): 3%\nФосфор (P₂O₅): 11%\nКалій (K₂O): 38%\nМагній (MgO): 4%\nСірчаний ангідрид (SO₃): 25%''',
        'високу частку калію, а також містить магній і сірку',
    ),
    'plantafol-20-20-20': plantafol_spec(
        '20-20-20',
        '''Загальний азот (N): 20%\nКарбамідний азот (N): 14%\nНітратний азот (N): 4%\nАмонійний азот (N): 2%\nФосфор (P₂O₅): 20%\nКалій (K₂O): 20%''',
        'збалансоване співвідношення N, P і K',
    ),
    'plantafol-10-54-10': plantafol_spec(
        '10-54-10',
        '''Загальний азот (N): 10%\nКарбамідний азот (N): 2%\nАмонійний азот (N): 8%\nФосфор (P₂O₅): 54%\nКалій (K₂O): 10%''',
        'виражений фосфорний акцент',
    ),
    'plantafol-30-10-10': plantafol_spec(
        '30-10-10',
        '''Загальний азот (N): 30%\nКарбамідний азот (N): 24%\nНітратний азот (N): 3%\nАмонійний азот (N): 3%\nФосфор (P₂O₅): 10%\nКалій (K₂O): 10%''',
        'виражений азотний акцент',
    ),
    'plantafol-5-15-45': plantafol_spec(
        '5-15-45',
        '''Загальний азот (N): 5%\nНітратний азот (N): 5%\nФосфор (P₂O₅): 15%\nКалій (K₂O): 45%''',
        'виражений калійний акцент',
    ),
    'plantafol-0-25-50': plantafol_spec(
        '0-25-50',
        '''Фосфор (P₂O₅): 25%\nКалій (K₂O): 50%''',
        'дуже високий вміст калію без азоту',
    ),
    'megafol': {
        'source': CATALOGUE_2019,
        'short_description': 'Антистресовий біостимулятор на основі добірних рослинних екстрактів для листкового застосування.',
        'description': '''MEGAFOL — природний біостимулятор Valagro для підтримки росту рослин у нормальних умовах і під час абіотичних стресів. Офіційні матеріали описують комплекс добірних рослинних екстрактів, а також вітаміни, амінокислоти й білки, бетаїни та фактори росту.\n\nЗа регулярного внесення MEGAFOL підтримує збалансований вегетативний розвиток і продуктивність. Під час стресу продукт допомагає рослині швидше відновлювати ріст; також виробник описує його як носій інших продуктів у листкових обробках.''',
        'benefits': [
            benefit('Антистресова підтримка', 'Застосовується для підтримки рослин за абіотичних стресів.'),
            benefit('Рослинні екстракти', 'Містить комплекс добірних рослинних екстрактів і біологічно активних компонентів.'),
            benefit('Підтримка росту', 'Сприяє збалансованому вегетативному розвитку та продуктивності.'),
            benefit('Носій у листкових сумішах', 'Виробник описує MEGAFOL як носій продуктів при позакореневому внесенні.'),
        ],
        'how_it_works': '''Комплекс рослинних екстрактів, амінокислот, білків, бетаїнів та інших біологічно активних компонентів підтримує фізіологічні процеси рослини під час стресу.\n\nБетаїни й амінокислоти працюють синергічно, допомагаючи рослині швидше подолати наслідки несприятливих умов та відновити ріст.''',
        'application': f'''MEGAFOL застосовують позакоренево. За офіційним каталогом Valagro: плодові культури — 2–3 л/га перед цвітінням, після зав’язування, під час розвитку плодів і у випадках стресу; овочеві — 2–3 л/га після висаджування з повторенням кожні 10–15 днів; польові культури — 2–3 л/га, 1–2 обробки протягом циклу за абіотичного стресу.\n\nПеред баковим змішуванням перевірити сумісність і актуальну локальну етикетку.\n\n{CATALOGUE_2019}''',
        'composition': '''Основа: комплекс добірних рослинних екстрактів\nБіологічно активні компоненти: вітаміни, амінокислоти та білки, бетаїни, фактори росту''',
        'seo': {
            'title': 'MEGAFOL — антистресовий біостимулятор Valagro | BB610 Market',
            'description': 'MEGAFOL — біостимулятор на основі рослинних екстрактів для підтримки росту і відновлення рослин за абіотичного стресу.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Овочеві культури; Польові культури'},
            {'label': 'Призначення', 'value': 'Антистресова підтримка; біостимуляція; підтримка вегетативного росту'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове внесення'},
            {'label': 'Діюча речовина', 'value': 'Комплекс рослинних екстрактів, амінокислот, білків, бетаїнів та факторів росту'},
            {'label': 'Хімічна група', 'value': 'Біостимулятори'},
            {'label': 'Препаративна форма', 'value': 'Рідка'},
        ],
    },
    'radifarm': {
        'source': CATALOGUE_2020,
        'short_description': 'Кореневий біостимулятор Valagro для зменшення стресу після пересаджування та розвитку нових поглинальних коренів.',
        'description': '''RADIFARM — біостимулятор Valagro, розроблений для фази пересаджування та ранніх етапів розвитку рослин. Виробник позиціонує його як root promoter: продукт допомагає швидше подолати післяпересадковий стрес і стимулює формування розвиненої кореневої системи.\n\nОфіційні матеріали вказують на комплекс вітамінів, сапонінів, амінокислот і білків, полісахаридів, бетаїнів та мінеральної фракції.''',
        'benefits': [
            benefit('Розвиток коренів', 'Стимулює подовження наявних і формування нових поглинальних коренів.'),
            benefit('Менше стресу після пересаджування', 'Допомагає скоротити період відновлення після пересаджування.'),
            benefit('Рівномірний старт', 'Сприяє більш однорідному розвитку рослин на старті.'),
            benefit('GEA932', 'У каталозі Valagro продукт пов’язаний із технологією GEA932.'),
        ],
        'how_it_works': '''RADIFARM діє у кореневій зоні на ранніх етапах розвитку. Біологічно активний комплекс підтримує сигнали, пов’язані з формуванням коренів, і допомагає рослині швидше відновитися після пересаджування.\n\nОдночасно продукт постачає органічний вуглець, азот, калій і цинк як частину формуляції.''',
        'application': f'''RADIFARM застосовують переважно через фертигацію або локальне поливне внесення. За офіційним каталогом Valagro: овочеві культури з фертигацією — 5 л/га під час пересаджування та повторно через 7 днів; плодові культури — 5 л/га під час висаджування, через 7 днів або на початку відновлення вегетації; декоративні та горщикові рослини — 1,5–2 л/м³ води, 2–3 внесення кожні 7 днів після пересаджування.\n\nДля овочевих без фертигації офіційний каталог наводить 150–200 мл/100 л води.\n\n{CATALOGUE_2020}''',
        'composition': '''Загальний азот (N): 3%\nОрганічний азот (N): 1%\nКарбамідний азот (N): 2%\nКалій (K₂O): 8%\nОрганічний вуглець (C): 10%\nЦинк (Zn), хелатований EDTA: 0,1%''',
        'seo': {
            'title': 'RADIFARM — біостимулятор розвитку кореневої системи | BB610 Market',
            'description': 'RADIFARM Valagro — біостимулятор для укорінення, пересаджування та раннього розвитку кореневої системи.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Овочеві культури; Плодові культури; Декоративні та горщикові рослини; Розсадники'},
            {'label': 'Призначення', 'value': 'Розвиток кореневої системи; укорінення; зменшення післяпересадкового стресу'},
            {'label': 'Спосіб застосування', 'value': 'Фертигація; локальне кореневе внесення; полив'},
            {'label': 'Діюча речовина', 'value': 'Комплекс GEA932; органічний вуглець; N; K₂O; Zn-EDTA'},
            {'label': 'Хімічна група', 'value': 'Біостимулятори кореневої системи'},
            {'label': 'Препаративна форма', 'value': 'Рідка'},
        ],
    },
    'viva': {
        'source': CATALOGUE_2019,
        'short_description': 'Біостимулятор Valagro для покращення структури, біохімічної активності та мікробіологічних процесів у ризосфері.',
        'description': '''VIVA — біостимулятор Valagro для керування ризосферою та підтримки балансу між вегетативною і продуктивною частинами рослини. Виробник описує продукт як засіб, що відновлює та покращує структуру й біохімічну активність кореневої зони.\n\nАктуальна продуктова сторінка Syngenta Biologicals також вказує на підтримку мікробно опосередкованих циклів поживних речовин, активності ґрунтових ферментів і чисельності корисних мікроорганізмів.''',
        'benefits': [
            benefit('Підтримка ризосфери', 'Покращує параметри структури та біохімічної активності кореневої зони.'),
            benefit('Мікробні цикли живлення', 'Підтримує процеси мобілізації поживних елементів за участю мікроорганізмів.'),
            benefit('Корисна мікрофлора', 'Сприяє збільшенню чисельності та біомаси корисних мікроорганізмів.'),
            benefit('Вегетативно-продуктивний баланс', 'Позиціонується для підтримки збалансованого росту та продуктивності.'),
        ],
        'how_it_works': '''VIVA працює у ризосфері: біологічно активні компоненти формуляції підтримують структуру кореневого середовища, активність ферментів і мікробні процеси, пов’язані з обігом поживних речовин.\n\nЦе створює сприятливіші умови для функціонування кореневої системи та живлення рослини.''',
        'application': f'''VIVA застосовують через фертигацію. За офіційним каталогом Valagro: плодові культури — 20–30 л/га від відновлення вегетації до періоду після зав’язування, 2–3 внесення; суниця — 2–3 л/1000 м² після пересаджування, під час відновлення росту та після зав’язування; овочеві — 2–3 л/1000 м² після пересаджування, під час вегетативного росту та після зав’язування з інтервалом 10–15 днів; квіткові культури — 2–4 л/1000 м² кожні 15–20 днів; польові — 10–20 л/га локально під час сівби.\n\n{CATALOGUE_2019}''',
        'composition': '''Загальний азот (N): 3%\nОрганічний азот (N): 1%\nКарбамідний азот (N): 2%\nКалій (K₂O): 8%\nОрганічний вуглець (C): 8%\nЗалізо (Fe): 0,02%''',
        'seo': {
            'title': 'VIVA — біостимулятор ризосфери Valagro | BB610 Market',
            'description': 'VIVA Valagro — біостимулятор для підтримки ризосфери, корисної мікрофлори та балансу росту рослин.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Суниця; Овочеві культури; Квіткові культури; Польові культури'},
            {'label': 'Призначення', 'value': 'Підтримка ризосфери; біостимуляція кореневої зони; підтримка ґрунтової мікрофлори'},
            {'label': 'Спосіб застосування', 'value': 'Фертигація; локальне внесення у кореневу зону'},
            {'label': 'Діюча речовина', 'value': 'Біологічно активний комплекс; органічний вуглець; N; K₂O; Fe'},
            {'label': 'Хімічна група', 'value': 'Біостимулятори ризосфери'},
            {'label': 'Препаративна форма', 'value': 'Рідка'},
        ],
    },
}

DEFERRED = {
    'blackjak': 'brand/manufacturer/source conflict — verify and correct separately before enrichment',
}


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _products_dir() -> Path:
    return _root() / 'data' / 'product_cards_v3' / 'products'


def _load(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise RuntimeError(f'Invalid JSON object: {path}')
    return obj


def _find_all() -> dict[str, tuple[Path, dict]]:
    products_dir = _products_dir()
    if not products_dir.exists():
        raise SystemExit(f'Product Card v3 directory not found: {products_dir}')
    wanted = set(PRODUCTS)
    found: dict[str, tuple[Path, dict]] = {}
    for path in sorted(products_dir.glob('prd_*.json')):
        try:
            card = _load(path)
        except Exception:
            continue
        slug = str(card.get('slug') or '').strip().lower()
        if slug in wanted:
            if slug in found:
                raise SystemExit(f'Duplicate Product Card v3 slug: {slug}')
            found[slug] = (path, card)
    missing = sorted(wanted - set(found))
    if missing:
        raise SystemExit('PRE-FLIGHT FAILED: missing Product Card v3 slugs: ' + ', '.join(missing))
    return found


def _managed_labels(spec: dict) -> set[str]:
    return {str(row['label']).strip().casefold() for row in spec['characteristics']} | {'npk'}


def _merge_characteristics(existing, spec: dict) -> list[dict]:
    managed = _managed_labels(spec)
    kept: list[dict] = []
    for row in existing if isinstance(existing, list) else []:
        if not isinstance(row, dict):
            continue
        label = str(row.get('label') or '').strip()
        if label.casefold() in managed:
            continue
        kept.append(deepcopy(row))
    return kept + deepcopy(spec['characteristics'])


def _build(current: dict, spec: dict) -> dict:
    updated = deepcopy(current)
    content = updated.get('content')
    if not isinstance(content, dict):
        raise RuntimeError(f"Invalid card content for {current.get('slug')}")
    for key in CONTENT_KEYS:
        content[key] = deepcopy(spec[key])
    content['characteristics'] = _merge_characteristics(content.get('characteristics'), spec)
    return updated


def _without_managed(card: dict, spec: dict) -> dict:
    out = deepcopy(card)
    content = out.get('content')
    if isinstance(content, dict):
        for key in CONTENT_KEYS:
            content[key] = '__IGNORED__'
        managed = _managed_labels(spec)
        content['characteristics'] = [
            row for row in (content.get('characteristics') or [])
            if isinstance(row, dict)
            and str(row.get('label') or '').strip().casefold() not in managed
        ]
    return out


def _save_atomic(path: Path, card: dict) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(card, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def _backup_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = _root() / 'var' / 'content_backups' / f'valagro-batch-v2-{stamp}'
    path.mkdir(parents=True, exist_ok=False)
    return path


def _verify(card: dict, spec: dict) -> None:
    content = card.get('content') or {}
    for key in CONTENT_KEYS:
        if content.get(key) != spec[key]:
            raise RuntimeError(f"verify mismatch {card.get('slug')}: {key}")
    got = {str(x.get('label') or ''): str(x.get('value') or '') for x in (content.get('characteristics') or []) if isinstance(x, dict)}
    for row in spec['characteristics']:
        if got.get(row['label']) != row['value']:
            raise RuntimeError(f"verify characteristic mismatch {card.get('slug')}: {row['label']}")
    if 'NPK' in got and not any(row['label'] == 'NPK' for row in spec['characteristics']):
        raise RuntimeError(f"unexpected NPK placeholder in {card.get('slug')}")


def main() -> int:
    parser = argparse.ArgumentParser(description='Apply BB610 Product Card v3 Valagro/Syngenta content batch v2.')
    parser.add_argument('--apply', action='store_true', help='Write changes. Without this flag, run preflight/dry-run only.')
    args = parser.parse_args()

    found = _find_all()
    prepared: dict[str, tuple[Path, dict, dict]] = {}
    preview = []
    for slug, spec in PRODUCTS.items():
        path, current = found[slug]
        updated = _build(current, spec)
        if _without_managed(current, spec) != _without_managed(updated, spec):
            raise SystemExit(f'SAFETY CHECK FAILED: fields outside managed content would change for {slug}')
        if current.get('sku_media') != updated.get('sku_media'):
            raise SystemExit(f'SAFETY CHECK FAILED: sku_media would change for {slug}')
        prepared[slug] = (path, current, updated)
        preview.append({
            'slug': slug,
            'product_id': current.get('product_id'),
            'file': str(path),
            'source': spec['source'],
            'composition_lines': len([x for x in spec['composition'].splitlines() if x.strip()]),
            'characteristics': len(spec['characteristics']),
        })

    print(json.dumps({
        'batch': BATCH,
        'apply': bool(args.apply),
        'count': len(prepared),
        'products': preview,
        'deferred': DEFERRED,
        'safety_contract': {
            'content_only': True,
            'commerce_changed': False,
            'media_changed': False,
            'sku_changed': False,
        },
    }, ensure_ascii=False, indent=2))

    if not args.apply:
        print('\nDRY RUN: preflight passed; no files changed.')
        return 0

    backup_dir = _backup_dir()
    written: list[str] = []
    try:
        for slug, (path, current, _updated) in prepared.items():
            (backup_dir / path.name).write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for slug, (path, _current, updated) in prepared.items():
            _save_atomic(path, updated)
            written.append(slug)
        for slug, (path, current, _updated) in prepared.items():
            verify = _load(path)
            _verify(verify, PRODUCTS[slug])
            if _without_managed(current, PRODUCTS[slug]) != _without_managed(verify, PRODUCTS[slug]):
                raise RuntimeError(f'post-write safety mismatch: {slug}')
            if current.get('sku_media') != verify.get('sku_media'):
                raise RuntimeError(f'post-write sku_media mismatch: {slug}')
    except Exception:
        for slug in written:
            path, _current, _updated = prepared[slug]
            backup = backup_dir / path.name
            if backup.exists():
                path.write_text(backup.read_text(encoding='utf-8'), encoding='utf-8')
        raise

    print('\n' + json.dumps({
        'status': 'APPLIED',
        'batch': BATCH,
        'updated_slugs': list(PRODUCTS),
        'count': len(PRODUCTS),
        'backup_dir': str(backup_dir),
        'commerce_changed': False,
        'media_changed': False,
        'sku_changed': False,
        'deferred': DEFERRED,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
