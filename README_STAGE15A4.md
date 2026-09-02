# BB610 Market — Stage 15A.4

Nova Poshta sender city + warehouse hotfix.

## Why
Some Nova Poshta sender counterparties do not expose a usable CityRef/address list. Stage 15A.4 stops guessing the sender city from counterparty metadata.

## Flow
`Відправник → Контактна особа → Місто відправлення → Відділення відправлення`

The backend stores four independent refs:
- `nova_poshta.sender_ref`
- `nova_poshta.sender_contact_ref`
- `nova_poshta.sender_city_ref`
- `nova_poshta.sender_address_ref`

Contacts are loaded independently from warehouses. A warehouse lookup failure therefore no longer clears an already valid contact selection.

`ПЕРЕВІРИТИ ТТН` remains read-only. This patch does not create a real TTN during installation or tests.
