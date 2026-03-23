-- Batch uploads
CREATE TABLE batches (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id        UUID NOT NULL REFERENCES clients(id),
  supplier_template_id UUID REFERENCES supplier_templates(id),
  file_name        TEXT NOT NULL,
  file_path        TEXT NOT NULL,
  file_type        TEXT NOT NULL CHECK (file_type IN ('pdf','csv','xlsx','image','api_feed')),
  item_count       INT,
  processed_count  INT DEFAULT 0,
  status           TEXT DEFAULT 'queued' CHECK (status IN ('queued','processing','complete','failed')),
  error_message    TEXT,
  created_by       UUID REFERENCES users(id),
  created_at       TIMESTAMPTZ DEFAULT now(),
  completed_at     TIMESTAMPTZ
);

-- Master product record
CREATE TABLE products (
  id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  batch_id            UUID REFERENCES batches(id),
  client_id           UUID NOT NULL REFERENCES clients(id),
  taxonomy_node_id    UUID REFERENCES taxonomy_nodes(id),
  supplier_template_id UUID REFERENCES supplier_templates(id),
  product_name        TEXT,
  model_number        TEXT,
  sku                 TEXT,
  upc                 TEXT,
  ean                 TEXT,
  brand               TEXT,
  supplier_name       TEXT,
  current_stage       INT DEFAULT 1,
  status              TEXT DEFAULT 'draft' CHECK (status IN (
                        'draft','processing','review','published','rejected'
                      )),
  pipeline_config_id  UUID REFERENCES pipeline_configs(id),
  product_title       TEXT,
  short_description   TEXT,
  long_description    TEXT,
  overall_confidence  FLOAT,
  completeness_pct    FLOAT,
  stage_metadata      JSONB DEFAULT '{}',
  dq_results          JSONB DEFAULT '{}',
  created_at          TIMESTAMPTZ DEFAULT now(),
  updated_at          TIMESTAMPTZ DEFAULT now(),
  published_at        TIMESTAMPTZ
);

CREATE INDEX idx_products_client ON products(client_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_batch ON products(batch_id);
CREATE INDEX idx_products_taxonomy ON products(taxonomy_node_id);

-- Layer 0: Raw supplier values (immutable)
CREATE TABLE product_raw_values (
  id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id           UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  supplier_template_id UUID REFERENCES supplier_templates(id),
  supplier_field_name  TEXT NOT NULL,
  raw_value            TEXT,
  source               TEXT NOT NULL CHECK (source IN (
                         'ocr','vision','csv','web_google','web_marketplace','api','manual'
                       )),
  source_url           TEXT,
  source_page_ref      TEXT,
  source_cell_ref      TEXT,
  extraction_model     TEXT,
  extraction_confidence FLOAT,
  mapped_to_attribute_id UUID REFERENCES iksula_class_attributes(id),
  mapping_id           UUID REFERENCES supplier_field_mappings(id),
  extracted_at         TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_prv_product ON product_raw_values(product_id);
CREATE INDEX idx_prv_unmapped ON product_raw_values(mapped_to_attribute_id)
  WHERE mapped_to_attribute_id IS NULL;

-- Layer 1: Iksula normalised values
CREATE TABLE product_iksula_values (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id        UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  attribute_id      UUID NOT NULL REFERENCES iksula_class_attributes(id),
  value_text        TEXT,
  value_numeric     DECIMAL,
  value_boolean     BOOLEAN,
  value_array       TEXT[],
  source            TEXT NOT NULL CHECK (source IN (
                      'raw_normalised','kb','llm','vision',
                      'web_google','web_marketplace','human','dq_override'
                    )),
  source_raw_value_ids UUID[],
  model_name        TEXT,
  prompt_template   TEXT,
  raw_extracted     TEXT,
  confidence        FLOAT DEFAULT 0,
  confidence_breakdown JSONB,
  all_sources       JSONB,
  sources_agree     BOOLEAN,
  agreement_count   INT DEFAULT 1,
  review_status     TEXT DEFAULT 'pending' CHECK (review_status IN (
                      'pending','auto_approved','needs_review','low_confidence',
                      'human_approved','human_edited','rejected','dq_override'
                    )),
  set_at_stage      INT NOT NULL,
  updated_at_stage  INT,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now(),
  UNIQUE(product_id, attribute_id)
);

CREATE INDEX idx_piv_product ON product_iksula_values(product_id);
CREATE INDEX idx_piv_review ON product_iksula_values(review_status);
CREATE INDEX idx_piv_confidence ON product_iksula_values(confidence);

-- Layer 2: Client normalised values (transformed output)
CREATE TABLE product_client_values (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id        UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  client_id         UUID NOT NULL REFERENCES clients(id),
  template_id       UUID NOT NULL REFERENCES retailer_templates(id),
  field_mapping_id  UUID NOT NULL REFERENCES client_field_mappings(id),
  client_field_name TEXT NOT NULL,
  client_value      TEXT NOT NULL,
  iksula_attribute_id UUID REFERENCES iksula_class_attributes(id),
  iksula_raw_value  TEXT,
  transform_applied TEXT,
  review_status     TEXT DEFAULT 'auto' CHECK (review_status IN (
                      'auto','human_approved','human_edited','rejected'
                    )),
  edited_value      TEXT,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now(),
  UNIQUE(product_id, client_id, field_mapping_id)
);

CREATE INDEX idx_pcv_product ON product_client_values(product_id);
CREATE INDEX idx_pcv_client ON product_client_values(client_id);
