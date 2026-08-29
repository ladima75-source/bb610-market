# BB610 MARKET — STAGE 2 / VISUAL LANGUAGE

## Goal
Premium professional B2B/B2C e-commerce visual environment built on Stage 1 E-commerce Core.

## Locked visual principles
- Warm matte graphite, not absolute black.
- No visible fabric/noise texture.
- No glossy treatment and no decorative gradients in Stage 2 overrides.
- Product photography is the main color source.
- MARKET yellow is reserved for CTA, active navigation, counters and small accents.
- Dense professional shop grid; no return to oversized empty presentation spacing.
- Product cards remain photo-first.
- BB610 VERIFIED is a compact trust/data-verification signal, not a promotional badge.

## Brand asset
Header uses the user-supplied raster BB610 MARKET master directly, without SVG tracing:
- assets/bb610-market-logo.png
- RGBA PNG with genuine alpha transparency
- Web-sized master: 1200 × 644 px

## Implementation
The visual layer is isolated in:
- css/market-stage2.css

Existing Stage 1 architecture remains unchanged:
- catalog.master.json
- generated runtime catalog
- stable SKU/item_id model
- localStorage cart/favorites/compare
- analytics dataLayer adapter
- build_catalog.py

## Scope of Stage 2
Applied across the current static pages through a shared stylesheet. Main review emphasis remains:
- index.html
- catalog.html
- product.html
