# BB610 MARKET — GTM / GA4 / Google Ads / Meta event map

| Site event | GA4 | Google Ads | Meta browser | Notes |
|---|---|---|---|---|
| view_item_list | view_item_list | remarketing audience signal | optional custom/list signal | SKU-based items |
| select_item | select_item | optional | optional | product selection from list |
| view_item | view_item | dynamic remarketing | ViewContent | use same item_id as feed |
| add_to_cart | add_to_cart | dynamic remarketing | AddToCart | value only if known |
| remove_from_cart | remove_from_cart | optional | optional custom | value only if known |
| view_cart | view_cart | remarketing | optional | cart contents |
| begin_checkout | begin_checkout | funnel/audience | InitiateCheckout | emitted on checkout entry |
| purchase | purchase | conversion | Purchase | backend-confirmed only |
| search | search | audience | Search | no PII |

## Purchase mapping
`transaction_id` is mandatory and must be unique.
`event_id` should be supplied by the backend (or deterministically derived from transaction id) so a later Meta CAPI Purchase can deduplicate against browser Purchase.

## Privacy rule
Never push name, phone, email, delivery address, comment, public order token or payment credentials to the browser dataLayer.
