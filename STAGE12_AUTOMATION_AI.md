# Stage 12 — Automation & AI Foundation

Stage 12 adds an event-driven operational layer without changing the ecommerce identity or analytics architecture from Stages 1–11.

## Pipeline

`Commerce event -> Rule -> AUTO / AI PREPARE / HUMAN APPROVAL -> Audit log`

## Database entities

- `commerce_events` — immutable operational event envelope.
- `automation_rules` — event-to-action rules.
- `ai_jobs` — provider-neutral AI work queue.
- `approval_requests` — explicit human decision queue.
- `automation_audit_log` — operational audit trail.

## Safety model

- AI is disabled by default (`BB610_AI_PROVIDER=disabled`).
- No provider key is shipped in frontend or repository templates.
- AI jobs default to privacy-minimized context (`order_summary_no_pii`).
- High-risk actions can require approval. Stage 12 routes order cancellation through Approval Queue.
- Payments, refunds, pricing, VERIFIED publication and advertising budget are not delegated to AI by Stage 12.

## Seed rules

1. `order.created` -> AI PREPARE `order_triage`.
   If AI provider is not configured the job is stored as `blocked`, not lost and not executed.
2. `payment.paid` -> AUTO audit-only action.
3. `order.cancel_requested` -> HUMAN APPROVAL.

## Admin

`/admin/` now contains:

- Замовлення
- Потребує рішення
- AI Jobs
- Автоматизації
- Audit

## Important

Stage 12 is an orchestration foundation, not an autonomous agent. A real LLM/provider adapter can be attached later to `backend/services/ai/` without changing Orders, Delivery or Payment domains.
