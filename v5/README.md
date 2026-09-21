# BB610 Product Master V5

Clean catalog rebuilt independently from the legacy storefront stack.

## Current baseline

- 86 canonical products
- 255 preserved SKU identities
- 75 legacy/duplicate SKU aliases
- 48 current Plantlogic request-price SKU
- 1 disabled Plantlogic legacy SKU retained only for identity/history
- 118 recorded content sources
- 0 canonical products without source-backed V5 content

## Single-source rules

- Product Master V5 is the only catalog authority.
- Stable SKU IDs are preserved.
- Commerce is migrated by exact SKU identity.
- Product text enters V5 only through recorded source provenance.
- Package value and unit are structured fields.
- SKU media is explicit; runtime matching by package text is forbidden.
- One physical media path is one V5 media record.
- Generated JS, static pages and feeds are outputs only.
- V1/V2/V3/CMS/runtime overrides are migration inputs, not V5 authorities.

## Migration gates

IDENTITY -> CONTENT -> SKU -> MEDIA -> COMMERCE

A product remains draft until the cutover gate is explicitly completed.

## Legacy compatibility

Legacy product IDs/slugs can resolve through product_aliases.
Duplicate legacy SKU can resolve through sku_aliases.
A legacy SKU that cannot be mapped safely to one exact current SKU is retained disabled rather than guessed.

## Shadow API

The new read-only catalog surface is mounted at:

`/api/v1/catalog/v5`

The existing storefront still uses the legacy catalog until shadow comparison and cutover are complete.
