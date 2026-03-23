-- Clients (retailers)
CREATE TABLE clients (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name            TEXT NOT NULL,
  code            TEXT NOT NULL UNIQUE,
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Users
CREATE TABLE users (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email           TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,
  full_name       TEXT,
  role            TEXT NOT NULL CHECK (role IN ('admin','reviewer','viewer')),
  client_id       UUID REFERENCES clients(id),
  is_active       BOOLEAN DEFAULT true,
  last_active_at  TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
