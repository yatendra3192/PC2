-- Supplier data format definitions
CREATE TABLE supplier_templates (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  supplier_name    TEXT NOT NULL,
  supplier_code    TEXT NOT NULL,
  format_type      TEXT NOT NULL CHECK (format_type IN ('csv','xlsx','pdf','api','web')),
  template_name    TEXT NOT NULL,
  version          TEXT DEFAULT '1.0',
  field_definitions JSONB NOT NULL DEFAULT '[]',
  is_active        BOOLEAN DEFAULT true,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE(supplier_code, version)
);

-- Maps supplier fields to Iksula attributes (Layer 0 → Layer 1)
CREATE TABLE supplier_field_mappings (
  id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  supplier_template_id UUID NOT NULL REFERENCES supplier_templates(id),
  taxonomy_node_id     UUID REFERENCES taxonomy_nodes(id),
  supplier_field_name  TEXT NOT NULL,
  supplier_field_alias TEXT[],
  iksula_attribute_id  UUID REFERENCES iksula_class_attributes(id),
  normalise_rule       JSONB,
  mapping_status       TEXT DEFAULT 'auto' CHECK (mapping_status IN (
                         'auto','manual','corrected','unmapped','ignored'
                       )),
  mapped_by            UUID REFERENCES users(id),
  mapped_at            TIMESTAMPTZ,
  auto_map_confidence  FLOAT,
  created_at           TIMESTAMPTZ DEFAULT now(),
  updated_at           TIMESTAMPTZ DEFAULT now(),
  UNIQUE(supplier_template_id, supplier_field_name, taxonomy_node_id)
);

CREATE INDEX idx_sfm_template ON supplier_field_mappings(supplier_template_id);
CREATE INDEX idx_sfm_status ON supplier_field_mappings(mapping_status);
