PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
  product_id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  brand TEXT,
  manufacturer TEXT,
  category_id TEXT NOT NULL,
  short_description TEXT,
  description TEXT,
  application TEXT,
  composition TEXT,
  benefits_json TEXT NOT NULL DEFAULT '[]',
  how_it_works TEXT,
  characteristics_json TEXT NOT NULL DEFAULT '{}',
  seo_title TEXT,
  seo_description TEXT,
  public_enabled INTEGER NOT NULL DEFAULT 1 CHECK (public_enabled IN (0,1)),
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','active','archived')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_sources (
  source_id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  source_url TEXT,
  source_label TEXT,
  verified_at TEXT,
  status TEXT NOT NULL DEFAULT 'candidate'
    CHECK (status IN ('candidate','verified','rejected')),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS skus (
  sku_id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
  manufacturer_sku TEXT,
  package_value REAL,
  package_unit TEXT,
  package_label TEXT,
  package_group TEXT
    CHECK (package_group IN ('small','medium','large') OR package_group IS NULL),
  attributes_json TEXT NOT NULL DEFAULT '{}',
  sort_order INTEGER NOT NULL DEFAULT 0,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_skus_product ON skus(product_id);
CREATE INDEX IF NOT EXISTS idx_skus_package_group ON skus(package_group);

CREATE TABLE IF NOT EXISTS media (
  media_id TEXT PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,
  sha256 TEXT,
  kind TEXT NOT NULL DEFAULT 'image',
  source_url TEXT,
  verification_status TEXT NOT NULL DEFAULT 'candidate'
    CHECK (verification_status IN ('candidate','verified','rejected')),
  alt TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_media (
  product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
  media_id TEXT NOT NULL REFERENCES media(media_id) ON DELETE CASCADE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  source_kind TEXT,
  source_url TEXT,
  PRIMARY KEY (product_id, media_id)
);

CREATE TABLE IF NOT EXISTS sku_media (
  sku_id TEXT NOT NULL REFERENCES skus(sku_id) ON DELETE CASCADE,
  media_id TEXT NOT NULL REFERENCES media(media_id) ON DELETE CASCADE,
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)),
  sort_order INTEGER NOT NULL DEFAULT 0,
  binding_kind TEXT NOT NULL DEFAULT 'exact'
    CHECK (binding_kind = 'exact'),
  source_kind TEXT,
  source_url TEXT,
  PRIMARY KEY (sku_id, media_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sku_primary_media
ON sku_media(sku_id)
WHERE is_primary = 1;

CREATE TABLE IF NOT EXISTS sku_commerce (
  sku_id TEXT PRIMARY KEY REFERENCES skus(sku_id) ON DELETE CASCADE,
  price REAL,
  sale_price REAL,
  availability TEXT,
  stock_qty REAL,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS migration_evidence (
  evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  field_name TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_ref TEXT,
  decision TEXT NOT NULL
    CHECK (decision IN ('accepted','rejected','pending')),
  note TEXT
);

CREATE INDEX IF NOT EXISTS idx_evidence_entity
ON migration_evidence(entity_type, entity_id);


CREATE TABLE IF NOT EXISTS product_aliases (
  alias TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
  alias_kind TEXT NOT NULL DEFAULT 'legacy',
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

CREATE TABLE IF NOT EXISTS sku_aliases (
  alias_sku_id TEXT PRIMARY KEY,
  canonical_sku_id TEXT NOT NULL REFERENCES skus(sku_id) ON DELETE CASCADE,
  alias_kind TEXT NOT NULL DEFAULT 'legacy',
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_product_aliases_product
ON product_aliases(product_id);

CREATE INDEX IF NOT EXISTS idx_sku_aliases_canonical
ON sku_aliases(canonical_sku_id);

CREATE TABLE IF NOT EXISTS sku_alias_commerce (
  alias_sku_id TEXT PRIMARY KEY
    REFERENCES sku_aliases(alias_sku_id) ON DELETE CASCADE,
  price REAL,
  sale_price REAL,
  availability TEXT,
  stock_qty REAL,
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0,1)),
  updated_at TEXT
);
