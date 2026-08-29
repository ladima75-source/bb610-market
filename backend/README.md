# BB610 Market Orders backend — Stage 7 reference implementation

This folder is now a runnable Orders Core reference backend, not only an API contract.

## Local run
From the site root:

```bash
python -m pip install -r backend/requirements.txt
export BB610_ADMIN_TOKEN='use-a-long-random-secret'
export BB610_CORS_ORIGINS='http://127.0.0.1:8000,http://localhost:8000,https://market.bb610.com.ua'
python -m backend.run_local
```

API: `http://127.0.0.1:8610`
Swagger: `http://127.0.0.1:8610/docs`

Set the storefront's public API origin in `config/commerce-config.js` only when a real backend is deployed. For admin UI, enter the API URL + admin token at `/admin/`.

## Persistence
Default DB: `backend/runtime/bb610-orders.sqlite3`. In production set `BB610_DB_PATH` to a persistent mounted volume and include it in backups.

## Notifications
All notification integrations are opt-in environment settings. See `.env.example`. Telegram/email are notifications, never the source of truth. The database is the source of truth.

## Current limitation by design
All current BB610 SKU remain commercially unconfigured, so order creation rejects them. This is correct until actual prices and stock are entered.

## Stage 12 — Automation & AI

The Commerce API now includes an event/rules/AI-job/approval/audit layer. AI is disabled by default and requires a backend-only provider adapter. High-risk order cancellation is routed through the approval queue.
