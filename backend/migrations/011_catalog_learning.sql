CREATE TABLE IF NOT EXISTS catalog_behavior_events (
  event_id TEXT NOT NULL,
  event_name TEXT NOT NULL,
  product_id TEXT NOT NULL,
  sku TEXT NOT NULL DEFAULT '',
  quantity INTEGER NOT NULL DEFAULT 1,
  value REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(event_id,event_name,product_id,sku)
);

CREATE INDEX IF NOT EXISTS idx_catalog_behavior_created
  ON catalog_behavior_events(created_at);
CREATE INDEX IF NOT EXISTS idx_catalog_behavior_product
  ON catalog_behavior_events(product_id,event_name,created_at);

CREATE TABLE IF NOT EXISTS sku_costs (
  sku TEXT PRIMARY KEY,
  unit_cost REAL NOT NULL CHECK(unit_cost >= 0),
  currency TEXT NOT NULL DEFAULT 'UAH',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
