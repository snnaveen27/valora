-- ============================================================================
-- Vector Database Schema (pgvector only)
-- Stores embeddings for properties for semantic search and recommendations
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- optional text search

-- Embeddings table (one row per property)
CREATE TABLE IF NOT EXISTS property_embeddings (
    property_id UUID PRIMARY KEY,
    description_embedding VECTOR(1536),
    amenities_embedding VECTOR(1536),
    location_embedding VECTOR(1536),
    combined_embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Vector indexes
CREATE INDEX IF NOT EXISTS idx_emb_description_ivf ON property_embeddings USING ivfflat (description_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_emb_amenities_ivf  ON property_embeddings USING ivfflat (amenities_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_emb_location_ivf   ON property_embeddings USING ivfflat (location_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_emb_combined_ivf   ON property_embeddings USING ivfflat (combined_embedding vector_cosine_ops);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_property_embeddings_updated_at ON property_embeddings;
CREATE TRIGGER update_property_embeddings_updated_at
BEFORE UPDATE ON property_embeddings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
