CREATE TABLE IF NOT EXISTS sku_commerce (
  sku TEXT PRIMARY KEY,
  price REAL,
  sale_price REAL,
  availability TEXT NOT NULL DEFAULT 'unknown',
  stock_qty INTEGER,
  enabled INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sku_commerce_enabled ON sku_commerce(enabled);
