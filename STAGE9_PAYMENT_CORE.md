# BB610 MARKET — Stage 9 Payment Core

Stage 9 adds a provider-neutral payment layer without enabling any real acquiring account.

## Payment methods
- `cod` — cash on delivery / pay on receipt. Disabled by default. When enabled, a server-created order is a valid ecommerce checkout and may unlock `purchase`; collection remains `pending` until confirmed.
- `online_card` — online card payment. Disabled until a real payment adapter is configured. `purchase_ready` remains false until a signature-verified backend webhook confirms `paid`.

## Source of truth
The browser never marks an online payment as paid. Redirect query parameters are not trusted. Only the backend payment state can unlock `purchase`.

## Stable identity
`order_id` and `order_number` belong to BB610 Orders. SKU remains the item identity. Provider payment IDs are external references only.

## Security
Provider private keys, signatures and webhook secrets live only on the backend. Online-card payment state is webhook-owned; the admin UI cannot manually mark it paid.

## No live payment is bundled
Stage 9 intentionally contains no LiqPay/WayForPay/other merchant credentials and no live provider adapter. Choosing a provider later only requires implementing the adapter interface in `backend/services/payment/`.
