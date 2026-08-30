# BB610 Market — Products & Orders Admin v2

## Что добавлено

### Заказы
- Поиск по номеру заказа, клиенту, телефону и e-mail.
- Человекочитаемые статусы на украинском.
- Полная карточка заказа: клиент, позиции, сумма, доставка, оплата.
- Быстрые ссылки позвонить / написать e-mail.
- Изменение рабочего статуса заказа.
- Ввод ТТН прямо в карточке заказа.
- Внутренние заметки менеджера, которые покупатель не видит.
- История статусов сохранена.
- Существующая Approval Queue для отмены заказа сохранена.

### Карточки товаров
Новая страница: `/admin/catalog.html`

- Список всех текущих товаров.
- Поиск и фильтр опубликованных/черновиков.
- Редактирование существующей карточки без GitHub.
- Создание нового товара кнопкой `+ Додати товар`.
- Основные поля товара: название, бренд, категория, производитель, страна, тип, форма, NPK, действующее вещество.
- Тексты: описание, рекомендации производителя, применение, нормы, ограничения.
- Списочные поля: культуры, назначение, состав, заводские фасовки.
- Основное фото и дополнительные фотографии.
- Загрузка JPG/PNG/WEBP прямо с компьютера, до 8 MB на файл.
- Источник и флаг BB610 VERIFIED.
- Черновик / публикация.
- Добавление новых SKU/фасовок к товару.

### Архитектура
- Старый `data/catalog.master.json` остаётся статической базой/резервом.
- Изменения карточек и новые товары хранятся в SQLite на VPS.
- Публичный сайт получает runtime overlay через `/api/v1/catalog/content`.
- Цены/наличие продолжают жить в `sku_commerce` и `/api/v1/catalog/commerce`.
- Новый динамический SKU участвует в checkout с серверной проверкой цены и наличия.
- Загруженные фото хранятся на VPS в `backend/runtime/media/products` и выдаются через `/media/products/...`.

## Новые API
- `GET /api/v1/catalog/content`
- `GET /api/v1/admin/catalog/products`
- `GET /api/v1/admin/catalog/products/{product_id}`
- `POST /api/v1/admin/catalog/products`
- `PATCH /api/v1/admin/catalog/products/{product_id}`
- `POST /api/v1/admin/catalog/products/{product_id}/skus`
- `POST /api/v1/admin/catalog/media`
- `POST /api/v1/admin/orders/{order_id}/notes`

## Миграции
- `006_catalog_cms.sql`
- `007_order_admin_notes.sql`

## Важно при деплое
После `git pull` выполнить обновление Python-зависимостей, потому что загрузка файлов использует `python-multipart`:

```bash
cd /opt/bb610-market
source .venv/bin/activate
pip install -r backend/requirements.txt
systemctl restart bb610-market
```

SQLite база и `.env` при обновлении репозитория не заменяются.
