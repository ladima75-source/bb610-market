# BB610 Product Master V5

Clean catalog rebuilt in parallel with the current production system.

Core rules:
- preserve stable SKU IDs;
- migrate commerce by exact SKU ID;
- keep only sourced or explicitly accepted content;
- store package value/unit structurally;
- bind media explicitly to product or SKU;
- never infer SKU media from package text at runtime;
- generated JS/HTML/feeds are outputs, not data sources.

Required migration gates for every product:
IDENTITY -> SKU -> CONTENT -> MEDIA -> COMMERCE

The current production catalog remains unchanged until shadow comparison and cutover.
