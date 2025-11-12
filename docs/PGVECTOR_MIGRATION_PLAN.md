# PostgreSQL + pgvector Migration Plan

## Overview
Migrate from file-based vector storage (`SimpleVectorStore` using pickle + JSON) to PostgreSQL with pgvector extension for better scalability, ACID compliance, and production readiness.

## Current Implementation Analysis

### Current State
- **Storage**: `SimpleVectorStore` class in `simple_vector_store.py`
- **Backend**: File-based (pickle for vectors, JSON for metadata)
- **Location**: `./user_data/{user_id}/vector_store_personal_assistant/`
- **Features**:
  - User-specific storage paths
  - Optional encryption for metadata
  - Google Generative AI embeddings (`models/gemini-embedding-001`)
  - Cosine similarity search
  - Document CRUD operations

### Key Methods to Preserve
```python
- __init__(store_path, embedding_model, user_id)
- add_texts(texts, metadatas) -> List[str]
- add_documents(documents) -> List[str]
- similarity_search(query, k=4) -> List[Document]
- similarity_search_with_score(query, k=4) -> List[tuple]
- delete(ids) -> None
- get_collection_stats() -> Dict
- from_texts() -> SimpleVectorStore
```

## Migration Strategy

### Phase 1: Infrastructure Setup

#### 1.1 Database Connection Module
**File**: `storage/pg_connection.py`
- Create connection pool manager
- Handle user-specific database connections
- Support connection string from environment variables
- Connection pooling for performance

#### 1.2 Database Schema
**File**: `storage/migrations/001_create_vector_tables.sql`
- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- Create `vector_documents` table:
  ```sql
  CREATE TABLE vector_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL DEFAULT 'personal_assistant',
    text TEXT NOT NULL,
    embedding vector(768),  -- Adjust based on embedding dimension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
  );
  ```
- Create indexes:
  - `idx_vector_documents_user_collection` on (user_id, collection_name)
  - HNSW index for vector similarity: `CREATE INDEX ON vector_documents USING hnsw (embedding vector_cosine_ops);`
- Add updated_at trigger

#### 1.3 Environment Configuration
**New Variables**:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chat_pgvector
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
# Or use connection string:
DATABASE_URL=postgresql://user:password@host:port/database
```

### Phase 2: PgVectorStore Implementation

#### 2.1 Core Class Structure
**File**: `storage/pg_vector_store.py`
- Implement same interface as `SimpleVectorStore`
- Use psycopg2 for PostgreSQL connection
- Use pgvector for vector operations
- Maintain user-specific data isolation
- Support encryption (if enabled)

#### 2.2 Key Implementation Details

**Embedding Dimension**:
- Google `gemini-embedding-001` produces 768-dimensional vectors
- Use `vector(768)` type in PostgreSQL

**Similarity Search**:
- Use pgvector's cosine distance operator: `<=>`
- Query: `SELECT *, embedding <=> %s AS distance FROM vector_documents WHERE user_id = %s ORDER BY distance LIMIT k`

**Metadata Storage**:
- Store as JSONB for flexible querying
- Support filtering by metadata fields

**User Isolation**:
- Always filter by `user_id` in queries
- Use `collection_name` for multi-collection support

### Phase 3: Data Migration

#### 3.1 Migration Script
**File**: `storage/migrations/migrate_to_pgvector.py`
- Read existing pickle/JSON files
- Extract vectors and metadata
- Insert into PostgreSQL
- Verify data integrity
- Option to rollback

**Migration Steps**:
1. Connect to PostgreSQL
2. Run schema migration
3. For each user's vector store:
   - Load `vectors.pkl` and `metadata.json`
   - Decrypt metadata if encrypted
   - Insert into PostgreSQL with user_id
4. Verify counts match
5. Create backup of old files

### Phase 4: Code Updates

#### 4.1 Update Imports
- Replace `from simple_vector_store import SimpleVectorStore` 
- With `from storage.pg_vector_store import PgVectorStore`
- Or create alias for backward compatibility

#### 4.2 Files to Update
1. `app.py` - Main chat interface
2. `pages/upload_docs.py` - Document upload
3. `pages/interview_prep.py` - Interview prep features
4. `simple_vector_store.py` - Add deprecation warning or wrapper

#### 4.3 Backward Compatibility
- Option 1: Keep `SimpleVectorStore` as wrapper around `PgVectorStore`
- Option 2: Add feature flag to switch between implementations
- Option 3: Direct replacement (cleaner, but requires migration)

### Phase 5: Testing & Validation

#### 5.1 Unit Tests
- Test all CRUD operations
- Test similarity search accuracy
- Test user isolation
- Test metadata filtering
- Test encryption (if enabled)

#### 5.2 Integration Tests
- Test with real embeddings
- Test migration script
- Test performance benchmarks
- Compare results with old implementation

#### 5.3 Performance Considerations
- Connection pooling
- Batch inserts for multiple documents
- Index optimization (HNSW vs IVFFlat)
- Query performance with large datasets

## Implementation Details

### Database Schema Design

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main documents table
CREATE TABLE IF NOT EXISTS vector_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL DEFAULT 'personal_assistant',
    text TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_vector_documents_user_collection 
    ON vector_documents(user_id, collection_name);

CREATE INDEX IF NOT EXISTS idx_vector_documents_embedding_hnsw 
    ON vector_documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_vector_documents_updated_at 
    BEFORE UPDATE ON vector_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### PgVectorStore Class Structure

```python
class PgVectorStore:
    def __init__(self, collection_name="personal_assistant", 
                 embedding_model="models/gemini-embedding-001",
                 user_id=None):
        # Initialize connection
        # Get user_id
        # Initialize embeddings
        
    def add_texts(self, texts, metadatas=None):
        # Generate embeddings
        # Batch insert into PostgreSQL
        
    def similarity_search(self, query, k=4):
        # Generate query embedding
        # Query with cosine distance
        # Return Document objects
        
    def delete(self, ids):
        # Delete by IDs
        
    def get_collection_stats(self):
        # Query count and stats
```

## Dependencies

### New Requirements
```txt
psycopg2-binary>=2.9.0
pgvector>=0.2.0  # Python client for pgvector
```

### PostgreSQL Setup
- PostgreSQL 11+ required
- pgvector extension must be installed
- For local development: `docker run -p 5432:5432 pgvector/pgvector:pg16`

## Migration Checklist

- [ ] Install PostgreSQL and pgvector extension
- [ ] Create database connection module
- [ ] Create database schema migration
- [ ] Implement PgVectorStore class
- [ ] Create data migration script
- [ ] Update requirements.txt
- [ ] Update all imports and usage
- [ ] Test with existing data
- [ ] Run migration script
- [ ] Update tests
- [ ] Performance testing
- [ ] Documentation updates
- [ ] Remove old SimpleVectorStore (optional)

## Rollback Plan

1. Keep old `SimpleVectorStore` code
2. Add feature flag to switch implementations
3. Keep old data files until migration verified
4. Document rollback procedure

## Performance Considerations

### Index Strategy
- **HNSW**: Better for high-dimensional vectors, faster queries, larger index size
- **IVFFlat**: Smaller index, faster build time, slightly slower queries

**Recommendation**: Use HNSW for production, IVFFlat for development/testing

### Connection Pooling
- Use psycopg2.pool.ThreadedConnectionPool
- Configure pool size based on expected load
- Reuse connections efficiently

### Batch Operations
- Insert multiple documents in single transaction
- Use `executemany()` for bulk inserts
- Consider COPY for very large migrations

## Security Considerations

1. **User Isolation**: Always filter by user_id (SQL injection prevention)
2. **Connection Security**: Use SSL for production connections
3. **Credentials**: Store in environment variables, never in code
4. **Encryption**: Continue supporting metadata encryption if enabled
5. **SQL Injection**: Use parameterized queries exclusively

## Next Steps

1. Review and approve this plan
2. Set up PostgreSQL development environment
3. Implement Phase 1 (Infrastructure)
4. Implement Phase 2 (PgVectorStore)
5. Test with sample data
6. Create migration script
7. Update application code
8. Run full migration
9. Monitor and optimize

