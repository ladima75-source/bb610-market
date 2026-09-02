# BB610 Market — Stage 15A.3 Nova Poshta Sender Warehouse Fix

Fixes the empty **Адреса / точка відправлення** selector for Nova Poshta senders who dispatch parcels from a Nova Poshta branch.

## What changed
- sender counterparty and contact still come from the sender account;
- the dispatch point is now loaded from `Address.getWarehouses` for the sender city instead of relying on `Counterparty.getCounterpartyAddresses`;
- parcel lockers are excluded from sender dispatch choices; regular Nova Poshta branches are shown;
- the selected branch Ref is persisted as the existing `sender_address_ref` and used as `SenderAddress` for `WarehouseWarehouse` shipments;
- dry-run validates that the saved branch still exists before a real TTN can be created;
- no real TTN is created by this patch.

After install: Admin → Інтеграції → Нова пошта → choose sender → contact → branch → save → reopen page → use **ПЕРЕВІРИТИ ТТН**.
