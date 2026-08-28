# BB610 MARKET — STAGE 5: ORDERS / CHECKOUT / PAYMENT ARCHITECTURE

## Implemented
- Static GitHub Pages frontend remains autonomous for browsing/catalog.
- Provider-neutral commerce config (`config/commerce-config.js`), disabled by default.
- Order API client with request timeout and Idempotency-Key.
- Short guest checkout UI: name, phone, optional email, fulfillment, destination, comment.
- Checkout sends SKU + quantity only; browser price is not authoritative.
- Checkout is automatically blocked until backend is configured AND every cart SKU is commercially active, priced and has known availability.
- Public success page at `/order/success/`.
- Success page fetches authoritative order status from backend before any purchase event.
- `purchase` uses backend-confirmed transaction_id, total and line prices.
- Browser refresh protection: `bb610_purchase_sent:<transaction_id>` marker.
- Cart is cleared only when backend returns `clear_cart=true`.
- Payment is backend-directed: frontend accepts a redirect URL but has no payment secret or provider-specific code.
- Backend contract supplied as OpenAPI + JSON Schemas.

## Intentionally NOT implemented
- Real order API/server/database.
- A selected payment provider.
- Payment secret keys.
- Payment webhooks.
- Shipping-carrier API.
- CRM/ERP connection.
- Real purchase event in static mode.

## Activation checklist
1. Choose backend/runtime and authoritative commerce database.
2. Implement `POST /api/v1/orders` and `GET /api/v1/orders/{orderId}` to the supplied contract.
3. Configure CORS for `https://market.bb610.com.ua` only as needed.
4. Set `apiBaseUrl` in `config/commerce-config.js`.
5. Activate commercial SKU price/availability in the authoritative data source.
6. Add payment provider server-side and verify its webhook signature.
7. Test duplicate submit/idempotency, price changes, out-of-stock conflicts and payment return flow.
8. Only then enable production checkout.
