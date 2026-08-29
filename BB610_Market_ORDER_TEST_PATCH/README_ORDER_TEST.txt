BB610 Market — INTERNAL ORDER TEST PATCH

Purpose:
- Adds hidden diagnostic SKU BB610-TEST-ORDER-001 (100 UAH).
- SKU is active only for checkout testing.
- Hidden product is excluded from normal catalog product lists.
- Hidden product/SKU are excluded from generated product pages and sitemap.
- feed_eligible remains false, so it is not exported to merchant/meta CSV feeds.
- /tools/ is already disallowed by robots.txt; order-test.html also has noindex,nofollow.

Upload these files to the same paths in the GitHub repository.
Then enable BB610_PAYMENT_COD_ENABLED=1 in Render Environment.
Use: https://market.bb610.com.ua/tools/order-test.html
