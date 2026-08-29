# Payment Architecture

Flow:

`Checkout -> POST /orders -> server validates SKU/price/stock -> payment initialization -> order DB`

COD:
`accepted backend order -> purchase_ready=true -> payment pending -> carrier/admin confirms collected`

Online card:
`accepted backend order -> provider checkout -> provider webhook -> signature verification -> paid -> purchase_ready=true`

The browser return URL is display/navigation only and never authorizes payment.

Payment states: `pending`, `requires_action`, `paid`, `failed`, `cancelled`, `partially_refunded`, `refunded`.

Webhook idempotency is enforced by `(provider, provider_event_id)`.
