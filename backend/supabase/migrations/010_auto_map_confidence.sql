-- Add AI auto-mapping confidence column to client_field_mappings
ALTER TABLE client_field_mappings ADD COLUMN IF NOT EXISTS auto_map_confidence FLOAT;
