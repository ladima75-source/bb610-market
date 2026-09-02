# BB610 Market — Stage 15A.2 Nova Poshta Sender Save Hotfix

Fixes the Nova Poshta sender settings workflow in Admin → Інтеграції:

- sender/contact/address selections are rehydrated after reconnect/reload;
- Save is blocked when only part of the sender trio is selected;
- the browser verifies that the backend returned the same Sender/Contact/Address refs that were submitted;
- backend rejects partial sender configuration with HTTP 422 instead of silently persisting an incomplete state;
- successful save explicitly confirms that sender, contact and dispatch point were persisted.

This patch does not create a TTN and does not touch orders, payments, media, catalog, or product data.
