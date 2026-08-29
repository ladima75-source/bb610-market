# BB610 MARKET — Stage 8: Delivery Core

Stage 8 adds a carrier-neutral delivery layer on top of Stage 7 Orders Core. Stages 1–7 remain the source of truth for SKU, cart, order creation and analytics gating.

## Checkout
Supported fulfillment structures:
- `pickup_dnipro / pickup`
- `delivery_dnipro / courier`
- `nova_poshta / branch`
- `nova_poshta / locker`
- `ukrposhta / branch`

The checkout sends structured delivery fields (`provider`, `service`, city/branch refs, postal code/address) instead of one free-text destination. Manual text entry remains available when carrier API credentials are not configured.

## Order database
`002_delivery.sql` adds a 1:1 `order_delivery` record and append-only `delivery_events`. Orders keep a delivery snapshot independent of future carrier directory changes.

## Nova Poshta
Official API endpoint is kept server-side. With `BB610_NOVA_POSHTA_API_KEY`, city and branch/locker lookup can run through the Nova Poshta API. The key is never exposed to the browser. Shipment/EW creation is intentionally locked until sender refs, cargo defaults/weight and payment policy are confirmed.

## Ukrposhta
A separate adapter and production configuration are reserved. The e-commerce API requires business credentials/token. Stage 8 does not invent account-specific API calls or credentials; checkout works with manual city/branch entry until the production integration is configured and tested.

## Admin
The order panel now shows structured delivery data and allows an operator to attach a tracking/TTN number. Tracking refresh is adapter-based and can be enabled per carrier when production credentials are available.

## Safety / invariants
- Carrier API credentials are backend-only.
- Browser data is not authoritative for delivery price.
- Delivery amount remains `0` until a backend quote/rule is introduced; no fake price is shown.
- Attaching a tracking number does not unlock `purchase` analytics.
- Stage 8 does not change payment, GTM, GA4, Meta or Merchant behavior.
