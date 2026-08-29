PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS order_delivery (
  order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
  provider TEXT,
  service TEXT,
  city TEXT,
  city_ref TEXT,
  branch TEXT,
  branch_ref TEXT,
  postal_code TEXT,
  address_line TEXT,
  recipient_name TEXT,
  recipient_phone TEXT,
  quoted_price REAL,
  quoted_currency TEXT DEFAULT 'UAH',
  quote_source TEXT,
  quote_created_at TEXT,
  tracking_number TEXT,
  carrier_shipment_ref TEXT,
  carrier_status TEXT,
  carrier_status_text TEXT,
  last_tracking_at TEXT,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS delivery_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  event_type TEXT NOT NULL,
  carrier_status TEXT,
  message TEXT,
  payload_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_delivery_tracking ON order_delivery(tracking_number);
CREATE INDEX IF NOT EXISTS idx_delivery_provider ON order_delivery(provider);
CREATE INDEX IF NOT EXISTS idx_delivery_events_order ON delivery_events(order_id,created_at);
