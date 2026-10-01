# BB610 Market — Category SEO Edge Worker

Purpose: preserve the existing Google Ads URLs while making their SEO metadata server-visible.

Intercepted route only:

- `https://market.bb610.com.ua/catalog.html*`

Changed only when:

- `category=nutrition`
- `category=biostimulation`

Everything else passes through unchanged to the current GitHub Pages origin.

## Production behavior

The Worker fetches the existing origin response and changes, before the response reaches the browser:

- `<title>`
- `<meta name="description">`
- `<link rel="canonical">`
- hero H1
- hero breadcrumb

No redirect is used. The visible URL remains exactly the current Google Ads URL.

## Resilience

Use a Workers **Route**, not a Custom Domain, because GitHub Pages remains the external origin. Configure the route to **fail open** so a Worker outage/quota issue bypasses the Worker and continues to serve GitHub Pages.

Suggested DNS/origin topology:

`visitor -> Cloudflare edge -> Worker route -> GitHub Pages`

A paid hosting account may later be added as a second origin/failover, but it is not required for this SEO change.

## Required Cloudflare prerequisites

1. `bb610.com.ua` must be an active Cloudflare zone.
2. `market.bb610.com.ua` must be a proxied Cloudflare DNS hostname whose origin remains GitHub Pages.
3. Deploy with Wrangler from this directory.
4. Route: `market.bb610.com.ua/catalog.html*`
5. Set route failure mode to **fail open**.

## Verify

These must return HTTP 200 and the correct metadata in the raw HTTP response:

- `/catalog.html`
- `/catalog.html?category=nutrition`
- `/catalog.html?category=biostimulation`

The two category responses also expose:

- `X-BB610-Category-SEO: nutrition`
- `X-BB610-Category-SEO: biostimulation`

The generic catalog and all other categories must not have that header.
