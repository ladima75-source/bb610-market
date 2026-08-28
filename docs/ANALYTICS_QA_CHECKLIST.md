# Stage 6 activation QA checklist

Before enabling GTM in production:

1. Validate catalog SKU ids are stable and match Merchant/Meta feed ids.
2. Confirm no `0 грн` or unknown-price SKU is feed-eligible.
3. Enable analytics debug locally and verify event payloads in console/dataLayer.
4. Check `view_item_list` fires once per rendered list state intended for measurement.
5. Check `select_item` contains the SKU used by the clicked product card.
6. Check `view_item` changes with the selected variant/SKU.
7. Check `add_to_cart` uses SKU + correct quantity.
8. Check `view_cart` uses current cart contents.
9. Check `begin_checkout` fires on checkout page entry, not twice from cart + checkout.
10. Check `purchase` cannot fire without backend-confirmed order status.
11. Reload success page and verify purchase is not emitted again in the same browser.
12. Confirm no PII exists in any dataLayer ecommerce event.
13. Test consent defaults and consent update before production tag publication.
14. Validate GTM Preview → GA4 DebugView.
15. Validate Google Ads conversion only after real conversion ID/label is configured.
16. Validate Meta Pixel browser event and later CAPI event share compatible `event_id` for deduplication.
17. Verify mobile funnel: ad landing → product → cart → checkout → success.
