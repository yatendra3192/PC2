-- Vector embeddings for deduplication
CREATE TABLE product_embeddings (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  embedding       VECTOR(1536),
  embedding_model TEXT NOT NULL,
  text_source     TEXT,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_embed_vector ON product_embeddings
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Audit trail (append-only)
CREATE TABLE audit_trail (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id      UUID REFERENCES products(id),
  layer           TEXT CHECK (layer IN ('raw','iksula','client','mapping','config')),
  field_name      TEXT,
  stage           INT,
  action          TEXT NOT NULL CHECK (action IN (
                    'extracted','normalised','enriched','validated','transformed',
                    'approved','edited','rejected','dq_passed','dq_failed',
                    'dq_overridden','mapping_created','mapping_corrected',
                    'value_mapping_corrected','published'
                  )),
  old_value       TEXT,
  new_value       TEXT,
  actor_type      TEXT NOT NULL CHECK (actor_type IN ('system','model','human')),
  actor_id        TEXT,
  model_name      TEXT,
  confidence      FLOAT,
  reason          TEXT,
  metadata        JSONB,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_product ON audit_trail(product_id);
CREATE INDEX idx_audit_layer ON audit_trail(layer);
CREATE INDEX idx_audit_action ON audit_trail(action);
CREATE INDEX idx_audit_created ON audit_trail(created_at);
