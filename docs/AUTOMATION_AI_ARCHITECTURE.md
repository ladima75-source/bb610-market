# BB610 Market — Automation & AI Architecture

## Design principle

Deterministic commerce logic remains deterministic. AI can prepare analysis or drafts, but does not become the source of truth for orders, price, payment, stock or shipment state.

### Three authority levels

- **AUTO** — deterministic low-risk actions and technical logging.
- **AI PREPARE** — analysis/draft generation. No critical mutation by the model.
- **HUMAN APPROVAL** — actions with business, financial or legal consequences.

## Event envelope

Every event has:

- stable `event_id`;
- `event_type`;
- aggregate type/id;
- privacy-minimized JSON payload;
- source;
- creation/processing timestamps.

Examples:

- `order.created`
- `order.status_changed`
- `order.cancel_requested`
- `payment.paid`
- `payment.cancelled`
- `shipment.tracking_attached`
- `shipment.tracking_updated`

## AI privacy boundary

The default AI job contains order ID, order total/item count, payment/delivery method and operational event metadata. It does **not** automatically include customer name, phone, email or street address.

A future worker must enforce `context_scope` before fetching additional data.

## Approval execution

Stage 12 uses order cancellation as the first real approval-controlled action:

1. Operator requests cancellation.
2. `order.cancel_requested` event is emitted.
3. Rule creates `approval_request`.
4. Admin approves/rejects it.
5. Only approval executes the existing Orders transition to `cancelled`.
6. All steps are written to audit/event history.

## AI provider

No external provider is active in Stage 12. `backend/services/ai/` defines the integration boundary. Provider credentials must be server-side environment secrets.
