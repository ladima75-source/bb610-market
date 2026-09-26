# BB610 Market — Google Ads / Merchant / PDP launch checkpoint

Дата: 2026-09-26
Статус: подготовка к запуску, кампании НЕ запущены.

## Merchant Center
- Account: 5858266688.
- Shopping Ads: 164 active / 0 pending / 0 disapproved.
- Free Listings: 0 active / 163 pending / 0 disapproved (отдельный reporting context, Shopping Ads не блокирует).
- Проблема SeaSailer 20 кг «изображение слишком маленькое» устранена.
- SKU BB610-906E45D6FF4693 теперь использует локальное изображение:
  https://market.bb610.com.ua/assets/img/v5/channel/seasailer-20kg.jpg
- Изображение 500x500, image/jpeg.
- Merchant уже видит новый image_link и Google thumbnail.

## Google Ads
Account: 520-890-7439 (BB610 Market)

Кампании:
- BB610 | Search | Brand | UA — PAUSED — 50 грн/день — Manual CPC.
- BB610 | Search | Products | UA — PAUSED — 200 грн/день — Manual CPC.
- BB610 | Search | SKU | UA — PAUSED — 300 грн/день — Manual CPC.

Search Partners выключены.
SKU geo подтвержден Presence only.
Brand/Products пользователь вручную выставлял Presence only; Windsor может отображать задержанно.

### Уже сделано по структуре
- Brand отделен от non-brand.
- В Brand добавлены phrase keywords: bb610, бб610.
- В Products добавлено 34 campaign-level negative keywords:
  - бренд BB610;
  - названия SKU, которые уже имеют отдельные SKU ad groups.
- В SKU добавлены brand negatives bb610 / бб610.
- Цель: исключить внутреннюю конкуренцию Brand / Products / SKU.

### SKU Search
12 основных рекламных ad groups:
- Kendal
- Plantafol 10-54-10
- Plantafol 5-15-45
- Brexil Mix
- PeKacid 0-60-20
- Master 20-20-20
- Viva
- Master 13-40-13
- Plantafol 20-20-20
- Megafol
- Radifarm
- Kendal TE

Используются Exact + Phrase.
Текущие RSA одобрены Google.
Ad Strength не используется как самостоятельный KPI; часть RSA Average/Poor требует улучшения только если есть реальная коммерческая причина.

## Аналитика / теги
- GTM: GTM-MF8PZJCJ
- GA4: G-QWG1K17HC3
- Google Ads conversion: AW-18468335580
- Purchase conversion label: TnTkCK6GtoEdENzfseZE
- Purchase отправляет:
  - value
  - currency
  - transaction_id
- Meta Pixel: 1103668908981910
- Meta CAPI endpoint включен.
- Consent Mode реализован через analytics.js.

## SEO / PDP
Первоначально обнаружен динамический product.html с noindex.
После дальнейшей ревизии подтверждено, что архитектура уже развилась в правильную схему:
- динамический product.html оставляется техническим / noindex;
- индексируемые товарные страницы публикуются по /products/.../;
- config/seo-routes.js связывает V5 продукты с SEO routes;
- js/product.js умеет выбирать SEO canonical.

Для рекламных SKU уже есть SEO routes, включая:
- /products/kendal/
- /products/kendal-te/
- /products/megafol/
- /products/radifarm/
- /products/viva/
- /products/brexil-mix/
- /products/pekacid-0-60-20/
- /products/master-13-40-13/
- /products/master-20-20-20/
- /products/plantafol-10-54-10/
- /products/plantafol-20-20-20/
- /products/plantafol-5-15-45/

## Контент карточек
По 12 рекламным SKU тексты в целом заполнены:
- short description;
- описание;
- применение;
- характеристики;
- how it works.

Слабое место: медиа.
- У большинства рекламных SKU около 2 изображений.
- Видео в текущем продуктном контенте фактически отсутствует.
- Kendal TE в старом runtime слое имел недостаток собственных изображений.
- Приоритет перед запуском: улучшить фото/инфографику/видео именно для SKU, на которые покупается трафик.

## Текущий следующий шаг
1. Не запускать кампании.
2. Проверить, что Search ads ведут на SEO landing pages /products/.../, а не старые product.html?id=...
3. Там, где Ads еще ведут на динамические URL, заменить landing pages безопасно:
   - создать новые RSA с теми же/улучшенными текстами и правильным SEO final URL;
   - старые RSA оставить/перевести в PAUSED после read-back;
   - сама campaign остается PAUSED.
4. Затем пройти 12 рекламных PDP по медиа/контенту/фасовкам/merchant consistency.
5. После этого — финальный go/no-go запуск и недельный бюджет.

## Бюджет первого теста
Текущий максимальный недельный лимит:
- Brand 350 грн
- Products 1400 грн
- SKU 2100 грн
Итого максимум 3850 грн / 7 дней.
Это верхний предел, не обязательный расход.

## Правило
- Никакая Ads campaign не включается без прямого разрешения пользователя.
- Не делать косметические изменения ради score/Ad Strength.
- Только изменения, которые снижают риск потери денег или увеличивают вероятность продаж.
