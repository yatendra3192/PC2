-- Pipeline configurations
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

-- Add pipeline_config reference to clients
ALTER TABLE clients ADD COLUMN pipeline_config_id UUID REFERENCES pipeline_configs(id);

-- Model registry
CREATE TABLE model_registry (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  model_name        TEXT NOT NULL,
  model_type        TEXT NOT NULL CHECK (model_type IN ('llm','vision','ocr','embedding','classification','kb','custom')),
  provider          TEXT NOT NULL CHECK (provider IN ('iksula','openai','anthropic','google','aws','huggingface','client_custom')),
  endpoint_url      TEXT,
  api_key_ref       TEXT,
  capabilities      TEXT[],
  default_for_stages INT[],
  is_active         BOOLEAN DEFAULT true,
  added_by          TEXT DEFAULT 'iksula',
  client_id         UUID REFERENCES clients(id),
  fallback_model_id UUID REFERENCES model_registry(id),
  created_at        TIMESTAMPTZ DEFAULT now()
);

-- Retailer templates
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

-- Prompt templates
CREATE TABLE prompt_templates (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  template_name   TEXT NOT NULL,
  model_type      TEXT NOT NULL,
  taxonomy_node_id UUID,  -- FK added after taxonomy_nodes created
  client_id       UUID REFERENCES clients(id),
  template_text   TEXT NOT NULL,
  version         TEXT NOT NULL,
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now()
);
