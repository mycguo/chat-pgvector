-- Migration: Create vector_documents table with pgvector support
-- Run this migration to set up the database schema for vector storage

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main documents table for storing vectors and metadata
CREATE TABLE IF NOT EXISTS vector_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL DEFAULT 'personal_assistant',
    text TEXT NOT NULL,
    embedding vector(768) NOT NULL,  -- Google gemini-embedding-001 produces 768-dimensional vectors
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user and collection lookups
CREATE INDEX IF NOT EXISTS idx_vector_documents_user_collection 
    ON vector_documents(user_id, collection_name);

-- HNSW index for fast vector similarity search
-- Using cosine distance operator
CREATE INDEX IF NOT EXISTS idx_vector_documents_embedding_hnsw 
    ON vector_documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Alternative IVFFlat index (uncomment if preferred for smaller datasets)
-- CREATE INDEX IF NOT EXISTS idx_vector_documents_embedding_ivfflat 
--     ON vector_documents USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_vector_documents_metadata_gin 
    ON vector_documents USING gin (metadata);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_vector_documents_updated_at ON vector_documents;
CREATE TRIGGER update_vector_documents_updated_at 
    BEFORE UPDATE ON vector_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE vector_documents IS 'Stores document embeddings with metadata for semantic search';
COMMENT ON COLUMN vector_documents.embedding IS '768-dimensional vector embedding (Google gemini-embedding-001)';
COMMENT ON COLUMN vector_documents.metadata IS 'JSONB metadata for flexible querying and filtering';
COMMENT ON INDEX idx_vector_documents_embedding_hnsw IS 'HNSW index for fast approximate nearest neighbor search';

