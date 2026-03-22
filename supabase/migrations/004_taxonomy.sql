-- Taxonomy hierarchy (Dept > Cat > Class > Subclass)
CREATE TABLE taxonomy_nodes (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  parent_id       UUID REFERENCES taxonomy_nodes(id),
  level           TEXT NOT NULL CHECK (level IN ('department','category','class','subclass')),
  code            TEXT NOT NULL UNIQUE,
  name            TEXT NOT NULL,
  full_path       TEXT NOT NULL,
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Add FK to prompt_templates
ALTER TABLE prompt_templates ADD CONSTRAINT fk_prompt_taxonomy
  FOREIGN KEY (taxonomy_node_id) REFERENCES taxonomy_nodes(id);

-- Client-specific labels for taxonomy nodes
CREATE TABLE taxonomy_client_labels (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  taxonomy_node_id UUID NOT NULL REFERENCES taxonomy_nodes(id),
  client_id        UUID NOT NULL REFERENCES clients(id),
  client_name      TEXT NOT NULL,
  client_code      TEXT,
  UNIQUE(taxonomy_node_id, client_id)
);

-- Per-class attribute definitions (Iksula normalised structure)
CREATE TABLE iksula_class_attributes (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  taxonomy_node_id UUID NOT NULL REFERENCES taxonomy_nodes(id),
  attribute_code   TEXT NOT NULL,
  attribute_name   TEXT NOT NULL,
  attribute_group  TEXT,
  data_type        TEXT NOT NULL CHECK (data_type IN (
                     'text','integer','decimal','boolean','enum','multi_enum',
                     'measurement','url','date'
                   )),
  unit             TEXT,
  is_mandatory     BOOLEAN DEFAULT false,
  is_searchable    BOOLEAN DEFAULT true,
  display_order    INT DEFAULT 0,
  description      TEXT,
  validation_rule  JSONB,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE(taxonomy_node_id, attribute_code)
);

CREATE INDEX idx_ica_taxonomy ON iksula_class_attributes(taxonomy_node_id);

-- Allowed/picklist values per attribute
CREATE TABLE iksula_allowed_values (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  attribute_id    UUID NOT NULL REFERENCES iksula_class_attributes(id),
  value_code      TEXT NOT NULL,
  value_label     TEXT NOT NULL,
  synonyms        TEXT[],
  sort_order      INT DEFAULT 0,
  is_active       BOOLEAN DEFAULT true,
  UNIQUE(attribute_id, value_code)
);
