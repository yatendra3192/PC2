-- ============================================================
-- PC2 v2.0 DEMO SEED DATA (idempotent — safe to re-run)
-- ============================================================

-- CLIENTS
INSERT INTO clients (id, name, code) VALUES
  ('11111111-1111-1111-1111-111111111111', 'SiteOne Landscape Supply', 'siteone'),
  ('11111111-1111-1111-1111-222222222222', 'The Home Depot', 'thd')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name;

-- USERS (password: "demo123")
INSERT INTO users (id, email, password_hash, full_name, role, client_id) VALUES
  ('22222222-2222-2222-2222-222222222222', 'reviewer@iksula.com',
   '$2b$12$LJ3m4ys4I3OxKBGqGMu.8eQrYzE7m5l3v5u8V6kF9W7wDmO7x3Mq6',
   'Sarah R.', 'reviewer', '11111111-1111-1111-1111-111111111111'),
  ('22222222-2222-2222-2222-333333333333', 'viewer@siteone.com',
   '$2b$12$LJ3m4ys4I3OxKBGqGMu.8eQrYzE7m5l3v5u8V6kF9W7wDmO7x3Mq6',
   'Mike J.', 'viewer', '11111111-1111-1111-1111-111111111111')
ON CONFLICT (email) DO NOTHING;

-- PIPELINE CONFIGS
INSERT INTO pipeline_configs (id, client_id, name, stages_enabled, stage_configs) VALUES
  ('44444444-4444-4444-4444-111111111111', '11111111-1111-1111-1111-111111111111',
   'SiteOne Full Pipeline',
   '{"1":true,"2":true,"3":true,"4":true,"5":true,"6":true,"7":true}',
   '{
     "1": {"confidence": {"auto_approve_threshold": 90, "needs_review_threshold": 65}},
     "2": {"confidence": {"auto_approve_threshold": 85, "needs_review_threshold": 60}},
     "3": {"confidence": {"new_item_threshold": 30, "variant_threshold": 60, "duplicate_threshold": 85}},
     "4": {"confidence": {"auto_approve_threshold": 85, "needs_review_threshold": 60}},
     "5": {"confidence": {"block_on_failure": true}},
     "6": {"confidence": {"auto_approve_threshold": 90, "needs_review_threshold": 70}},
     "7": {}
   }'),
  ('44444444-4444-4444-4444-222222222222', '11111111-1111-1111-1111-222222222222',
   'THD Pipeline (no dedup)',
   '{"1":true,"2":true,"3":false,"4":true,"5":true,"6":true,"7":true}',
   '{}')
ON CONFLICT (id) DO NOTHING;

UPDATE clients SET pipeline_config_id = '44444444-4444-4444-4444-111111111111' WHERE code = 'siteone';
UPDATE clients SET pipeline_config_id = '44444444-4444-4444-4444-222222222222' WHERE code = 'thd';

-- RETAILER TEMPLATES
INSERT INTO retailer_templates (id, client_id, template_name, version, export_formats, maintained_by) VALUES
  ('55555555-5555-5555-5555-111111111111', '11111111-1111-1111-1111-111111111111',
   'SiteOne Template v2.4', '2.4', '{"csv","json","pim"}', 'Iksula'),
  ('55555555-5555-5555-5555-222222222222', '11111111-1111-1111-1111-222222222222',
   'THD Template v6.1', '6.1', '{"csv","xml","pim"}', 'Iksula')
ON CONFLICT (id) DO NOTHING;

-- MODEL REGISTRY
INSERT INTO model_registry (model_name, model_type, provider, capabilities, default_for_stages) VALUES
  ('Iksula OCR Engine v2', 'ocr', 'iksula', '{"pdf_extraction","text_recognition"}', '{1}'),
  ('GPT-4o', 'llm', 'openai', '{"copy_generation","attribute_inference","classification"}', '{2,4}'),
  ('Iksula Vision v1.2', 'vision', 'iksula', '{"image_analysis","label_reading","colour_detection"}', '{1,4}'),
  ('Iksula KB v3.1', 'kb', 'iksula', '{"attribute_lookup","picklist_match","synonym_match"}', '{4}'),
  ('Iksula Dedup Model v1.0', 'classification', 'iksula', '{"duplicate_detection","variant_detection"}', '{3}'),
  ('Iksula DIM Validator v2.3', 'custom', 'iksula', '{"unit_normalisation","range_validation","format_check"}', '{5}'),
  ('Iksula Enrichment — Irrigation v4', 'custom', 'iksula', '{"web_enrichment","attribute_fill"}', '{4}'),
  ('Iksula Retail Taxonomy v4.2', 'classification', 'iksula', '{"taxonomy_classification","category_assignment"}', '{2}')
ON CONFLICT DO NOTHING;

-- TAXONOMY
INSERT INTO taxonomy_nodes (id, parent_id, level, code, name, full_path) VALUES
  ('33333333-3333-3333-3333-111111111111', NULL, 'department', 'HW', 'Hardware & Tools', 'Hardware & Tools'),
  ('33333333-3333-3333-3333-222222222222', '33333333-3333-3333-3333-111111111111', 'category', 'HW-IRR', 'Irrigation', 'Hardware & Tools > Irrigation'),
  ('33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-222222222222', 'class', 'HW-IRR-CTRL', 'Controllers', 'Hardware & Tools > Irrigation > Controllers'),
  ('33333333-3333-3333-3333-444444444444', '33333333-3333-3333-3333-333333333333', 'subclass', 'HW-IRR-CTRL-SMART', 'Smart Controllers', 'Hardware & Tools > Irrigation > Controllers > Smart Controllers')
ON CONFLICT (code) DO NOTHING;

-- Client labels
INSERT INTO taxonomy_client_labels (taxonomy_node_id, client_id, client_name, client_code) VALUES
  ('33333333-3333-3333-3333-444444444444', '11111111-1111-1111-1111-111111111111', 'Smart Controllers', 'SMART-CTRL'),
  ('33333333-3333-3333-3333-444444444444', '11111111-1111-1111-1111-222222222222', 'Wi-Fi Irrigation Timers', 'WIFI-IRR-TMR')
ON CONFLICT DO NOTHING;

-- IKSULA CLASS ATTRIBUTES (17 attributes for Smart Controllers)
INSERT INTO iksula_class_attributes (id, taxonomy_node_id, attribute_code, attribute_name, attribute_group, data_type, unit, is_mandatory, display_order, validation_rule) VALUES
  ('aa000001-0000-0000-0000-000000000001', '33333333-3333-3333-3333-444444444444', 'voltage', 'Voltage', 'Electrical', 'measurement', 'V', true, 1, '{"allowed":[12,24,120]}'),
  ('aa000001-0000-0000-0000-000000000002', '33333333-3333-3333-3333-444444444444', 'zones', 'Number of Zones', 'Functional', 'integer', NULL, true, 2, '{"min":1,"max":48}'),
  ('aa000001-0000-0000-0000-000000000003', '33333333-3333-3333-3333-444444444444', 'wifi_enabled', 'Wi-Fi Enabled', 'Connectivity', 'boolean', NULL, true, 3, NULL),
  ('aa000001-0000-0000-0000-000000000004', '33333333-3333-3333-3333-444444444444', 'ip_rating', 'IP Rating', 'Physical', 'enum', NULL, true, 4, NULL),
  ('aa000001-0000-0000-0000-000000000005', '33333333-3333-3333-3333-444444444444', 'colour', 'Colour', 'Physical', 'enum', NULL, true, 5, NULL),
  ('aa000001-0000-0000-0000-000000000006', '33333333-3333-3333-3333-444444444444', 'material', 'Material', 'Physical', 'enum', NULL, true, 6, NULL),
  ('aa000001-0000-0000-0000-000000000007', '33333333-3333-3333-3333-444444444444', 'weight_kg', 'Weight', 'Physical', 'measurement', 'kg', true, 7, '{"min":0.01,"max":50}'),
  ('aa000001-0000-0000-0000-000000000008', '33333333-3333-3333-3333-444444444444', 'shipping_weight_kg', 'Shipping Weight', 'Logistics', 'measurement', 'kg', true, 8, '{"min":0.01,"max":100}'),
  ('aa000001-0000-0000-0000-000000000009', '33333333-3333-3333-3333-444444444444', 'width_cm', 'Width', 'Physical', 'measurement', 'cm', false, 9, '{"min":0.1,"max":500}'),
  ('aa000001-0000-0000-0000-000000000010', '33333333-3333-3333-3333-444444444444', 'depth_cm', 'Depth', 'Physical', 'measurement', 'cm', false, 10, '{"min":0.1,"max":500}'),
  ('aa000001-0000-0000-0000-000000000011', '33333333-3333-3333-3333-444444444444', 'height_cm', 'Height', 'Physical', 'measurement', 'cm', false, 11, '{"min":0.1,"max":500}'),
  ('aa000001-0000-0000-0000-000000000012', '33333333-3333-3333-3333-444444444444', 'operating_temp_min_c', 'Operating Temp Min', 'Environmental', 'measurement', '°C', true, 12, '{"min":-40,"max":60}'),
  ('aa000001-0000-0000-0000-000000000013', '33333333-3333-3333-3333-444444444444', 'operating_temp_max_c', 'Operating Temp Max', 'Environmental', 'measurement', '°C', true, 13, '{"min":-20,"max":80}'),
  ('aa000001-0000-0000-0000-000000000014', '33333333-3333-3333-3333-444444444444', 'certifications', 'Certifications', 'Compliance', 'multi_enum', NULL, true, 14, NULL),
  ('aa000001-0000-0000-0000-000000000015', '33333333-3333-3333-3333-444444444444', 'compatible_valve_types', 'Compatible Valve Types', 'Functional', 'multi_enum', NULL, false, 15, NULL),
  ('aa000001-0000-0000-0000-000000000016', '33333333-3333-3333-3333-444444444444', 'app_name', 'Connected App Name', 'Connectivity', 'text', NULL, false, 16, NULL),
  ('aa000001-0000-0000-0000-000000000017', '33333333-3333-3333-3333-444444444444', 'warranty_months', 'Warranty', 'Commercial', 'integer', 'months', false, 17, '{"min":0,"max":120}')
ON CONFLICT (id) DO NOTHING;

-- ALLOWED VALUES (picklists)
INSERT INTO iksula_allowed_values (attribute_id, value_code, value_label, synonyms, sort_order) VALUES
  ('aa000001-0000-0000-0000-000000000005', 'grey', 'Grey', '{"gray","gry","grau","silver"}', 1),
  ('aa000001-0000-0000-0000-000000000005', 'white', 'White', '{"wht","whi"}', 2),
  ('aa000001-0000-0000-0000-000000000005', 'black', 'Black', '{"blk","blck"}', 3),
  ('aa000001-0000-0000-0000-000000000005', 'green', 'Green', '{"grn"}', 4),
  ('aa000001-0000-0000-0000-000000000004', 'ip44', 'IP44', '{"ip-44"}', 1),
  ('aa000001-0000-0000-0000-000000000004', 'ip54', 'IP54', '{"ip-54"}', 2),
  ('aa000001-0000-0000-0000-000000000004', 'ip65', 'IP65', '{"ip-65"}', 3),
  ('aa000001-0000-0000-0000-000000000004', 'ip67', 'IP67', '{"ip-67"}', 4),
  ('aa000001-0000-0000-0000-000000000006', 'abs_plastic', 'ABS Plastic', '{"abs","acrylonitrile butadiene styrene"}', 1),
  ('aa000001-0000-0000-0000-000000000006', 'polycarbonate', 'Polycarbonate', '{"pc","polycarb"}', 2),
  ('aa000001-0000-0000-0000-000000000006', 'pvc', 'PVC', '{"polyvinyl chloride"}', 3),
  ('aa000001-0000-0000-0000-000000000006', 'stainless_steel', 'Stainless Steel', '{"ss","s/s","304ss","316ss"}', 4),
  ('aa000001-0000-0000-0000-000000000014', 'ce', 'CE', '{"ce mark","ce marking"}', 1),
  ('aa000001-0000-0000-0000-000000000014', 'rohs', 'RoHS', '{"rohs compliant","rohs2"}', 2),
  ('aa000001-0000-0000-0000-000000000014', 'ul', 'UL Listed', '{"ul listed","underwriters laboratories"}', 3),
  ('aa000001-0000-0000-0000-000000000014', 'etl', 'ETL', '{"etl listed","intertek"}', 4),
  ('aa000001-0000-0000-0000-000000000014', 'fcc', 'FCC', '{"fcc certified","fcc compliant"}', 5),
  ('aa000001-0000-0000-0000-000000000015', '24vac_solenoid', '24VAC Solenoid', '{"24v solenoid","24 volt solenoid"}', 1),
  ('aa000001-0000-0000-0000-000000000015', 'dc_latching', 'DC Latching', '{"dc latching solenoid","9v dc"}', 2)
ON CONFLICT DO NOTHING;

-- SUPPLIER TEMPLATE: Orbit CSV
INSERT INTO supplier_templates (id, supplier_name, supplier_code, format_type, template_name, field_definitions) VALUES
  ('66666666-6666-6666-6666-111111111111', 'Orbit Irrigation Products', 'orbit', 'csv', 'Orbit CSV Catalog 2026',
   '[{"supplier_field":"Product Name","data_type":"text"},{"supplier_field":"Model","data_type":"text"},{"supplier_field":"Voltage","data_type":"text"},{"supplier_field":"# Stations","data_type":"text"},{"supplier_field":"WiFi","data_type":"text"},{"supplier_field":"IP","data_type":"text"},{"supplier_field":"Wt","data_type":"text"},{"supplier_field":"Clr","data_type":"text"},{"supplier_field":"Op Temp","data_type":"text"},{"supplier_field":"Warranty (mo)","data_type":"text"}]')
ON CONFLICT (id) DO NOTHING;

-- Supplier field mappings
INSERT INTO supplier_field_mappings (supplier_template_id, taxonomy_node_id, supplier_field_name, supplier_field_alias, iksula_attribute_id, normalise_rule, mapping_status) VALUES
  ('66666666-6666-6666-6666-111111111111', '33333333-3333-3333-3333-444444444444', 'Voltage', '{"Volts","V"}', 'aa000001-0000-0000-0000-000000000001', '{"type":"direct"}', 'auto'),
  ('66666666-6666-6666-6666-111111111111', '33333333-3333-3333-3333-444444444444', '# Stations', '{"Stations","Zones"}', 'aa000001-0000-0000-0000-000000000002', '{"type":"direct"}', 'auto'),
  ('66666666-6666-6666-6666-111111111111', '33333333-3333-3333-3333-444444444444', 'WiFi', '{"Wi-Fi","Wireless"}', 'aa000001-0000-0000-0000-000000000003', '{"type":"direct"}', 'auto'),
  ('66666666-6666-6666-6666-111111111111', '33333333-3333-3333-3333-444444444444', 'IP', '{"IP Rating"}', 'aa000001-0000-0000-0000-000000000004', '{"type":"direct"}', 'auto'),
  ('66666666-6666-6666-6666-111111111111', '33333333-3333-3333-3333-444444444444', 'Wt', '{"Weight"}', 'aa000001-0000-0000-0000-000000000007', '{"type":"direct"}', 'auto'),
  ('66666666-6666-6666-6666-111111111111', '33333333-3333-3333-3333-444444444444', 'Clr', '{"Color","Colour"}', 'aa000001-0000-0000-0000-000000000005', '{"type":"direct"}', 'corrected'),
  ('66666666-6666-6666-6666-111111111111', '33333333-3333-3333-3333-444444444444', 'Warranty (mo)', '{"Warranty"}', 'aa000001-0000-0000-0000-000000000017', '{"type":"direct"}', 'auto')
ON CONFLICT DO NOTHING;

-- CLIENT FIELD MAPPINGS: SiteOne
INSERT INTO client_field_mappings (client_id, template_id, taxonomy_node_id, iksula_attribute_id, client_field_name, client_field_code, client_field_order, is_mandatory, transform_rule, mapping_status) VALUES
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000001', 'Operating Voltage', 'op_voltage', 1, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000002', 'Zone Count', 'zone_count', 2, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000003', 'Wi-Fi Enabled', 'wifi', 3, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000004', 'IP Rating', 'ip_rating', 4, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000005', 'Product Color', 'color', 5, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000006', 'Material', 'material', 6, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000007', 'Weight (lbs)', 'weight_lbs', 7, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000008', 'Shipping Weight (lbs)', 'ship_weight_lbs', 8, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000014', 'Certifications', 'certifications', 9, true, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000017', 'Warranty Period', 'warranty', 10, false, '{"type":"direct"}', 'auto'),
  ('11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-111111111111', '33333333-3333-3333-3333-444444444444', 'aa000001-0000-0000-0000-000000000016', 'App Name', 'app_name', 11, false, '{"type":"direct"}', 'auto')
ON CONFLICT DO NOTHING;

-- PROMPT TEMPLATES
INSERT INTO prompt_templates (template_name, model_type, taxonomy_node_id, client_id, template_text, version) VALUES
  ('Iksula Copy Prompt — Irrigation Controllers v3.0 — SiteOne edition', 'llm',
   '33333333-3333-3333-3333-444444444444', '11111111-1111-1111-1111-111111111111',
   'You are a product content writer for SiteOne Landscape Supply. Generate professional B2B product copy.',
   '3.0')
ON CONFLICT DO NOTHING;

-- EXISTING PRODUCT for dedup matching
INSERT INTO products (id, client_id, taxonomy_node_id, product_name, model_number, sku, brand, supplier_name, current_stage, status, overall_confidence, completeness_pct) VALUES
  ('77777777-7777-7777-7777-111111111111',
   '11111111-1111-1111-1111-111111111111',
   '33333333-3333-3333-3333-444444444444',
   'Orbit 4-Zone Smart Irrigation Controller', 'B-0424W', 'ORB-0424W',
   'Orbit', 'Orbit Irrigation Products',
   7, 'published', 95.0, 100.0)
ON CONFLICT (id) DO NOTHING;

-- Existing product's Iksula values
INSERT INTO product_iksula_values (product_id, attribute_id, value_text, value_numeric, source, confidence, review_status, set_at_stage) VALUES
  ('77777777-7777-7777-7777-111111111111', 'aa000001-0000-0000-0000-000000000001', '24V', 24, 'raw_normalised', 98, 'human_approved', 1),
  ('77777777-7777-7777-7777-111111111111', 'aa000001-0000-0000-0000-000000000002', NULL, 4, 'raw_normalised', 98, 'human_approved', 1),
  ('77777777-7777-7777-7777-111111111111', 'aa000001-0000-0000-0000-000000000003', NULL, NULL, 'raw_normalised', 98, 'human_approved', 1),
  ('77777777-7777-7777-7777-111111111111', 'aa000001-0000-0000-0000-000000000005', 'grey', NULL, 'raw_normalised', 95, 'human_approved', 4),
  ('77777777-7777-7777-7777-111111111111', 'aa000001-0000-0000-0000-000000000006', 'abs_plastic', NULL, 'kb', 95, 'human_approved', 4),
  ('77777777-7777-7777-7777-111111111111', 'aa000001-0000-0000-0000-000000000007', NULL, 0.34, 'web_google', 90, 'human_approved', 4)
ON CONFLICT (product_id, attribute_id) DO NOTHING;

UPDATE product_iksula_values SET value_boolean = true
WHERE product_id = '77777777-7777-7777-7777-111111111111'
  AND attribute_id = 'aa000001-0000-0000-0000-000000000003';
