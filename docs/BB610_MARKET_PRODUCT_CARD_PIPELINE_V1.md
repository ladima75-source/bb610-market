# BB610 MARKET — PRODUCT CARD PIPELINE v1

Status: ACTIVE

## 1. Working rule

The catalog is improved in complete blocks, not by endless micro-patches.

- Default unit of work: one full batch or one complete subsystem.
- No approval is requested for routine reversible implementation choices inside an approved direction.
- User review happens after a meaningful finished result, not after every small step.
- Escalate only when a decision is irreversible, changes commerce/order logic, deletes data, changes public pricing/stock, or contradicts an already approved product rule.
- Existing commerce, prices, stock, availability, orders and publication are never rewritten by content-quality automation unless a separate task explicitly authorizes it.

## 2. Product identity rule

- One product = one Product Card v3.
- Each package/size = a separate SKU inside that card.
- Product Card v3 owns content + SKU structure + media references.
- Commerce owns price + stock + availability + sale enablement + publication.
- Legacy catalog stays available as source/archive during migration.

## 3. Approved MASTER card

The previously approved MASTER-card content is the canonical source for enrichment of existing v3 cards. It is stored in:

`data/content_batches/stage22c_batch*.json`

The MASTER card contains the richer editorial/source layer: product name, brand/category, short and full description, benefits/why, how-it-works, application, specs/characteristics, origin, documents and source verification metadata.

The frozen Product Card v3 schema is not expanded to duplicate MASTER metadata. Enrichment maps only approved MASTER content into existing v3 content fields. Source verification is read separately by QA.

## 4. Source priority

Agronomic facts must be traceable. Preferred order:

1. Manufacturer official page, technical sheet, label or PDF.
2. Official distributor/importer material.
3. Supplier catalog / Organic Planet source data.
4. Secondary sources only for cross-checking.

AI may rewrite verified facts into clear commercial language, but must not invent composition, rates, compatibility, registration, safety or agronomic claims.

A MASTER card is treated as source-verified only when it contains a source URL/document and a recorded verification date/revision. Cards without that evidence cannot become READY.

## 5. Automatic QA statuses

Statuses are computed. They are not stored inside the frozen Product Card v3 schema.

### DRAFT
The card still has a core structural/content blocker, such as missing brand/category, weak descriptions, missing application/composition, no active SKU, incomplete package fields, or a disabled card.

### REVIEW
Core structure is present, but the card still needs review or has a publication blocker such as missing verified MASTER source, missing SKU photo, incomplete SEO/media metadata, missing commerce mapping, no commerce publication or no sellable SKU.

### READY
The card passes the core content gate, has a verified MASTER source, active SKU structure, primary SKU media gate and the linked commerce product has publication plus at least one priced sellable SKU.

READY is the automated release gate. It does not authorize changing commerce data automatically.

## 6. Quality dashboard

`admin/product-cards.html` is the single working screen for Product Card v3.

The Quality Center shows:

- total v3 cards;
- DRAFT / REVIEW / READY counts;
- average readiness score;
- verified MASTER-source coverage;
- SKU photo coverage;
- commerce mapping coverage;
- products with sellable SKU;
- common issue filters;
- per-card score, source state, status and blockers.

The operator works from exceptions: filter DRAFT/REVIEW or a specific issue, fix those cards, then re-run QA automatically.

## 7. Batch execution

For a full approved MASTER set or a brand batch:

1. Read the approved MASTER card and its recorded source evidence.
2. Match it to exactly one Product Card v3 identity.
3. Preflight the entire batch before writing.
4. Back up every target card.
5. Replace only v3 `content` fields that have MASTER evidence.
6. Preserve product_id, slug, enabled, SKU structure, media and all commerce data.
7. Validate every resulting v3 card.
8. Run the master-enrichment verifier.
9. Use QA to resolve remaining photo/commerce/publication exceptions.

Do not stop for approval between routine steps unless source data conflicts or a destructive/business-critical decision is required.

## 8. Hard boundaries

This pipeline must not automatically:

- change prices;
- invent stock;
- enable a sale offer;
- publish a product;
- delete legacy products/SKUs;
- merge two ambiguous product identities;
- alter product_id/slug/SKU identity during content enrichment;
- replace an existing verified media asset with an uncertain image.

These operations require their own explicit task or confirmed business rule.
