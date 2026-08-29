# BB610 MARKET — STAGE 7 / ORDERS CORE

Stage 7 completes the order-storage skeleton without changing Stages 1–6.

## Implemented
- Real server-side order persistence reference using SQLite.
- Immutable line-item snapshots: SKU, product, variant, unit price, quantity, line total.
- Unique order ID + human-readable order number.
- Public confirmation token is deterministic HMAC from order ID; only its SHA-256 hash is stored in DB, so idempotent retries can replay the same safe confirmation token.
- Idempotency-Key protection.
- Operational statuses: `new → confirmed → preparing → shipped → completed`, plus cancellation paths.
- Status history/audit trail.
- Separate payment and shipping status fields reserved for Stages 8–9.
- Admin Orders API protected by server-side bearer token.
- Static `/admin/` panel that reads orders only via the protected API.
- Optional Telegram and SMTP notification adapters; disabled until server environment variables are configured.
- Notification delivery log.
- Existing Stage 5 public order confirmation contract retained.
- `purchase` remains backend-gated and `purchase_ready` stays false throughout Stage 7. Order status changes cannot unlock it; payment/order finalization in Stage 9 will own that decision. Stage 7 does not enable GTM/GA4/Meta/Ads.

## Important production rule
The static GitHub Pages site cannot safely hold order data or secret credentials. `backend/` must be deployed to a server/runtime with persistent storage. GitHub Pages remains the storefront frontend.

## Current catalog state
Commercial SKU price/availability are still not configured. Therefore the real create-order endpoint correctly rejects draft/unavailable SKU. No fake orders or prices were enabled just to demo Stage 7.

## Bootstrap admin authentication
The supplied admin UI uses `BB610_ADMIN_TOKEN` as a minimal bootstrap security boundary. The token is entered by the operator and stored only in browser `sessionStorage`. For a mature multi-user operation replace this with managed identity/SSO; the Orders API boundary can remain unchanged.
