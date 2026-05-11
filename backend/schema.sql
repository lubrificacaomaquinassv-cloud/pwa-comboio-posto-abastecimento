CREATE TABLE IF NOT EXISTS lancamentos (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL CHECK (event_type IN ('abastecimento', 'recebimento')),
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  vehicle TEXT,
  fuel_type TEXT NOT NULL,
  liters REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lancamentos_created_at ON lancamentos (created_at);
CREATE INDEX IF NOT EXISTS idx_lancamentos_fuel_type ON lancamentos (fuel_type);
