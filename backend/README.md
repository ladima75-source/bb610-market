# Backend boundary (Stage 5)

No backend is bundled or required to browse the current static BB610 Market site.

For production ordering, implement the provider-neutral API described by `openapi-stage5.yaml`, then set only the public API origin in `config/commerce-config.js`.

Required backend responsibilities:
1. Validate request schema and Idempotency-Key.
2. Resolve SKU from authoritative commerce storage.
3. Re-check commercial status, current price, stock and currency.
4. Reject or return explicit conflict when a line cannot be sold.
5. Create immutable order snapshots and unique transaction/order IDs.
6. Create payment sessions server-side when applicable.
7. Verify payment webhooks server-side.
8. Return a public confirmation state safe for the success page.
9. Decide when `analytics.purchase_ready` and `clear_cart` may become true.
10. Never expose provider secret keys to the static frontend.
