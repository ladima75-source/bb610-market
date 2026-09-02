# BB610 Market — Stage 16A: Real Product Cards + Feed Readiness

## Ціль
Перевести BB610 Market від внутрішнього TEST ORDER до реальної стартової матриці товарів та підготувати Google Merchant / Meta Catalog до перевірки без вигаданих цін, залишків, GTIN або MPN.

## Стартова матриця
- 40 SKU загалом.
- 29 SKU — `A / склад`.
- 11 SKU — `B / тест`.
- Назви та фасування базуються на погодженій матриці Organic Planet.
- Ціни, акційні ціни, фактична наявність, кількість і перемикач `Продаж` НЕ імпортуються з прайсу постачальника. Їх оператор задає вручну в `Адмінка → Ціни`.

## Картки товарів
Stage 16A створює/оновлює 34 товарні сімейства і гарантує 40 стабільних BB610 SKU. Для карток додано:
- зрозумілу українську торгову назву;
- бренд / виробника, коли він підтверджений;
- категорію, тип, форму, NPK де він відомий;
- короткий опис та безпечні тексти застосування без вигаданих норм;
- SEO title / description;
- Feed title / description;
- canonical product/SKU URL;
- launch priority A/B;
- explicit feed policy;
- контроль реального фото для рекламних фідів;
- GTIN/MPN залишаються порожніми, доки не підтверджені джерелом.

## Google / Meta feeds
Існуючі статичні файли `feeds/*` залишаються build-snapshot і генеруються з `data/catalog.master.json`.

Оскільки ціна та наявність тепер керуються LIVE через SQLite / admin API, Stage 16A додає правильні runtime-фіди:
- Google Merchant: `https://api.market.bb610.com.ua/api/v1/catalog/feeds/google-merchant.csv`
- Meta Catalog: `https://api.market.bb610.com.ua/api/v1/catalog/feeds/meta-catalog.csv`
- Feed Status: `https://api.market.bb610.com.ua/api/v1/catalog/feeds/feed-status.json`

Саме LIVE URL слід використовувати для майбутнього scheduled fetch у Merchant Center / Meta.

### Умови потрапляння у LIVE feed
SKU потрапляє в feed тільки коли одночасно:
1. `Продаж` увімкнений в адмінці;
2. фактична ціна > 0;
3. availability відома (`in_stock`, `out_of_stock`, `preorder`, `backorder`);
4. товар не прихований CMS;
5. `feed_policy=allowed`;
6. є реальне фото товару, а не category placeholder;
7. є бренд, якщо для картки він позначений обов'язковим.

`feed-status.json` показує блокуючі причини та warnings для кожного SKU. Відсутній/непідтверджений GTIN/MPN дає warning, але система не вигадує ідентифікатор.

## Structured data
На SKU-сторінці після завантаження LIVE commerce overlay Product JSON-LD синхронізується з реальною ціною, availability, SKU та Offer. Browser redirect або frontend ніколи не є джерелом істини для замовлення/платежу.

## Адмінка
У `Адмінка → Ціни` додано блок `Фіди Google / Meta` з прямими посиланнями на:
- Google Merchant CSV;
- Meta Catalog CSV;
- Feed Status.

## Безпека даних
- TEST ORDER не видаляється і залишається internal-only.
- Stage 16A не перезаписує існуючі записи `sku_commerce` у SQLite; уже введені вручну ціни не стираються.
- Нові SKU при першому старті backend створюються disabled / без ціни, якщо до цього не існували.
- ЗЗР / legacy-товари без explicit `feed_policy=allowed` не потрапляють у LIVE feed автоматично.

## Перевірка після установки
1. `Адмінка → Ціни` — має з'явитися 40 SKU стартової матриці серед загального каталогу.
2. Ввести ціну, availability, кількість і `Продаж` для одного реального SKU з реальним фото, наприклад Megafol 100 мл.
3. Відкрити Feed Status: SKU має перейти в `included=true` (GTIN/MPN можуть лишатися warning).
4. Завантажити Google Merchant CSV і перевірити id/title/price/availability/link/image/brand.
5. Оформити реальний тестовий checkout цим SKU.
