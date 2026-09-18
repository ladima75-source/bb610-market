CREATE TABLE IF NOT EXISTS price_request_notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_code TEXT NOT NULL,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  error TEXT,
  provider_message_id TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_attempt_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(request_code, channel)
);

CREATE INDEX IF NOT EXISTS idx_price_request_notifications_status
  ON price_request_notifications(status);

CREATE INDEX IF NOT EXISTS idx_price_request_notifications_request_code
  ON price_request_notifications(request_code);
