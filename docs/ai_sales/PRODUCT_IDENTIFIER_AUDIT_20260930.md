# BB610 Market — Product Identifier Audit

Updated: 2026-09-30
Scope: AI Sales / Google Merchant / OpenAI product discovery
Status: NO FABRICATED IDENTIFIERS

## Current channel state

Latest live validation:
- channel-eligible rows: 163
- GTIN populated: 0
- MPN populated: 0
- GTIN or MPN populated: 0
- core feed validation: PASS
- identifier coverage is a quality-enrichment gap, not a current core-feed blocker

## Rule

Never copy a manufacturer GTIN/EAN/MPN from a different package size.
A BB610 retail/repacked SKU must not inherit the identifier of a factory pack.

Populate GTIN/MPN only when the identifier is confirmed for the exact commercial unit sold by BB610 from one of:
1. manufacturer packaging / official label;
2. official manufacturer or distributor master data;
3. supplier invoice/catalog that identifies the exact package;
4. a barcode physically verified on the exact package.

## Priority AI-intent products

### Megafol

Verified product facts currently list factory packs:
- 1 L
- 10 L
- 20 L
- 1000 L

Current saleable BB610 variants include:
- 25 ml
- 100 ml
- 1 L
- 10 L

Decision:
- 25 ml / 100 ml: do not inherit a manufacturer GTIN from 1 L or larger packs.
- 1 L / 10 L: candidates for exact-pack identifier verification.
- no identifier is inserted until exact-package evidence is obtained.

### Radifarm

Current product facts list 1 L / 5 L / 10 L as package information, with source verification still partial.

Current saleable BB610 variants include:
- 25 ml
- 100 ml
- 1 L
- 10 L

Decision:
- 25 ml / 100 ml: do not inherit identifiers from larger factory packs.
- 1 L / 10 L: verify exact packaging first because the current source record is partial.
- no identifier inserted now.

### MASTER 13-40-13

Current product facts explicitly state that factory packaging for the exact formula/market still requires confirmation.

Current saleable BB610 variants:
- 20 g
- 250 g
- 1 kg
- 25 kg

Decision:
- no variant receives GTIN/MPN until the exact market package is confirmed.
- AI-17 (1 kg price intent) stays identifier-unverified.

### MASTER 20-20-20

Current verified facts note 10 kg / 25 kg in line catalogs, with market-specific confirmation still required.

Current saleable variants:
- 20 g
- 250 g
- 1 kg
- 10 kg
- 25 kg

Decision:
- 10 kg / 25 kg are first candidates for exact-pack verification.
- 20 g / 250 g / 1 kg must not inherit a large-pack identifier.
- no identifier inserted now.

### PLANTAFOL 20-20-20

Verified factory packs:
- 1 kg
- 5 kg
- 25 kg

Current saleable variants:
- 25 g
- 250 g
- 1 kg
- 5 kg

Decision:
- 1 kg / 5 kg are first candidates for exact-pack GTIN/MPN verification.
- 25 g / 250 g must not inherit identifiers from factory packs.
- no identifier inserted now.

### Brexil Fe / Nova PeKacid / SoluPotasse

Current canonical V5 product records do not provide sufficient exact-package identifier evidence for safe GTIN/MPN assignment in this audit.

Decision:
- leave identifiers blank;
- verify exact factory/supplier unit before any feed change.

## External official-source search checkpoint

Targeted official-domain searches for EAN/GTIN on priority Valagro/Syngenta products did not return a usable exact-pack identifier for:
- Megafol 1 L
- Radifarm 1 L
- MASTER 13-40-13 25 kg
- PLANTAFOL 20-20-20 1 kg

This is recorded as "not found in the targeted official search", not as proof that no GTIN exists.

## Next identifier work

Priority order:
1. exact physical/supplier barcode verification for factory-format SKUs used in high-value AI intents;
2. write verified identifier into Product Master V5 exact SKU only;
3. regenerate Google/OpenAI feeds;
4. require feed ↔ exact PDP identifier parity in live validation.

Do not lower feed integrity by filling identifier_exists, GTIN or MPN from assumptions.
