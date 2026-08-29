# Delivery architecture

`Checkout -> Orders API -> normalize_fulfillment -> order_delivery -> carrier adapter`

Carrier adapters expose capabilities instead of forcing one common external API shape. This keeps the website stable if Nova Poshta/Ukrposhta change their APIs or if a third carrier is added.

Public endpoints:
- `GET /api/v1/delivery/providers`
- `GET /api/v1/delivery/{provider}/cities?q=...`
- `GET /api/v1/delivery/{provider}/branches?city_ref=...`

Admin endpoints:
- `POST /api/v1/admin/orders/{order_id}/delivery/tracking`
- `POST /api/v1/admin/orders/{order_id}/delivery/refresh`

Production shipment creation is intentionally not guessed. It should be activated only after seller sender refs, parcel weight/dimensions, payer/payment mode, declared value and return-shipment policy are fixed.
