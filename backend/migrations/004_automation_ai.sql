PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS commerce_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL,
  aggregate_type TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  source TEXT NOT NULL DEFAULT 'system',
  created_at TEXT NOT NULL,
  processed_at TEXT
);

CREATE TABLE IF NOT EXISTS automation_rules (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  event_type TEXT NOT NULL,
  mode TEXT NOT NULL CHECK(mode IN ('auto','ai_prepare','human_approval')),
  action_type TEXT NOT NULL,
  action_json TEXT NOT NULL DEFAULT '{}',
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_jobs (
  id TEXT PRIMARY KEY,
  job_type TEXT NOT NULL,
  event_id TEXT REFERENCES commerce_events(event_id) ON DELETE SET NULL,
  aggregate_type TEXT,
  aggregate_id TEXT,
  context_scope TEXT NOT NULL DEFAULT 'minimal_no_pii',
  input_json TEXT NOT NULL DEFAULT '{}',
  output_json TEXT,
  status TEXT NOT NULL CHECK(status IN ('queued','blocked','running','completed','failed','cancelled')),
  provider TEXT,
  model TEXT,
  requires_approval INTEGER NOT NULL DEFAULT 1,
  error TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS approval_requests (
  id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_id TEXT,
  action_type TEXT NOT NULL,
  risk_level TEXT NOT NULL CHECK(risk_level IN ('low','medium','high')),
  title TEXT NOT NULL,
  summary TEXT,
  payload_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','expired','cancelled')),
  requested_at TEXT NOT NULL,
  decided_at TEXT,
  decided_by TEXT,
  decision_note TEXT
);

CREATE TABLE IF NOT EXISTS automation_audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  event_id TEXT,
  details_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_commerce_events_type_time ON commerce_events(event_type,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_commerce_events_aggregate ON commerce_events(aggregate_type,aggregate_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_status_time ON ai_jobs(status,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_status_time ON approval_requests(status,requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_audit_time ON automation_audit_log(created_at DESC);

INSERT OR IGNORE INTO automation_rules(id,name,event_type,mode,action_type,action_json,enabled,created_at,updated_at)
VALUES
('rule-order-triage','AI: короткий розбір нового замовлення','order.created','ai_prepare','agent_job','{"job_type":"order_triage","context_scope":"order_summary_no_pii","requires_approval":1}',1,datetime('now'),datetime('now')),
('rule-payment-paid-audit','Аудит підтвердженої оплати','payment.paid','auto','audit_only','{"action":"payment_confirmed"}',1,datetime('now'),datetime('now')),
('rule-order-cancel-approval','Контроль скасування замовлення','order.cancel_requested','human_approval','approval_request','{"action_type":"order_cancel","risk_level":"high","title":"Скасування замовлення потребує підтвердження"}',1,datetime('now'),datetime('now'));
