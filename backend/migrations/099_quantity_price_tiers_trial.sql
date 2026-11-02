CREATE TABLE IF NOT EXISTS quantity_price_tiers (
  sku TEXT NOT NULL,
  min_qty INTEGER NOT NULL CHECK(min_qty >= 1),
  max_qty INTEGER,
  unit_price REAL NOT NULL CHECK(unit_price >= 0),
  currency TEXT NOT NULL DEFAULT 'UAH',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (sku, min_qty)
);

CREATE INDEX IF NOT EXISTS idx_quantity_price_tiers_lookup
  ON quantity_price_tiers(sku, active, min_qty, max_qty);

INSERT OR IGNORE INTO quantity_price_tiers(
  sku,min_qty,max_qty,unit_price,currency,active,created_at,updated_at
) VALUES
  ('PL-1306010-BK',1,299,110,'UAH',1,'2026-11-02T00:00:00Z','2026-11-02T00:00:00Z'),
  ('PL-1306010-BK',300,2999,96,'UAH',1,'2026-11-02T00:00:00Z','2026-11-02T00:00:00Z'),
  ('PL-1306010-BK',3000,NULL,83,'UAH',1,'2026-11-02T00:00:00Z','2026-11-02T00:00:00Z');

UPDATE sku_commerce
SET price=110,
    sale_price=NULL,
    availability='preorder',
    enabled=1,
    updated_at='2026-11-02T00:00:00Z'
WHERE sku='PL-1306010-BK'
  AND price IS NULL
  AND availability='request_price';
