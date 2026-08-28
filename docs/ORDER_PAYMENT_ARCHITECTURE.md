# BB610 MARKET — ORDER / CHECKOUT / PAYMENT ARCHITECTURE

## Boundary
GitHub Pages remains a static frontend. The browser must never hold payment secret keys, create authoritative totals, or mark an order paid by itself.

## Order creation
Frontend sends only:
- customer/contact data;
- fulfillment choice;
- SKU + quantity;
- client_request_id / Idempotency-Key.

Backend must re-read every SKU from the authoritative commerce database, validate active status, price, stock and currency, then create an immutable order snapshot.

## Order snapshot
An accepted order stores at minimum:
- order_id and human order_number;
- created_at;
- customer + fulfillment snapshot;
- SKU, product/variant labels, quantity, unit_price for every line;
- subtotal, delivery, total, currency;
- payment status;
- order status.

Historical order lines do not change when the current product catalog changes.

## Idempotency
POST /api/v1/orders requires `Idempotency-Key`. Repeating the same request must return the same logical order, not create a second order.

## Payment
Provider is intentionally not selected in Stage 5. Backend creates a provider checkout/session and returns `payment.redirect_url`. Secret keys stay server-side.

Provider webhook is the source of truth for payment. A browser redirect such as `?paid=1` must never mark an order paid.

## Success page and purchase
`/order/success/` asks the backend for current order state. The backend sets `analytics.purchase_ready=true` only when the order is valid for purchase measurement (e.g. paid, or confirmed COD according to future business rules).

The page pushes `purchase` with server-confirmed transaction_id, total and line prices. A localStorage marker prevents repeat firing after browser refresh on the same device. The unique transaction_id remains the system-level deduplication key.

## Cart clearing
The backend response controls `clear_cart`. Cart must not be cleared merely because the payment provider redirected the browser.

## Future backend
This contract can be implemented by any backend/serverless platform. The frontend only needs `config/commerce-config.js` to receive the final API base URL.
