# BB610 MARKET — Stage 12 communications runtime fix

Updated after live Telegram + Gmail testing on 2026-08-29.

- `backend/.env` now loads automatically through `python-dotenv` whenever the backend package is imported.
- Existing process/hosting environment variables take priority over `.env`.
- Telegram and SMTP secrets remain backend-only and are excluded by `.gitignore`.
- New-order Telegram/email messages now include order number, customer, phone, total, payment, delivery, product lines, and Admin URL.
- `notification_log` behavior is preserved.
- `.env.example` points order notifications to `admin.bb610@gmail.com` and includes the Admin URL.
- Added an idempotent cleanup utility for the local `TEST-001` notification test order.
- No changes to SKU identity, checkout/order contracts, payment/delivery architecture, Merchant/Meta/GA4/GTM, or purchase gating.
