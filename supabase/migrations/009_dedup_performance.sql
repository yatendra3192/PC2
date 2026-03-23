-- Performance indexes for dedup at 300K+ products
-- These enable fast exact-match lookups and taxonomy-scoped vector search

-- Exact match indexes (B-tree, O(1) lookup)
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku) WHERE sku IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_upc ON products(upc) WHERE upc IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_ean ON products(ean) WHERE ean IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_model ON products(model_number) WHERE model_number IS NOT NULL;

-- Composite index: taxonomy + status (for pre-filtered dedup search)
CREATE INDEX IF NOT EXISTS idx_products_taxonomy_status ON products(taxonomy_node_id, status)
  WHERE status = 'published';

-- pgvector: recreate with proper list count for scale
-- For 300K products: sqrt(300000) ≈ 548, round to 500 lists
-- This replaces the initial index if it exists
DROP INDEX IF EXISTS idx_embed_vector;
CREATE INDEX idx_embed_vector ON product_embeddings
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 500);

-- Index for fast embedding lookup by product
CREATE INDEX IF NOT EXISTS idx_embed_product ON product_embeddings(product_id);
