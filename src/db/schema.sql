CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  fingerprint_hash TEXT,
  similarity_group TEXT,
  created_at INTEGER
);

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  event_type TEXT,
  latency_ms INTEGER,
  server_status TEXT,
  ip TEXT,
  country TEXT,
  user_agent TEXT,
  details TEXT,
  created_at INTEGER
);
