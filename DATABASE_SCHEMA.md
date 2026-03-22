# PC2 v2.0 — Database Schema

**Version:** 2.1
**Date:** 2026-03-22
**Status:** Draft
**Database:** Supabase (PostgreSQL 15 + pgvector)

---

## 1. Schema Design Principles

### The Core Problem

Product data arrives in any format from any supplier. It must be normalised to a canonical Iksula structure, then transformed to each retailer's specific output format. The database must preserve all three representations.

### The Three-Layer Model

```
LAYER 0: Raw Supplier Data         LAYER 1: Iksula Normalised        LAYER 2: Client Normalised
(as received — never modified)     (canonical, standardised)          (retailer output)

┌───────────────────────────┐      ┌───────────────────────────┐     ┌───────────────────────────┐
│ Supplier: Orbit CSV       │      │ Iksula Class:             │     │ SiteOne Template v2.4:    │
│                           │      │  "Smart Controllers"      │     │                           │
│ "Wt": "0.8 lbs"          │─────►│  weight_kg = 0.36         │────►│  Weight (lbs) = "0.79"    │
│ "Clr": "GRY"             │─────►│  colour = "grey"          │────►│  Product Color = "Gray"   │
│ "Op Temp": "32-122F"     │─────►│  temp_min_c = 0           │────►│  Temp Range = "32–122°F"  │
│ "# Stations": "6"        │─────►│  zones = 6                │────►│  Zone Count = "6"         │
│ "Warranty (mo)": "24"    │─────►│  warranty_months = 24     │────►│  Warranty = "2 Years"     │
│                           │      │                           │     │                           │
│ Preserved exactly as-is  │      │ Normalised via             │     │ Transformed via            │
│ for audit + re-processing│      │ supplier_field_mappings    │     │ client_field_mappings     │
└───────────────────────────┘      └───────────────────────────┘     └───────────────────────────┘

    mapping tables:                    mapping tables:
    supplier_templates                 client_field_mappings
    supplier_field_mappings            client_value_mappings
```

### Why Three Layers

| Layer | Why it exists |
|---|---|
| **Layer 0 — Raw** | Audit trail. Re-processing. Supplier data format analysis. You always need the original. Different suppliers send the same product with different field names, units, and formats. |
| **Layer 1 — Iksula** | Single source of truth. One canonical format regardless of which supplier sent it or which retailer will consume it. Class-specific attributes with controlled picklists. All enrichment, DQ, and dedup work happens here. |
| **Layer 2 — Client** | Each retailer needs data in their exact format. SiteOne wants imperial units and "Gray". THD wants metric and "GRY". The same Iksula record transforms differently for each client. |

### Why not just JSONB?

You could store everything as unstructured JSONB. But then:
- You can't enforce mandatory attributes per class
- You can't validate against picklists
- You can't auto-map between layers
- You can't query "show me all products missing weight" across 10,000 records
- You lose the mapping correction benefit (fix once, apply to all)

The structured approach costs more in schema complexity but pays back in data quality, which is the entire point of PC2.

---

## 2. Schema Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LAYER 0: RAW SUPPLIER DATA                      │
│                                                                     │
│  supplier_templates ──► supplier_field_mappings                     │
│  (supplier data structures)  (supplier field → Iksula attribute)   │
│                                                                     │
│  product_raw_values                                                 │
│  (one row per field per product — original values, original names)  │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ normalisation
┌──────────────────────────────────┴──────────────────────────────────┐
│                     LAYER 1: IKSULA NORMALISED                      │
│                                                                     │
│  taxonomy_nodes ──► iksula_class_attributes ──► iksula_allowed_vals │
│                                                                     │
│  product_iksula_values                                              │
│  (one row per attribute per product — normalised, typed, validated)  │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ transformation
┌──────────────────────────────────┴──────────────────────────────────┐
│                     LAYER 2: CLIENT NORMALISED                      │
│                                                                     │
│  client_field_mappings ──► client_value_mappings                    │
│  (Iksula attr → client field)  (Iksula value → client value)       │
│                                                                     │
│  product_client_values                                              │
│  (one row per field per product per client — retailer output)       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     SUPPORT TABLES                                   │
│  products · batches · audit_trail · product_embeddings              │
│  clients · retailer_templates · pipeline_configs · model_registry   │
│  prompt_templates · users                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Table Count: 20 tables

| Group | Count | Tables |
|---|---|---|
| Layer 0 — Raw | 3 | `supplier_templates`, `supplier_field_mappings`, `product_raw_values` |
| Layer 1 — Iksula | 4 | `taxonomy_nodes`, `iksula_class_attributes`, `iksula_allowed_values`, `product_iksula_values` |
| Layer 2 — Client | 4 | `taxonomy_client_labels`, `client_field_mappings`, `client_value_mappings`, `product_client_values` |
| Product Core | 2 | `products`, `product_embeddings` |
| Operations | 2 | `batches`, `audit_trail` |
| Config | 5 | `clients`, `retailer_templates`, `pipeline_configs`, `model_registry`, `prompt_templates` |
| Auth | 1 | `users` |

---

## 3. Layer 0 — Raw Supplier Data

### 3.1 `supplier_templates`

Defines the structure of each supplier's data format. Orbit sends a CSV with columns "Wt", "Clr", "# Stations". Rain Bird sends a PDF with different field names. This table records what each supplier's format looks like.

```sql
CREATE TABLE supplier_templates (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  supplier_name   TEXT NOT NULL,                   -- "Orbit Irrigation Products"
  supplier_code   TEXT NOT NULL,                   -- "orbit"
  format_type     TEXT NOT NULL CHECK (format_type IN ('csv','xlsx','pdf','api','web')),
  template_name   TEXT NOT NULL,                   -- "Orbit CSV Catalog 2026"
  version         TEXT DEFAULT '1.0',

  -- The supplier's field list (discovered or manually defined)
  field_definitions JSONB NOT NULL DEFAULT '[]',
  -- Example: [
  --   {"supplier_field": "Wt", "data_type": "text", "sample_value": "0.8 lbs"},
  --   {"supplier_field": "Clr", "data_type": "text", "sample_value": "GRY"},
  --   {"supplier_field": "# Stations", "data_type": "text", "sample_value": "6"},
  --   {"supplier_field": "Op Temp", "data_type": "text", "sample_value": "32-122F"}
  -- ]

  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now(),

  UNIQUE(supplier_code, version)
);
```

### 3.2 `supplier_field_mappings`

Maps a supplier's field name to an Iksula normalised attribute. This is what powers the Layer 0 → Layer 1 normalisation.

```sql
CREATE TABLE supplier_field_mappings (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  supplier_template_id UUID NOT NULL REFERENCES supplier_templates(id),
  taxonomy_node_id  UUID REFERENCES taxonomy_nodes(id),   -- Class-specific (NULL = universal)

  -- Supplier side
  supplier_field_name   TEXT NOT NULL,              -- e.g. "Wt", "Clr", "# Stations"
  supplier_field_alias  TEXT[],                     -- Alternative names: ["Weight","Wt.","Wght"]

  -- Iksula side
  iksula_attribute_id   UUID REFERENCES iksula_class_attributes(id),

  -- Normalisation rule (how to convert supplier value → Iksula value)
  normalise_rule        JSONB,
  -- Examples:
  -- {"type": "direct"}                                  → pass through
  -- {"type": "unit_convert", "from": "lbs", "to": "kg", "factor": 0.453592}
  -- {"type": "value_map", "map": {"GRY":"grey","WHT":"white","BLK":"black"}}
  -- {"type": "regex_extract", "pattern": "(\\d+)-(\\d+)F", "output": "temp_range"}
  -- {"type": "split", "delimiter": ",", "trim": true}   → for multi-value
  -- {"type": "boolean_parse", "true_values": ["Yes","Y","1","TRUE"]}

  -- Mapping status
  mapping_status    TEXT DEFAULT 'auto' CHECK (mapping_status IN (
                      'auto',          -- System auto-mapped (by name similarity or AI)
                      'manual',        -- Human manually mapped
                      'corrected',     -- Human corrected an auto-mapping
                      'unmapped',      -- No mapping — field ignored or needs attention
                      'ignored'        -- Explicitly marked as not needed
                    )),
  mapped_by         UUID REFERENCES users(id),
  mapped_at         TIMESTAMPTZ,

  -- Match confidence (for auto-mapped)
  auto_map_confidence FLOAT,                        -- How confident the auto-mapper was

  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now(),

  UNIQUE(supplier_template_id, supplier_field_name, taxonomy_node_id)
);

CREATE INDEX idx_sfm_template ON supplier_field_mappings(supplier_template_id);
CREATE INDEX idx_sfm_status ON supplier_field_mappings(mapping_status);
```

**Example: Orbit CSV → Iksula mappings**

| Supplier Field | Iksula Attribute | Normalise Rule | Status |
|---|---|---|---|
| Wt | weight_kg | `{"type":"unit_convert","from":"lbs","to":"kg","factor":0.453592}` | auto |
| Clr | colour | `{"type":"value_map","map":{"GRY":"grey","WHT":"white"}}` | corrected |
| # Stations | zones | `{"type":"regex_extract","pattern":"(\\d+)"}` | auto |
| Op Temp | operating_temp_min_c, operating_temp_max_c | `{"type":"temp_range_parse","input_unit":"F"}` | manual |
| Warranty (mo) | warranty_months | `{"type":"direct"}` | auto |
| Internal SKU | — | — | ignored |

### 3.3 `product_raw_values`

Stores the original supplier data exactly as received. One row per field per product. Never modified after initial ingestion.

```sql
CREATE TABLE product_raw_values (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id       UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  supplier_template_id UUID REFERENCES supplier_templates(id),

  -- Original supplier data
  supplier_field_name   TEXT NOT NULL,              -- "Wt", "Clr", etc.
  raw_value             TEXT,                       -- "0.8 lbs", "GRY", etc.

  -- Extraction metadata
  source           TEXT NOT NULL CHECK (source IN (
                     'ocr','vision','csv','web_google','web_marketplace',
                     'api','manual'
                   )),
  source_url       TEXT,                            -- URL if from web
  source_page_ref  TEXT,                            -- PDF page number
  source_cell_ref  TEXT,                            -- CSV row/column reference
  extraction_model TEXT,                            -- "Iksula OCR Engine v2", etc.
  extraction_confidence FLOAT,                      -- OCR/extraction confidence

  -- Which Iksula attribute this maps to (NULL if unmapped)
  mapped_to_attribute_id UUID REFERENCES iksula_class_attributes(id),
  mapping_id       UUID REFERENCES supplier_field_mappings(id),

  -- Timestamps
  extracted_at     TIMESTAMPTZ DEFAULT now(),

  -- Never updated — raw data is immutable
  CONSTRAINT raw_immutable CHECK (true)
);

CREATE INDEX idx_prv_product ON product_raw_values(product_id);
CREATE INDEX idx_prv_supplier ON product_raw_values(supplier_field_name);
CREATE INDEX idx_prv_unmapped ON product_raw_values(mapped_to_attribute_id) WHERE mapped_to_attribute_id IS NULL;
```

**Example rows for Orbit B-0624W:**

| supplier_field_name | raw_value | source | mapped_to (Iksula) |
|---|---|---|---|
| Product Name | Orbit 24V 6-Zone Smart Irrigation Controller | ocr | product_name (identity) |
| Model | B-0624W | ocr | model_number (identity) |
| Wt | 0.8 lbs | ocr | weight_kg |
| Clr | GRY | csv | colour |
| # Stations | 6 | ocr | zones |
| Op Temp | 32-122F | ocr | temp_min_c + temp_max_c |
| WiFi | Yes | ocr | wifi_enabled |
| IP | IP44 | ocr | ip_rating |
| Warranty (mo) | 24 | csv | warranty_months |
| Material | — | — | NULL (not found, will enrich) |
| — (from Google) | 0.8 lbs | web_google | weight_kg |
| — (from Amazon) | 12.8 oz | web_marketplace | weight_kg |
| — (from Vision) | Grey | vision | colour |

**Key point:** Multiple raw values can map to the same Iksula attribute. The system reconciles them in Layer 1 (multi-source agreement).

---

## 4. Layer 1 — Iksula Normalised

### 4.1 `taxonomy_nodes`

Retail taxonomy hierarchy. Shared across all clients.

```sql
CREATE TABLE taxonomy_nodes (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  parent_id       UUID REFERENCES taxonomy_nodes(id),
  level           TEXT NOT NULL CHECK (level IN ('department','category','class','subclass')),
  code            TEXT NOT NULL UNIQUE,             -- "HW-IRR-CTRL-SMART"
  name            TEXT NOT NULL,                    -- "Smart Controllers"
  full_path       TEXT NOT NULL,                    -- "Hardware & Tools > Irrigation > Controllers > Smart Controllers"
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
```

### 4.2 `iksula_class_attributes`

Defines which attributes exist for each class. This is the Iksula normalised structure definition.

```sql
CREATE TABLE iksula_class_attributes (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  taxonomy_node_id UUID NOT NULL REFERENCES taxonomy_nodes(id),
  attribute_code  TEXT NOT NULL,                    -- "voltage", "zones", "colour"
  attribute_name  TEXT NOT NULL,                    -- "Voltage", "Number of Zones"
  attribute_group TEXT,                             -- "Physical", "Electrical", "Connectivity"
  data_type       TEXT NOT NULL CHECK (data_type IN (
                    'text','integer','decimal','boolean','enum','multi_enum',
                    'measurement','url','date'
                  )),
  unit            TEXT,                             -- "V", "kg", "cm", "°C"
  is_mandatory    BOOLEAN DEFAULT false,
  is_searchable   BOOLEAN DEFAULT true,
  display_order   INT DEFAULT 0,
  description     TEXT,
  validation_rule JSONB,                            -- {"min":0,"max":240} or {"pattern":"^IP\\d{2}$"}
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now(),

  UNIQUE(taxonomy_node_id, attribute_code)
);
```

**Example: Smart Controllers class — 17 attributes**

| attribute_code | attribute_name | group | data_type | unit | mandatory |
|---|---|---|---|---|---|
| voltage | Voltage | Electrical | measurement | V | yes |
| zones | Number of Zones | Functional | integer | — | yes |
| wifi_enabled | Wi-Fi Enabled | Connectivity | boolean | — | yes |
| ip_rating | IP Rating | Physical | enum | — | yes |
| colour | Colour | Physical | enum | — | yes |
| material | Material | Physical | enum | — | yes |
| weight_kg | Weight | Physical | measurement | kg | yes |
| shipping_weight_kg | Shipping Weight | Logistics | measurement | kg | yes |
| width_cm | Width | Physical | measurement | cm | no |
| depth_cm | Depth | Physical | measurement | cm | no |
| height_cm | Height | Physical | measurement | cm | no |
| operating_temp_min_c | Operating Temp Min | Environmental | measurement | °C | yes |
| operating_temp_max_c | Operating Temp Max | Environmental | measurement | °C | yes |
| certifications | Certifications | Compliance | multi_enum | — | yes |
| compatible_valve_types | Compatible Valve Types | Functional | multi_enum | — | no |
| app_name | Connected App Name | Connectivity | text | — | no |
| warranty_months | Warranty | Commercial | integer | months | no |

### 4.3 `iksula_allowed_values`

Picklist values per attribute.

```sql
CREATE TABLE iksula_allowed_values (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  attribute_id    UUID NOT NULL REFERENCES iksula_class_attributes(id),
  value_code      TEXT NOT NULL,                    -- "grey", "abs_plastic", "ce"
  value_label     TEXT NOT NULL,                    -- "Grey", "ABS Plastic", "CE"
  synonyms        TEXT[],                           -- ["gray","gry","grau"] for matching
  sort_order      INT DEFAULT 0,
  is_active       BOOLEAN DEFAULT true,

  UNIQUE(attribute_id, value_code)
);
```

**Key feature: `synonyms` column.** When raw data says "GRY" or "Gray" or "gray", the system matches against synonyms to find the correct Iksula normalised value "grey". This powers auto-normalisation.

### 4.4 `product_iksula_values`

One row per attribute per product. The normalised, validated, enriched values.

```sql
CREATE TABLE product_iksula_values (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id       UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  attribute_id     UUID NOT NULL REFERENCES iksula_class_attributes(id),

  -- The normalised value (one of these is populated based on data_type)
  value_text       TEXT,
  value_numeric    DECIMAL,
  value_boolean    BOOLEAN,
  value_array      TEXT[],                          -- For multi_enum

  -- How this value was determined
  source           TEXT NOT NULL CHECK (source IN (
                     'raw_normalised',              -- Normalised from Layer 0 raw value
                     'kb',                          -- Iksula Knowledge Base
                     'llm',                         -- LLM inference
                     'vision',                      -- Image analysis
                     'web_google',                  -- Google scrape
                     'web_marketplace',             -- Amazon/retailer scrape
                     'human',                       -- Manual entry
                     'dq_override'                  -- Overridden after DQ check
                   )),
  source_raw_value_ids UUID[],                      -- Links back to product_raw_values rows that contributed

  -- Model / provenance
  model_name       TEXT,
  prompt_template  TEXT,
  raw_extracted    TEXT,                             -- The pre-normalisation value

  -- Confidence
  confidence       FLOAT DEFAULT 0,
  confidence_breakdown JSONB,

  -- Multi-source reconciliation
  all_sources      JSONB,                           -- [{source, value, confidence, url}, ...]
  sources_agree    BOOLEAN,
  agreement_count  INT DEFAULT 1,

  -- Review status
  review_status    TEXT DEFAULT 'pending' CHECK (review_status IN (
                     'pending','auto_approved','needs_review','low_confidence',
                     'human_approved','human_edited','rejected','dq_override'
                   )),

  -- Stage tracking
  set_at_stage     INT NOT NULL,
  updated_at_stage INT,

  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now(),

  UNIQUE(product_id, attribute_id)
);

CREATE INDEX idx_piv_product ON product_iksula_values(product_id);
CREATE INDEX idx_piv_review ON product_iksula_values(review_status);
CREATE INDEX idx_piv_confidence ON product_iksula_values(confidence);
```

---

## 5. Layer 2 — Client Normalised

### 5.1 `taxonomy_client_labels`

Client-specific names for taxonomy nodes.

```sql
CREATE TABLE taxonomy_client_labels (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  taxonomy_node_id UUID NOT NULL REFERENCES taxonomy_nodes(id),
  client_id       UUID NOT NULL REFERENCES clients(id),
  client_name     TEXT NOT NULL,
  client_code     TEXT,

  UNIQUE(taxonomy_node_id, client_id)
);
```

### 5.2 `client_field_mappings`

Maps Iksula attributes to client-specific field names + transform rules.

```sql
CREATE TABLE client_field_mappings (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id         UUID NOT NULL REFERENCES clients(id),
  template_id       UUID NOT NULL REFERENCES retailer_templates(id),
  taxonomy_node_id  UUID NOT NULL REFERENCES taxonomy_nodes(id),

  -- Iksula side
  iksula_attribute_id UUID NOT NULL REFERENCES iksula_class_attributes(id),

  -- Client side
  client_field_name   TEXT NOT NULL,
  client_field_code   TEXT NOT NULL,
  client_field_order  INT DEFAULT 0,
  is_mandatory        BOOLEAN DEFAULT false,
  char_limit          INT,

  -- Transform rule
  transform_rule      JSONB NOT NULL DEFAULT '{"type":"direct"}',
  -- Types: direct, unit_convert, lookup, boolean_format, case, duration_format,
  --        temp_range_format, concat, join, truncate, custom

  -- Mapping status
  mapping_status    TEXT DEFAULT 'auto' CHECK (mapping_status IN (
                      'auto','manual','corrected','unmapped'
                    )),
  mapped_by         UUID REFERENCES users(id),
  mapped_at         TIMESTAMPTZ,

  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now(),

  UNIQUE(template_id, taxonomy_node_id, iksula_attribute_id)
);
```

### 5.3 `client_value_mappings`

Maps Iksula enum values to client-specific values.

```sql
CREATE TABLE client_value_mappings (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_field_mapping_id UUID NOT NULL REFERENCES client_field_mappings(id),

  iksula_value_code   TEXT NOT NULL,
  iksula_value_label  TEXT NOT NULL,
  client_value        TEXT NOT NULL,

  mapping_status    TEXT DEFAULT 'auto' CHECK (mapping_status IN ('auto','manual','corrected')),
  mapped_by         UUID REFERENCES users(id),
  mapped_at         TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT now(),

  UNIQUE(client_field_mapping_id, iksula_value_code)
);

-- Example: Colour mappings
-- SiteOne: iksula "grey" → "Gray",  iksula "white" → "White"
-- THD:     iksula "grey" → "GRY",   iksula "white" → "WHT"
```

### 5.4 `product_client_values`

Transformed output. One row per field per product per client.

```sql
CREATE TABLE product_client_values (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id        UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  client_id         UUID NOT NULL REFERENCES clients(id),
  template_id       UUID NOT NULL REFERENCES retailer_templates(id),
  field_mapping_id  UUID NOT NULL REFERENCES client_field_mappings(id),

  client_field_name TEXT NOT NULL,
  client_value      TEXT NOT NULL,

  -- Traceability back to Iksula layer
  iksula_attribute_id UUID REFERENCES iksula_class_attributes(id),
  iksula_raw_value    TEXT,
  transform_applied   TEXT,

  -- Review
  review_status     TEXT DEFAULT 'auto' CHECK (review_status IN (
                      'auto','human_approved','human_edited','rejected'
                    )),
  edited_value      TEXT,

  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now(),

  UNIQUE(product_id, client_id, field_mapping_id)
);
```

---

## 6. Product Core & Support Tables

### 6.1 `products`

```sql
CREATE TABLE products (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  batch_id         UUID REFERENCES batches(id),
  client_id        UUID NOT NULL REFERENCES clients(id),
  taxonomy_node_id UUID REFERENCES taxonomy_nodes(id),
  supplier_template_id UUID REFERENCES supplier_templates(id),

  -- Identity
  product_name     TEXT,
  model_number     TEXT,
  sku              TEXT,
  upc              TEXT,
  ean              TEXT,
  brand            TEXT,
  supplier_name    TEXT,

  -- Pipeline state
  current_stage    INT DEFAULT 1,
  status           TEXT DEFAULT 'draft' CHECK (status IN (
                     'draft','processing','review','published','rejected'
                   )),
  pipeline_config_id UUID REFERENCES pipeline_configs(id),

  -- Generated content
  product_title       TEXT,
  short_description   TEXT,
  long_description    TEXT,

  -- Scores
  overall_confidence  FLOAT,
  completeness_pct    FLOAT,

  -- DQ + stage metadata
  stage_metadata   JSONB DEFAULT '{}',
  dq_results       JSONB DEFAULT '{}',

  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now(),
  published_at     TIMESTAMPTZ
);

CREATE INDEX idx_products_client ON products(client_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_batch ON products(batch_id);
CREATE INDEX idx_products_taxonomy ON products(taxonomy_node_id);
```

### 6.2 `batches`

```sql
CREATE TABLE batches (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id       UUID NOT NULL REFERENCES clients(id),
  supplier_template_id UUID REFERENCES supplier_templates(id),
  file_name       TEXT NOT NULL,
  file_path       TEXT NOT NULL,
  file_type       TEXT NOT NULL CHECK (file_type IN ('pdf','csv','xlsx','image','api_feed')),
  item_count      INT,
  processed_count INT DEFAULT 0,
  status          TEXT DEFAULT 'queued' CHECK (status IN ('queued','processing','complete','failed')),
  error_message   TEXT,
  created_by      UUID REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT now(),
  completed_at    TIMESTAMPTZ
);
```

### 6.3 `audit_trail`

```sql
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
```

### 6.4 `product_embeddings`

```sql
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
```

### 6.5 `clients`

```sql
CREATE TABLE clients (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name            TEXT NOT NULL,
  code            TEXT NOT NULL UNIQUE,
  pipeline_config_id UUID REFERENCES pipeline_configs(id),
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

### 6.6 `retailer_templates`

```sql
CREATE TABLE retailer_templates (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id       UUID NOT NULL REFERENCES clients(id),
  template_name   TEXT NOT NULL,
  version         TEXT NOT NULL,
  export_formats  TEXT[] DEFAULT '{"csv"}',
  is_active       BOOLEAN DEFAULT true,
  maintained_by   TEXT DEFAULT 'Iksula',
  last_updated    TIMESTAMPTZ DEFAULT now(),
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

### 6.7 `pipeline_configs`

```sql
CREATE TABLE pipeline_configs (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id       UUID NOT NULL REFERENCES clients(id),
  name            TEXT NOT NULL,
  stages_enabled  JSONB NOT NULL DEFAULT '{"1":true,"2":true,"3":true,"4":true,"5":true,"6":true,"7":true}',
  stage_configs   JSONB DEFAULT '{}',
  dq_config       JSONB DEFAULT '{}',
  scraper_config  JSONB DEFAULT '{}',
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
```

### 6.8 `model_registry`

```sql
CREATE TABLE model_registry (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  model_name      TEXT NOT NULL,
  model_type      TEXT NOT NULL CHECK (model_type IN ('llm','vision','ocr','embedding','classification','kb','custom')),
  provider        TEXT NOT NULL CHECK (provider IN ('iksula','openai','anthropic','google','aws','huggingface','client_custom')),
  endpoint_url    TEXT,
  api_key_ref     TEXT,
  capabilities    TEXT[],
  default_for_stages INT[],
  is_active       BOOLEAN DEFAULT true,
  added_by        TEXT DEFAULT 'iksula',
  client_id       UUID REFERENCES clients(id),
  fallback_model_id UUID REFERENCES model_registry(id),
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

### 6.9 `prompt_templates`

```sql
CREATE TABLE prompt_templates (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  template_name   TEXT NOT NULL,
  model_type      TEXT NOT NULL,
  taxonomy_node_id UUID REFERENCES taxonomy_nodes(id),
  client_id       UUID REFERENCES clients(id),
  template_text   TEXT NOT NULL,
  version         TEXT NOT NULL,
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

### 6.10 `users`

```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY REFERENCES auth.users(id),
  email           TEXT NOT NULL,
  full_name       TEXT,
  role            TEXT NOT NULL CHECK (role IN ('admin','reviewer','viewer')),
  client_id       UUID REFERENCES clients(id),
  is_active       BOOLEAN DEFAULT true,
  last_active_at  TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 7. Data Flow Through the Three Layers

### Stage 1 — Ingestion → Layer 0

```
Supplier file uploaded
    │
    ├── Detect/select supplier_template
    │
    ├── For each field extracted (OCR/CSV/Vision):
    │       INSERT INTO product_raw_values (
    │         product_id, supplier_field_name, raw_value,
    │         source, extraction_model, extraction_confidence
    │       )
    │
    └── Auto-map supplier fields to Iksula attributes:
            Look up supplier_field_mappings for this supplier_template
            For each mapped field:
                Apply normalise_rule
                INSERT INTO product_iksula_values (Layer 1)
            For unmapped fields:
                Flag for human mapping in HIL
```

### Stage 4 — Enrichment → Layer 0 + Layer 1

```
For each missing Iksula attribute:
    │
    ├── KB lookup → if found:
    │       INSERT into product_raw_values (source='kb')
    │       INSERT/UPDATE product_iksula_values (source='kb')
    │
    ├── LLM inference → if generated:
    │       INSERT into product_raw_values (source='llm')
    │       INSERT/UPDATE product_iksula_values (source='llm')
    │
    ├── Google scrape (3 URLs) → for each attribute found:
    │       INSERT into product_raw_values (source='web_google', source_url=...)
    │       Normalise value → UPDATE product_iksula_values
    │
    └── Amazon scrape (10 results) → for each attribute found:
            INSERT into product_raw_values (source='web_marketplace', source_url=...)
            Normalise value → UPDATE product_iksula_values

Multi-source reconciliation:
    If 2+ raw values map to same Iksula attribute:
        Compare values → update agreement_count, sources_agree
        Select highest-confidence value as primary
```

### Stage 6 — Transformation → Layer 2

```
For each product being transformed:
    │
    ├── Get all product_iksula_values for this product
    │
    ├── Get client_field_mappings for this class + client template
    │
    ├── For each mapping:
    │       Apply transform_rule:
    │         direct     → pass through
    │         unit_convert → multiply by factor
    │         lookup     → look up client_value_mappings
    │         case       → apply title/upper/lower case
    │         duration   → "24 months" → "2 Years"
    │         concat     → combine multiple fields
    │         ...
    │
    │       INSERT INTO product_client_values (
    │         client_field_name, client_value,
    │         iksula_raw_value, transform_applied
    │       )
    │
    └── Flag unmapped attributes for human mapping
```

---

## 8. Mapping Correction Flows

### Correcting a supplier → Iksula mapping

A reviewer sees that Orbit's "# Stations" field was not auto-mapped. They map it to `zones`:

```sql
-- Correct the mapping
UPDATE supplier_field_mappings
SET
  iksula_attribute_id = (SELECT id FROM iksula_class_attributes WHERE attribute_code = 'zones'),
  normalise_rule = '{"type":"regex_extract","pattern":"(\\d+)"}',
  mapping_status = 'corrected',
  mapped_by = 'reviewer-uuid',
  mapped_at = now()
WHERE supplier_template_id = 'orbit-csv-uuid'
  AND supplier_field_name = '# Stations';

-- Re-normalise all existing products from this supplier
-- (triggered automatically or manually by admin)
```

### Correcting an Iksula → Client mapping

A reviewer sees that SiteOne's "Valve Compatibility" field was unmapped:

```sql
UPDATE client_field_mappings
SET
  client_field_name = 'Valve Compatibility',
  client_field_code = 'valve_compat',
  transform_rule = '{"type":"join","separator":", ","use_labels":true}',
  mapping_status = 'corrected',
  mapped_by = 'reviewer-uuid',
  mapped_at = now()
WHERE template_id = 'siteone-v2.4-uuid'
  AND iksula_attribute_id = (SELECT id FROM iksula_class_attributes WHERE attribute_code = 'compatible_valve_types');

-- Re-transform all products in this class for SiteOne
```

### Correcting a value mapping

SiteOne wants "Grey" spelled as "Gray":

```sql
INSERT INTO client_value_mappings (
  client_field_mapping_id, iksula_value_code, iksula_value_label,
  client_value, mapping_status, mapped_by, mapped_at
) VALUES (
  'colour-mapping-uuid', 'grey', 'Grey',
  'Gray', 'corrected', 'reviewer-uuid', now()
);
```

All corrections are logged in `audit_trail` with `layer='mapping'` and `action='mapping_corrected'`.

---

## 9. Key Queries

### All three layers for a single product

```sql
-- Layer 0: Raw
SELECT supplier_field_name, raw_value, source, extraction_confidence
FROM product_raw_values WHERE product_id = 'orbit-001'
ORDER BY extracted_at;

-- Layer 1: Iksula Normalised
SELECT ica.attribute_name, ica.attribute_code, ica.unit,
       COALESCE(piv.value_text, piv.value_numeric::text, piv.value_boolean::text) as value,
       piv.source, piv.confidence, piv.review_status, piv.agreement_count
FROM product_iksula_values piv
JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
WHERE piv.product_id = 'orbit-001'
ORDER BY ica.display_order;

-- Layer 2: Client (SiteOne)
SELECT client_field_name,
       COALESCE(edited_value, client_value) as final_value,
       iksula_raw_value, transform_applied, review_status
FROM product_client_values
WHERE product_id = 'orbit-001' AND client_id = 'siteone-uuid'
ORDER BY (SELECT client_field_order FROM client_field_mappings WHERE id = field_mapping_id);
```

### Unmapped supplier fields across all products

```sql
SELECT st.supplier_name, prv.supplier_field_name,
       COUNT(DISTINCT prv.product_id) as products_affected,
       array_agg(DISTINCT prv.raw_value) as sample_values
FROM product_raw_values prv
JOIN supplier_templates st ON prv.supplier_template_id = st.id
WHERE prv.mapped_to_attribute_id IS NULL
GROUP BY st.supplier_name, prv.supplier_field_name
ORDER BY products_affected DESC;
```

### HIL review queue across all layers

```sql
-- Unmapped raw fields (Layer 0)
SELECT 'raw_unmapped' as issue, prv.supplier_field_name as field,
       prv.raw_value as value, NULL as confidence, p.product_name
FROM product_raw_values prv JOIN products p ON prv.product_id = p.id
WHERE prv.mapped_to_attribute_id IS NULL AND p.status != 'published'

UNION ALL

-- Low confidence Iksula values (Layer 1)
SELECT 'low_confidence', ica.attribute_name, piv.value_text,
       piv.confidence, p.product_name
FROM product_iksula_values piv
JOIN iksula_class_attributes ica ON piv.attribute_id = ica.id
JOIN products p ON piv.product_id = p.id
WHERE piv.review_status IN ('needs_review','low_confidence') AND p.status != 'published'

UNION ALL

-- Unmapped client fields (Layer 2)
SELECT 'unmapped_client', ica.attribute_name, NULL, NULL, NULL
FROM iksula_class_attributes ica
LEFT JOIN client_field_mappings cfm ON ica.id = cfm.iksula_attribute_id AND cfm.template_id = 'siteone-v2.4-uuid'
WHERE cfm.id IS NULL AND ica.is_mandatory = true

ORDER BY confidence ASC NULLS FIRST;
```

---

## 10. Entity Relationship Diagram

```
supplier_templates
  │
  ├──► supplier_field_mappings (1:many — field maps per supplier)
  │       └──► iksula_class_attributes (many:1 — target attribute)
  │
  └──► product_raw_values (1:many — raw data per product)
          └──► products (many:1)

taxonomy_nodes
  │
  ├──► iksula_class_attributes (1:many — attrs per class)
  │       │
  │       ├──► iksula_allowed_values (1:many — picklist per attr)
  │       │
  │       ├──► product_iksula_values (1:many — normalised values per product)
  │       │       └──► products (many:1)
  │       │
  │       ├──► supplier_field_mappings (1:many — supplier→Iksula maps)
  │       │
  │       └──► client_field_mappings (1:many — Iksula→client maps)
  │               │
  │               ├──► client_value_mappings (1:many — value translations)
  │               │
  │               └──► product_client_values (1:many — transformed output)
  │
  └──► taxonomy_client_labels (1:many — client names)

products
  ├──► product_raw_values (1:many, Layer 0)
  ├──► product_iksula_values (1:many, Layer 1)
  ├──► product_client_values (1:many, Layer 2)
  ├──► product_embeddings (1:many)
  ├──► audit_trail (1:many)
  ├──► batches (many:1)
  └──► clients (many:1)
```

---

*Document generated: 2026-03-22*
*PC2 v2.0 Database Schema v2.1 — Three-Layer Model — Draft*
