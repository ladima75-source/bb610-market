# Production deployment checklist

## Storefront
- [ ] `market.bb610.com.ua` открывается по HTTPS.
- [ ] HTTP перенаправляется на HTTPS.
- [ ] CNAME корректен.
- [ ] 404 работает.
- [ ] Все product/category canonical ведут на production domain.
- [ ] robots.txt доступен.
- [ ] sitemap.xml доступен.

## Backend
- [ ] API развернут отдельно от GitHub Pages.
- [ ] API HTTPS.
- [ ] CORS ограничен production storefront.
- [ ] DEBUG выключен.
- [ ] Admin credentials не находятся в публичном репозитории.
- [ ] Payment/delivery keys только в environment/secret store.
- [ ] SQLite/DB файл не доступен через web root.

## Orders
- [ ] Создание заказа возвращает уникальный order_id.
- [ ] Idempotency-Key проверен.
- [ ] Price/availability перепроверяются сервером.
- [ ] immutable order item snapshot сохраняется.
- [ ] admin видит новый заказ.
- [ ] notification failure не теряет заказ.

## Delivery
- [ ] Нова пошта live lookup.
- [ ] Укрпошта live flow или утверждённый manual fallback.
- [ ] branch/postomat сохраняется в order delivery snapshot.
- [ ] tracking сохраняется и отображается в admin.

## Payment
- [ ] хотя бы один способ оплаты реально активен;
- [ ] online provider подпись/webhook проверены;
- [ ] browser return не может сам поставить paid;
- [ ] повторный webhook дедуплицируется;
- [ ] COD и online-card имеют разные статусы.

## Analytics
- [ ] GTM включать только после E2E.
- [ ] один add_to_cart на действие.
- [ ] один begin_checkout на checkout.
- [ ] один purchase на transaction_id.
- [ ] purchase только после purchase_ready=true.
- [ ] item_id == BB610 SKU во всех системах.

## Legal / Trust
- [ ] продавец указан одинаково в footer/legal/Merchant.
- [ ] телефон и email рабочие.
- [ ] адрес указан.
- [ ] delivery policy актуальна.
- [ ] payment policy актуальна.
- [ ] returns policy утверждена.
- [ ] privacy и terms заполнены реальными данными.
