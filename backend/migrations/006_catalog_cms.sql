CREATE TABLE IF NOT EXISTS product_content (
  product_id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  content_json TEXT NOT NULL,
  published INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_product_content_published ON product_content(published);

CREATE TABLE IF NOT EXISTS dynamic_skus (
  sku TEXT PRIMARY KEY,
  product_id TEXT NOT NULL,
  variant TEXT NOT NULL,
  volume_value REAL,
  volume_unit TEXT,
  image TEXT,
  currency TEXT NOT NULL DEFAULT 'UAH',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(product_id) REFERENCES product_content(product_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_dynamic_skus_product ON dynamic_skus(product_id);
