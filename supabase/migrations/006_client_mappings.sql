-- Maps Iksula attributes to client-specific field names (Layer 1 → Layer 2)
CREATE TABLE client_field_mappings (
  id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id           UUID NOT NULL REFERENCES clients(id),
  template_id         UUID NOT NULL REFERENCES retailer_templates(id),
  taxonomy_node_id    UUID NOT NULL REFERENCES taxonomy_nodes(id),
  iksula_attribute_id UUID NOT NULL REFERENCES iksula_class_attributes(id),
  client_field_name   TEXT NOT NULL,
  client_field_code   TEXT NOT NULL,
  client_field_order  INT DEFAULT 0,
  is_mandatory        BOOLEAN DEFAULT false,
  char_limit          INT,
  transform_rule      JSONB NOT NULL DEFAULT '{"type":"direct"}',
  mapping_status      TEXT DEFAULT 'auto' CHECK (mapping_status IN (
                        'auto','manual','corrected','unmapped'
                      )),
  mapped_by           UUID REFERENCES users(id),
  mapped_at           TIMESTAMPTZ,
  created_at          TIMESTAMPTZ DEFAULT now(),
  updated_at          TIMESTAMPTZ DEFAULT now(),
  UNIQUE(template_id, taxonomy_node_id, iksula_attribute_id)
);

CREATE INDEX idx_cfm_template ON client_field_mappings(template_id);
CREATE INDEX idx_cfm_taxonomy ON client_field_mappings(taxonomy_node_id);
CREATE INDEX idx_cfm_status ON client_field_mappings(mapping_status);

-- Maps Iksula enum values to client-specific values
CREATE TABLE client_value_mappings (
  id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_field_mapping_id UUID NOT NULL REFERENCES client_field_mappings(id),
  iksula_value_code       TEXT NOT NULL,
  iksula_value_label      TEXT NOT NULL,
  client_value            TEXT NOT NULL,
  mapping_status          TEXT DEFAULT 'auto' CHECK (mapping_status IN ('auto','manual','corrected')),
  mapped_by               UUID REFERENCES users(id),
  mapped_at               TIMESTAMPTZ,
  created_at              TIMESTAMPTZ DEFAULT now(),
  UNIQUE(client_field_mapping_id, iksula_value_code)
);
