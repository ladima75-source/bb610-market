from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

CONTENT_KEYS = (
    'short_description',
    'description',
    'benefits',
    'how_it_works',
    'application',
    'composition',
    'seo',
)

VALAGRO_BREXIL_CATALOGUE = 'https://www.valagro.com/media/filer_public/b6/7d/b67dfa60-9560-4b52-aa43-edd528ec24ea/valagro_catalogue_farm2018_en.pdf'
BENEFIT_PZ_CATALOGUE = 'https://www.valagro.com/media/media_articles/attachments/ValagroCatalogue2019_1J0QPe9.pdf'
BREXIL_MIX_UA = 'https://www.syngenta.ua/product/crop-protection/mikroelementy/breksiltm-miks'
BOROPLUS_UA = 'https://www.syngenta.ua/product/crop-protection/mikroelementy/boroplyustm'

PRODUCTS: dict[str, dict] = {
    'brexil-ca': {
        'source': VALAGRO_BREXIL_CATALOGUE,
        'short_description': 'Кальцієве мікродобриво з 20% CaO та 0,5% B у комплексі з LSA для позакореневого живлення.',
        'description': '''Brexil Ca — спеціалізоване листкове мікродобриво лінійки Brexil для профілактики та корекції дефіциту кальцію. За офіційним каталогом Valagro, продукт містить 20% CaO та 0,5% бору.

Мікроелементи лінійки Brexil комплексовані природним носієм LSA (лігносульфонатом амонію), який має високу спорідненість із рослинними тканинами та сприяє швидкому і безпечному поглинанню поживних речовин через листкову поверхню.''',
        'benefits': [
            {'title': '20% CaO', 'text': 'Концентрований кальцієвий компонент для цільового листкового живлення.'},
            {'title': 'Бор 0,5%', 'text': 'Додаткове джерело бору у складі формуляції.'},
            {'title': 'LSA-комплекс', 'text': 'Природний лігносульфонатний носій сприяє проникненню та засвоєнню мікроелементів.'},
            {'title': 'Листкове внесення', 'text': 'Формуляція мікрогранул розрахована на позакореневе живлення.'},
        ],
        'how_it_works': '''Brexil Ca постачає кальцій і бор безпосередньо через листкову поверхню. LSA — лігносульфонат амонію природного походження — виконує роль комплексоутворювача та носія, полегшуючи проходження поживних речовин через кутикулу.

За описом лінійки Brexil, така система сприяє швидкому листковому поглинанню та переміщенню мікроелементів у тканинах рослини при низькому ризику фітотоксичності.''',
        'application': f'''Brexil Ca застосовують позакоренево для профілактики та корекції дефіциту кальцію.

За офіційним каталогом Valagro рекомендовані орієнтовні норми: плодові культури — 2,5–3,0 кг/га; овочеві — 2,5–3,0 кг/га; польові — 2,5–3,0 кг/га; квіткові культури — 250–300 г на 100 л робочого розчину.

Робочий розчин слід наносити рівномірно по листковій поверхні. Перед баковим змішуванням з іншими препаратами доцільно перевірити сумісність і звірити регламент із актуальною етикеткою для конкретного ринку.

{VALAGRO_BREXIL_CATALOGUE}''',
        'composition': '''Кальцій (CaO): 20%
Бор (B): 0,5%
Комплексоутворювач: LSA (лігносульфонат амонію)''',
        'seo': {
            'title': 'Brexil Ca — кальцій 20% + бор 0,5% у комплексі з LSA | BB610 Market',
            'description': 'Brexil Ca — мікродобриво Valagro з 20% CaO та 0,5% B у комплексі з LSA для позакореневого живлення.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Овочеві культури; Польові культури; Квіткові культури'},
            {'label': 'Призначення', 'value': 'Профілактика та корекція дефіциту кальцію; листкове живлення'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове живлення'},
            {'label': 'Діюча речовина', 'value': 'Кальцій (CaO) 20%; Бор (B) 0,5% у комплексі з LSA'},
            {'label': 'Хімічна група', 'value': 'Мікродобрива'},
            {'label': 'Препаративна форма', 'value': 'Водорозчинні мікрогранули'},
            {'label': 'pH 1% розчину', 'value': '6,5'},
            {'label': 'Розчинність', 'value': '25 г/100 мл'},
        ],
    },
    'brexil-fe': {
        'source': VALAGRO_BREXIL_CATALOGUE,
        'short_description': 'Мікродобриво з 10% заліза у комплексі з LSA для профілактики та корекції дефіциту Fe.',
        'description': '''Brexil Fe — спеціалізоване листкове мікродобриво лінійки Brexil з 10% заліза для профілактики та корекції дефіциту Fe.

Залізо комплексоване природним носієм LSA (лігносульфонатом амонію). За технологією Brexil, LSA підвищує біологічну спорідненість формуляції з рослинними тканинами та сприяє швидкому проникненню мікроелементів через листкову поверхню.''',
        'benefits': [
            {'title': 'Залізо 10%', 'text': 'Висока концентрація Fe для цільової корекції залізного живлення.'},
            {'title': 'LSA-комплекс', 'text': 'Природний комплексоутворювач і носій для ефективного листкового засвоєння.'},
            {'title': 'Швидке поглинання', 'text': 'Лінійка Brexil розроблена для швидкого надходження мікроелементів через листок.'},
            {'title': 'Водорозчинні мікрогранули', 'text': 'Формуляція з високою розчинністю для приготування робочого розчину.'},
        ],
        'how_it_works': '''Brexil Fe забезпечує рослину залізом через листкову поверхню. LSA утримує мікроелемент у комплексованій формі та виступає специфічним носієм, який допомагає проникненню поживної речовини через кутикулу.

Це робить продукт придатним для оперативної листкової корекції нестачі заліза, зокрема за появи ознак залізного хлорозу.''',
        'application': f'''Brexil Fe застосовують позакоренево для профілактики та корекції дефіциту заліза.

За офіційним каталогом Valagro рекомендовані орієнтовні норми: плодові культури — 2,0–2,5 кг/га; овочеві — 2,5–3,0 кг/га; польові — 2,5–3,0 кг/га; квіткові культури — 150–200 г на 100 л робочого розчину.

Забезпечити рівномірне змочування листкової поверхні. Перед баковим змішуванням перевірити сумісність та актуальність локального регламенту застосування.

{VALAGRO_BREXIL_CATALOGUE}''',
        'composition': '''Залізо (Fe): 10%
Комплексоутворювач: LSA (лігносульфонат амонію)''',
        'seo': {
            'title': 'Brexil Fe — залізо 10% у комплексі з LSA | BB610 Market',
            'description': 'Brexil Fe — листкове мікродобриво Valagro з 10% Fe у комплексі з LSA для корекції дефіциту заліза.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Овочеві культури; Польові культури; Квіткові культури'},
            {'label': 'Призначення', 'value': 'Профілактика та корекція дефіциту заліза; залізний хлороз'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове живлення'},
            {'label': 'Діюча речовина', 'value': 'Залізо (Fe) 10% у комплексі з LSA'},
            {'label': 'Хімічна група', 'value': 'Мікродобрива'},
            {'label': 'Препаративна форма', 'value': 'Водорозчинні мікрогранули'},
            {'label': 'pH 1% розчину', 'value': '3,3'},
            {'label': 'Розчинність', 'value': '40 г/100 мл'},
        ],
    },
    'brexil-combi': {
        'source': VALAGRO_BREXIL_CATALOGUE,
        'short_description': 'Комплексне мікродобриво з Fe, Mn, Zn, B, Cu та Mo у системі LSA для позакореневого живлення.',
        'description': '''Brexil Combi — комплексне листкове мікродобриво лінійки Brexil для одночасного забезпечення рослин основними мікроелементами. Офіційний каталог Valagro наводить у складі Fe, Mn, Zn, B, Cu та Mo.

Мікроелементи комплексовані LSA — лігносульфонатом амонію природного походження. Технологія орієнтована на швидке і безпечне поглинання через листкову поверхню та ефективну корекцію множинних мікродефіцитів.''',
        'benefits': [
            {'title': 'Шість мікроелементів', 'text': 'Fe, Mn, Zn, B, Cu та Mo в одній формуляції.'},
            {'title': 'LSA-комплекс', 'text': 'Природний комплексоутворювач сприяє листковому поглинанню та транспорту елементів.'},
            {'title': 'Комплексна корекція', 'text': 'Підходить для ситуацій, коли рослині бракує кількох мікроелементів одночасно.'},
            {'title': 'Позакореневе живлення', 'text': 'Мікрогранульована водорозчинна формуляція для листкових обробок.'},
        ],
        'how_it_works': '''Brexil Combi постачає набір мікроелементів безпосередньо через листок. LSA утворює комплекси з мікроелементами та одночасно працює як носій, допомагаючи їм проходити через кутикулу.

Комбінація різних мікроелементів дає можливість однією листковою обробкою підтримувати кілька важливих ланок мінерального живлення.''',
        'application': f'''Brexil Combi застосовують позакоренево для профілактики та корекції комплексного дефіциту мікроелементів.

За офіційним каталогом Valagro рекомендовані орієнтовні норми: плодові культури — 200–300 г на 100 л робочого розчину; овочеві — 150–200 г/100 л; квіткові — 150–200 г/100 л; польові культури — 1,5–2,5 кг/га.

Забезпечити рівномірне змочування листкової поверхні. Перед сумісним застосуванням з іншими продуктами провести тест на сумісність і звірити актуальний локальний регламент.

{VALAGRO_BREXIL_CATALOGUE}''',
        'composition': '''Залізо (Fe): 6,8%
Марганець (Mn): 2,6%
Цинк (Zn): 1,1%
Бор (B): 0,9%
Мідь (Cu): 0,3%
Молібден (Mo): 0,2%
Комплексоутворювач: LSA (лігносульфонат амонію)''',
        'seo': {
            'title': 'Brexil Combi — комплекс Fe, Mn, Zn, B, Cu, Mo з LSA | BB610 Market',
            'description': 'Brexil Combi — комплексне листкове мікродобриво Valagro з Fe, Mn, Zn, B, Cu та Mo у системі LSA.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Овочеві культури; Польові культури; Квіткові культури'},
            {'label': 'Призначення', 'value': 'Профілактика та корекція комплексного дефіциту мікроелементів'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове живлення'},
            {'label': 'Діюча речовина', 'value': 'Fe 6,8%; Mn 2,6%; Zn 1,1%; B 0,9%; Cu 0,3%; Mo 0,2% у системі LSA'},
            {'label': 'Хімічна група', 'value': 'Мікродобрива'},
            {'label': 'Препаративна форма', 'value': 'Водорозчинні мікрогранули'},
            {'label': 'pH 1% розчину', 'value': '3,9'},
            {'label': 'Розчинність', 'value': '35 г/100 мл'},
        ],
    },
    'brexil-mix': {
        'source': BREXIL_MIX_UA,
        'short_description': 'Комплексне мікродобриво з Mg, Fe, Mn, Zn, B, Cu та Mo у хелатній формі для листкового живлення.',
        'description': '''Brexil Mix — комплексне мікродобриво для забезпечення рослин основними мікроелементами. Актуальна сторінка Syngenta Україна вказує сумарний вміст діючих речовин 15,3% і комплекс Mg, Fe, Mn, Zn, B, Cu та Mo.

Завдяки природному комплексоутворювачу LSA (лігносульфонату амонію) продукт швидко проникає в тканини рослини, повністю розчиняється у воді та зменшує поверхневий натяг робочого розчину.''',
        'benefits': [
            {'title': 'Комплекс 7 елементів', 'text': 'Mg, Fe, Mn, Zn, B, Cu та Mo для комплексного листкового живлення.'},
            {'title': 'Висока швидкість засвоєння', 'text': 'LSA сприяє проникненню мікроелементів через листкову поверхню.'},
            {'title': 'Повна водорозчинність', 'text': 'Продукт розрахований на приготування однорідного робочого розчину.'},
            {'title': 'Ефект ПАР', 'text': 'Знижує поверхневий натяг і покращує змочування листка.'},
            {'title': 'Широка реєстрація', 'text': 'Має регламенти для польових, овочевих, ягідних, плодових та інших культур.'},
        ],
        'how_it_works': '''Мікроелементи Brexil Mix надходять через листок у комплексованій формі. LSA природного походження виконує роль специфічного носія, що полегшує проходження поживних речовин через кутикулу та підвищує їх поглинання клітинами.

Поєднання кількох мікроелементів дозволяє одночасно попереджати та коригувати комплексні дефіцити, а ефект зниження поверхневого натягу покращує контакт робочого розчину з листковою поверхнею.''',
        'application': f'''Brexil Mix застосовують позакоренево для попередження й лікування дефіциту елементів живлення та покращення якості продукції.

Польові культури: кукурудза у фазі 3–7 листків, соняшник у фазі 4–8 листків, соя від 2–3 трійчастих листків до цвітіння, ріпак від відновлення вегетації до бутонізації, пшениця та ячмінь від кінця кущення до колосіння. Норма — 1–2,5 кг/га, кратність залежить від культури.

Овочеві та коренеплідні культури: буряк, морква, огірки, томати, цибуля — переважно 0,15–0,2 кг на 100 л робочого розчину у відповідні фази формування продуктивних органів або від бутонізації.

Плодові, ягідні та виноград: виноград, груша, малина, персик, суниця садова, яблуня — переважно 0,2–0,3 кг на 100 л робочого розчину у фазах бутонізації та початку формування продуктивних органів.

Обприскування краще проводити профілактично. Не працювати по вологій листковій поверхні або якщо протягом 1,5–2 годин очікуються опади. Обробку проводити вранці або ввечері в безвітряну погоду. Не застосовувати за температури вище +25 °C та відносної вологості нижче 40%. Робочий розчин використати протягом 24 годин. Оптимальна температура застосування — +12…25 °C.

Перед баковим змішуванням з іншими засобами захисту рослин у кожному конкретному випадку провести тест на сумісність.

{BREXIL_MIX_UA}''',
        'composition': '''Магній (MgO): 6,0%
Цинк (Zn): 5,0%
Бор (B): 1,2%
Молібден (Mo): 1,0%
Мідь (Cu): 0,8%
Марганець (Mn): 0,7%
Залізо (Fe): 0,6%
Комплексоутворювач: LSA (лігносульфонат амонію)''',
        'seo': {
            'title': 'Brexil Mix — комплекс мікроелементів у хелатній формі | BB610 Market',
            'description': 'Brexil Mix — Mg, Fe, Mn, Zn, B, Cu та Mo у комплексованій формі для позакореневого живлення. Офіційні норми Syngenta Україна.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Буряк; Виноград; Груша; Кукурудза; Малина; Морква; Огірки; Персик; Пшениця; Ріпак; Соняшник; Соя; Суниця садова; Томати; Цибуля; Яблуня; Ячмінь'},
            {'label': 'Призначення', 'value': 'Попередження й лікування дефіциту елементів живлення; покращення якості продукції'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове живлення'},
            {'label': 'Діюча речовина', 'value': 'MgO 6,0%; Fe 0,6%; Mn 0,7%; Zn 5%; B 1,2%; Cu 0,8%; Mo 1% у хелатній формі'},
            {'label': 'Хімічна група', 'value': 'Мікродобрива'},
            {'label': 'Препаративна форма', 'value': 'Водорозчинні гранули'},
            {'label': 'Клас токсичності', 'value': 'IV'},
            {'label': 'Реєстраційний номер', 'value': '13674, серія А 08553'},
            {'label': 'Реєстрант', 'value': 'ТОВ «Агрісол»'},
            {'label': 'Упаковка виробника', 'value': '5 кг'},
            {'label': 'Температура застосування', 'value': '+12…25 °C'},
        ],
    },
    'boroplus': {
        'source': BOROPLUS_UA,
        'short_description': 'Борне мікродобриво з 11% B (150 г/л), комплексованим етаноламіном, для профілактики та корекції дефіциту бору.',
        'description': '''BoroPlus — рідке мікродобриво з високим вмістом бору для культур, чутливих до його дефіциту. Актуальна сторінка Syngenta Україна вказує 11% бору, або 150 г/л, у комплексі з етаноламіном.

Етаноламін виконує роль комплексоутворювача і носія, що полегшує проходження бору через кутикулу листка та сприяє його швидкому засвоєнню без характерних ризиків кислотно-сольових борних форм.''',
        'benefits': [
            {'title': 'Бор 11% / 150 г/л', 'text': 'Висока концентрація бору в легкодоступній для листкового засвоєння формі.'},
            {'title': 'Комплекс з етаноламіном', 'text': 'Специфічний носій сприяє проникненню бору в тканини рослини.'},
            {'title': 'Безпечність для культури', 'text': 'Виробник позиціонує формуляцію як безпечну для рослин за дотримання регламенту.'},
            {'title': 'Сумісність із ЗЗР', 'text': 'Може застосовуватися у бакових сумішах після перевірки сумісності.'},
        ],
        'how_it_works': '''Бор у BoroPlus комплексований етаноламіном. Така форма сприяє проходженню елемента через кутикулу та його поглинанню клітинами листка.

Продукт призначений для профілактики та швидкої корекції дефіциту бору у фазах, коли потреба культури в цьому елементі особливо висока.''',
        'application': f'''BoroPlus застосовують позакоренево для попередження й лікування дефіциту бору та покращення якості продукції.

Цукрові буряки: 1 л/га від 5 листків до змикання міжрядь і в період накопичення цукру, 1–3 обробки. Ріпак: 0,5–1 л/га у фазах 4–9 листків, стеблування та бутонізації — початку цвітіння, до 4 обробок. Соняшник: 1 л/га від 6–8 листків, у фазі зірочки та на початку цвітіння, 1–3 обробки. Соя: 1 л/га у фазі 2–3 трійчастих листків і під час цвітіння, 1–2 обробки.

Овочі відкритого й закритого ґрунту та картопля: 0,15 л на 100 л робочого розчину або норма за гектарним регламентом виробника залежно від культури; 1–3 обробки. Садові культури: 1–2 л/га або 0,1 л на 100 л робочого розчину у фазах бутонізації — початку цвітіння та одразу після цвітіння.

Не рекомендується обробляти вологу листкову поверхню або працювати, якщо протягом 1,5–2 годин очікуються опади чи туман. Обприскування проводять у ранкові або вечірні години в безвітряну погоду. Не застосовувати за температури вище +25 °C та вологості нижче 40%. Оптимальна температура — +12…25 °C. Робочий розчин використати протягом кількох годин після приготування.

Перед баковим змішуванням провести тест на сумісність.

{BOROPLUS_UA}''',
        'composition': '''Бор (B): 11% (150 г/л)
Комплексоутворювач: етаноламін''',
        'seo': {
            'title': 'BoroPlus — бор 11% (150 г/л), комплексований етаноламіном | BB610 Market',
            'description': 'BoroPlus — борне мікродобриво Syngenta/Valagro з 11% B (150 г/л) у комплексі з етаноламіном. Офіційні регламенти застосування.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Буряки цукрові; Овочі відкритого і закритого ґрунту; Картопля; Ріпак; Садові культури; Соняшник; Соя'},
            {'label': 'Призначення', 'value': 'Попередження й лікування дефіциту бору; покращення якості продукції'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове живлення'},
            {'label': 'Діюча речовина', 'value': 'Бор (B) 11% (150 г/л), комплексований етаноламіном'},
            {'label': 'Хімічна група', 'value': 'Мікродобрива'},
            {'label': 'Препаративна форма', 'value': 'Розчинний концентрат'},
            {'label': 'Клас токсичності', 'value': 'III'},
            {'label': 'Реєстраційний номер', 'value': '11698, серія А 06963'},
            {'label': 'Реєстрант', 'value': 'ТОВ «Агрісол»'},
            {'label': 'Упаковка виробника', 'value': '1 л; 10 л'},
            {'label': 'Температура застосування', 'value': '+12…25 °C'},
        ],
    },
    'benefit-pz': {
        'source': BENEFIT_PZ_CATALOGUE,
        'short_description': 'Біостимулятор для збільшення та вирівнювання розміру плодів без погіршення їх щільності та лежкості.',
        'description': '''Benefit PZ — біостимулятор Valagro для збільшення та вирівнювання розміру плодів. За офіційним каталогом виробника, застосування від початку цвітіння стимулює поділ і розтягнення клітин, збільшуючи їх кількість і потенціал росту в плоді.

Продукт призначений для плодових і овочевих культур, а також кавуна та дині. У складі вказані органічний азот і органічний вуглець; виробник також описує вітаміни, білки та вільні амінокислоти як функціональні компоненти.''',
        'benefits': [
            {'title': 'Збільшення калібру', 'text': 'Сприяє переходу плодів у більші та більш однорідні розмірні класи.'},
            {'title': 'Рівномірність плодів', 'text': 'Допомагає вирівнювати плоди за розміром у межах урожаю.'},
            {'title': 'Без втрати лежкості', 'text': 'За описом виробника, не погіршує консистенцію та строк зберігання плодів.'},
            {'title': 'Робота від цвітіння', 'text': 'Застосування починають із перших фаз цвітіння, коли формується потенціал майбутнього плоду.'},
        ],
        'how_it_works': '''Benefit PZ застосовують на початку генеративного циклу. Виробник пов’язує його дію зі стимуляцією клітинного поділу та розтягнення, завдяки чому в кожному плоді формується більше клітин і зростає потенціал подальшого збільшення розміру.

У міру надходження води та нормального перебігу метаболічних процесів більша кількість клітин може збільшуватися в об’ємі, що підтримує формування плодів більшого калібру.''',
        'application': f'''Benefit PZ застосовують позакоренево, починаючи з перших фаз цвітіння.

Плодові культури, зокрема кісточкові, ківі та столовий виноград: 2–3 обробки кожні 5–7 днів від початку цвітіння, норма 3–4 л/га.

Овочеві культури — огірок, кабачок, баклажан, перець, томат: починати від першого цвітіння, повторювати кожні 7–10 днів і на наступних хвилях цвітіння; норма 3–4 л/га.

Кавун і диня: щотижневі обробки від початку цвітіння, норма 3–4 л/га.

Робочий розчин потрібно розподіляти з добрим і рівномірним змочуванням листкової поверхні. Для плодових культур офіційний каталог рекомендує не менше 800 л готового робочого розчину на гектар.

{BENEFIT_PZ_CATALOGUE}''',
        'composition': '''Загальний азот (N): 3,0%
Водорозчинний органічний азот (N): 3,0%
Органічний вуглець (C): 10,0%
Функціональні компоненти: вітаміни, білки та вільні амінокислоти''',
        'seo': {
            'title': 'Benefit PZ — біостимулятор для збільшення та вирівнювання плодів | BB610 Market',
            'description': 'Benefit PZ Valagro — біостимулятор для підтримки збільшення та вирівнювання плодів. Офіційні норми 3–4 л/га від початку цвітіння.',
        },
        'characteristics': [
            {'label': 'Культури', 'value': 'Плодові культури; Кісточкові; Ківі; Виноград столовий; Огірок; Кабачок; Баклажан; Перець; Томат; Кавун; Диня'},
            {'label': 'Призначення', 'value': 'Збільшення та вирівнювання розміру плодів; підтримка росту плодів'},
            {'label': 'Спосіб застосування', 'value': 'Позакореневе обприскування; листкове внесення'},
            {'label': 'Діюча речовина', 'value': 'Органічний азот (N) 3%; органічний вуглець (C) 10%; вітаміни, білки та вільні амінокислоти'},
            {'label': 'Хімічна група', 'value': 'Біостимулянти'},
            {'label': 'Препаративна форма', 'value': 'Рідка'},
            {'label': 'pH 1% розчину', 'value': '6,8'},
            {'label': 'Густина при 20 °C', 'value': '1,20 г/см³'},
        ],
    },
}

# BlackJak is intentionally not in this verified Valagro/Syngenta batch. The current
# legacy catalogue attributes it to Valagro, while current external product evidence
# points to another manufacturer family. It must be reconciled separately rather than
# copying unverified brand/source data into Product Card v3.
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
        raise RuntimeError(f'Invalid Product Card JSON: {path}')
    return obj


def _save_atomic(path: Path, card: dict) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(card, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def _find_cards() -> dict[str, tuple[Path, dict]]:
    products_dir = _products_dir()
    if not products_dir.exists():
        raise SystemExit(f'Product Card v3 directory not found: {products_dir}')
    found: dict[str, list[tuple[Path, dict]]] = {slug: [] for slug in PRODUCTS}
    for path in sorted(products_dir.glob('prd_*.json')):
        try:
            card = _load(path)
        except Exception:
            continue
        slug = str(card.get('slug') or '').strip().lower()
        if slug in found:
            found[slug].append((path, card))
    problems = []
    result: dict[str, tuple[Path, dict]] = {}
    for slug, matches in found.items():
        if len(matches) != 1:
            problems.append(f'{slug}: expected exactly 1 card, found {len(matches)}')
        else:
            result[slug] = matches[0]
    if problems:
        raise SystemExit('Batch preflight failed:\n- ' + '\n- '.join(problems))
    return result


def _managed_labels(spec: dict) -> set[str]:
    labels = {str(row['label']).strip().casefold() for row in spec['characteristics']}
    labels.add('npk')
    return labels


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


def _without_managed(card: dict, spec: dict) -> dict:
    out = deepcopy(card)
    content = out.get('content')
    if isinstance(content, dict):
        for key in CONTENT_KEYS:
            content[key] = '__BB610_MANAGED__'
        managed = _managed_labels(spec)
        content['characteristics'] = [
            row for row in (content.get('characteristics') or [])
            if isinstance(row, dict)
            and str(row.get('label') or '').strip().casefold() not in managed
        ]
    return out


def _build_updated(current: dict, spec: dict) -> dict:
    updated = deepcopy(current)
    content = updated.get('content')
    if not isinstance(content, dict):
        raise RuntimeError(f"Invalid card content object for {current.get('slug')}")
    for key in CONTENT_KEYS:
        content[key] = deepcopy(spec[key])
    content['characteristics'] = _merge_characteristics((current.get('content') or {}).get('characteristics'), spec)
    return updated


def _verify(card: dict, spec: dict) -> None:
    content = card.get('content') or {}
    for key in CONTENT_KEYS:
        if content.get(key) != spec[key]:
            raise RuntimeError(f'{card.get("slug")}: {key} mismatch after write')
    got = {
        str(row.get('label') or ''): str(row.get('value') or '')
        for row in (content.get('characteristics') or [])
        if isinstance(row, dict)
    }
    for row in spec['characteristics']:
        if got.get(row['label']) != row['value']:
            raise RuntimeError(f"{card.get('slug')}: characteristic mismatch: {row['label']}")
    if 'NPK' in got and got['NPK'].strip() in {'', '-', '—', '–'}:
        raise RuntimeError(f"{card.get('slug')}: empty NPK placeholder must not remain")


def main() -> int:
    parser = argparse.ArgumentParser(description='Apply the first production BB610 Product Card v3 content batch.')
    parser.add_argument('--apply', action='store_true', help='Write changes. Without this flag only a dry-run preview is printed.')
    args = parser.parse_args()

    cards = _find_cards()
    prepared: dict[str, tuple[Path, dict, dict]] = {}
    preview = []

    for slug, spec in PRODUCTS.items():
        path, current = cards[slug]
        updated = _build_updated(current, spec)
        if _without_managed(current, spec) != _without_managed(updated, spec):
            raise SystemExit(f'SAFETY CHECK FAILED for {slug}: fields outside managed content would change')
        prepared[slug] = (path, current, updated)
        preview.append({
            'slug': slug,
            'product_id': current.get('product_id'),
            'file': str(path),
            'source': spec['source'],
            'composition_lines': len(str(spec['composition']).splitlines()),
            'characteristics': len(spec['characteristics']),
        })

    print(json.dumps({
        'batch': 'BB610 Product Card v3 / Valagro-Syngenta batch v1',
        'apply': bool(args.apply),
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
        print('\nDRY RUN: no files changed. Re-run with --apply to write.')
        return 0

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_dir = _root() / 'var' / 'content_backups' / f'valagro-batch-v1-{stamp}'
    backup_dir.mkdir(parents=True, exist_ok=False)
    for slug, (_, current, _) in prepared.items():
        (backup_dir / f'{slug}.json').write_text(
            json.dumps(current, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

    written: list[str] = []
    try:
        for slug, (path, _, updated) in prepared.items():
            _save_atomic(path, updated)
            written.append(slug)
        for slug, (path, current, _) in prepared.items():
            verify = _load(path)
            _verify(verify, PRODUCTS[slug])
            if _without_managed(current, PRODUCTS[slug]) != _without_managed(verify, PRODUCTS[slug]):
                raise RuntimeError(f'{slug}: safety verification failed after write')
    except Exception:
        for slug in written:
            path, current, _ = prepared[slug]
            _save_atomic(path, current)
        raise

    print(json.dumps({
        'status': 'APPLIED',
        'batch': 'BB610 Product Card v3 / Valagro-Syngenta batch v1',
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
