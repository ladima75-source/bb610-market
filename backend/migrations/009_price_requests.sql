CREATE TABLE IF NOT EXISTS price_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_code TEXT NOT NULL UNIQUE,
  product_id TEXT NOT NULL,
  sku TEXT NOT NULL,
  product_name TEXT NOT NULL,
  variant TEXT,
  quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity >= 1),
  customer_name TEXT NOT NULL,
  contact TEXT NOT NULL,
  comment TEXT,
  source_url TEXT,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_price_requests_created_at
  ON price_requests(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_price_requests_sku
  ON price_requests(sku);

CREATE INDEX IF NOT EXISTS idx_price_requests_status
  ON price_requests(status);
