# Orders Core architecture

Flow:

`Checkout → POST /api/v1/orders → validate authoritative SKU → create immutable order snapshot → SQLite/order DB → notification adapters → Admin API / Admin UI`

The browser sends SKU + quantity and customer/fulfillment data. It never authoritatively sends price. The backend resolves price and availability from the catalog before creating an order.

## Order identity
- `orders.id`: stable UUID for integrations.
- `orders.order_number`: human-readable BB610 order number.
- `analytics_event_id`: stable event key reserved for purchase deduplication.

## Status model
- `new`
- `confirmed`
- `preparing`
- `shipped`
- `completed`
- `cancelled`

Every transition is written to `order_status_history` with timestamp, actor and optional note.

## Payment and delivery
Stage 7 reserves `payment_status`, `payment_method`, `shipping_status` and fulfillment data. Nova Poshta/Ukrposhta and payment provider adapters are intentionally not implemented here.

## Notifications
Telegram and SMTP are side effects only. Failure to send a notification must never erase or roll back the order. All attempts are stored in `notification_log`.

## Security
- Order/customer data lives server-side only.
- Public order reads require order ID + a stable HMAC public token.
- The HMAC secret lives only on the backend; only the SHA-256 token hash is stored in the DB. This also lets Idempotency-Key retries return the same confirmation token safely.
- Admin endpoints require a server-configured bearer token in this bootstrap implementation.
- Payment secrets and notification credentials never enter static frontend files.


## Analytics gate
Stage 7 never changes `purchase_ready` to true. Operational completion and analytics purchase are deliberately separate. The real payment/order-finalization policy in Stage 9 will control the purchase gate.
