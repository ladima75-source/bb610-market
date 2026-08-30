# BB610 Products Admin v1

- Admin UI: `/admin/products.html`
- Public commerce overlay: `GET /api/v1/catalog/commerce`
- Admin list: `GET /api/v1/admin/products`
- Admin update: `PATCH /api/v1/admin/products/{sku}`
- Protected by `BB610_ADMIN_TOKEN`.
- SQLite migration: `backend/migrations/005_product_commerce.sql`.
- Checkout price/availability is resolved from SQLite, not trusted from browser/static JSON.
- Static catalog remains product-content/SEO fallback.
- Megafol retail seeds: 25 ml = 50 UAH, 100 ml = 172 UAH; availability remains `unknown` until explicitly set in Admin.
- Telegram UTF-8 runtime fix is included.
