# BB610 MARKET — Launch blockers

## B1 — Seller identity
Заполнить `config/store-info.js` реальными данными продавца:
- legal_name;
- entity_type;
- ЄДРПОУ / РНОКПП;
- registered_address;
- actual_address при необходимости;
- returns_address;
- phone;
- email;
- support_hours.

## B2 — Return policy
После юридической проверки зафиксировать:
- window_days;
- состояние товара/упаковки;
- return_method;
- return_shipping_payer;
- refund_timing;
- исключения для соответствующих товарных категорий.

## B3 — First sellable SKU
Для минимум одного SKU:
- commercial_status = active;
- offer_status = active;
- подтверждённая цена;
- currency;
- реальное availability;
- продаваемая фасовка;
- корректное изображение;
- feed_eligible только после проверки карточки.

## B4 — Delivery live credentials
Нова пошта / Укрпошта:
- API credentials;
- sender/contact refs;
- точка отправки;
- правила payer;
- вес/габариты, если требуются для расчёта;
- проверка поиска отделений и создания/привязки tracking.

## B5 — Payment live provider
Выбрать провайдера и на backend настроить:
- merchant/account ID;
- secret/signing key;
- return URL;
- webhook URL;
- signature verification;
- sandbox/live separation;
- refund workflow.

## B6 — Production deployment
- storefront: HTTPS;
- API: HTTPS;
- CORS только для реального storefront origin;
- secrets только в server environment;
- admin token заменить production credential;
- DB directory вне public web root.

## B7 — Backup / restore
Минимально:
- регулярная копия Orders DB;
- отдельное место хранения;
- retention;
- журнал успешных backup;
- тест восстановления до первого live заказа.

## B8 — Mobile & live E2E
На реальном домене проверить:

`ad/landing → product → SKU → cart → checkout → delivery → payment → order DB → admin → success → analytics gate`

Минимальные viewport: 360, 390/393, 430 px и desktop.
