PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS order_payments (
  order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
  method TEXT NOT NULL,
  provider TEXT,
  status TEXT NOT NULL,
  amount REAL NOT NULL,
  currency TEXT NOT NULL DEFAULT 'UAH',
  provider_payment_id TEXT,
  checkout_url TEXT,
  paid_at TEXT,
  refunded_at TEXT,
  last_event_at TEXT,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS payment_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  provider TEXT,
  provider_event_id TEXT,
  event_type TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT,
  payload_json TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(provider, provider_event_id)
);

CREATE INDEX IF NOT EXISTS idx_payment_status ON order_payments(status);
CREATE INDEX IF NOT EXISTS idx_payment_provider_id ON order_payments(provider,provider_payment_id);
CREATE INDEX IF NOT EXISTS idx_payment_events_order ON payment_events(order_id,created_at);
