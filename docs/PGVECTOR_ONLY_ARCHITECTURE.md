# pgvector-Only Architecture: Eliminating JSON Files

## 🎯 Goal

Eliminate JSON files entirely and use PostgreSQL + pgvector as the **single source of truth** for all data (both structured and semantic).

## Current State vs. Target State

### Current (Dual Storage)
```
JSON Files → Structured queries (filtering, sorting)
pgvector   → Semantic search (similarity queries)
```

### Target (Single Storage)
```
pgvector → Everything (structured queries + semantic search)
```

## Architecture Changes

### 1. Store Full Structured Data in Metadata

**Current**: Only formatted text in `metadata`
```python
metadata = {
    "text": "Job Application: Google - SWE\nStatus: applied...",
    "timestamp": "2024-01-01"
}
```

**New**: Full structured object in `metadata`
```python
metadata = {
    "record_type": "application",  # application, question, resume, company
    "record_id": "app_abc123",
    "data": {
        "company": "Google",
        "role": "SWE",
        "status": "applied",
        "applied_date": "2024-01-01",
        # ... full Application object
    },
    "text": "Job Application: Google - SWE\n...",  # For semantic search
    "timestamp": "2024-01-01"
}
```

### 2. Add JSONB Path Indexes

Add indexes for common structured queries:

```sql
-- Index for filtering by record_type
CREATE INDEX IF NOT EXISTS idx_vector_documents_record_type 
ON vector_documents ((metadata->>'record_type'));

-- Index for filtering applications by status
CREATE INDEX IF NOT EXISTS idx_vector_documents_app_status 
ON vector_documents ((metadata->'data'->>'status'))
WHERE metadata->>'record_type' = 'application';

-- Index for filtering applications by company
CREATE INDEX IF NOT EXISTS idx_vector_documents_app_company 
ON vector_documents ((metadata->'data'->>'company'))
WHERE metadata->>'record_type' = 'application';

-- Index for filtering questions by type/category
CREATE INDEX IF NOT EXISTS idx_vector_documents_question_type 
ON vector_documents ((metadata->'data'->>'type'))
WHERE metadata->>'record_type' = 'question';

-- Index for record_id lookups (for get_by_id queries)
CREATE INDEX IF NOT EXISTS idx_vector_documents_record_id 
ON vector_documents ((metadata->>'record_id'));
```

### 3. Extend PgVectorStore with Structured Query Methods

Add methods to `PgVectorStore` for structured queries:

```python
class PgVectorStore:
    # ... existing methods ...
    
    def get_by_record_id(self, record_type: str, record_id: str) -> Optional[Dict]:
        """Get a single record by type and ID"""
        
    def list_records(
        self,
        record_type: str,
        filters: Optional[Dict] = None,
        sort_by: Optional[str] = None,
        reverse: bool = True
    ) -> List[Dict]:
        """List records with filtering and sorting"""
        
    def query_structured(
        self,
        record_type: str,
        filters: Dict,
        limit: int = 100
    ) -> List[Dict]:
        """Query structured data using JSONB filters"""
```

### 4. Refactor Database Classes

**Option A: Keep API, Change Backend**
- `JobSearchDB`, `InterviewDB`, `ResumeDB` keep same methods
- Internally query `PgVectorStore` instead of JSON files
- No changes needed in `app.py` or pages

**Option B: Direct pgvector Access**
- Remove `JobSearchDB`, `InterviewDB`, `ResumeDB` entirely
- Use `PgVectorStore` directly everywhere
- More refactoring needed

**Recommendation**: Option A (keep API, change backend) for minimal disruption.

## Implementation Plan

### Phase 1: Update Vector Sync
- Modify `vector_sync.py` to store full structured data in `metadata['data']`
- Keep formatted text in `metadata['text']` for semantic search
- Add `record_type` and `record_id` to metadata

### Phase 2: Add JSONB Indexes
- Create migration script to add JSONB path indexes
- Test query performance

### Phase 3: Extend PgVectorStore
- Add structured query methods
- Support filtering, sorting, pagination
- Maintain backward compatibility

### Phase 4: Refactor Database Classes
- Update `JobSearchDB`, `InterviewDB`, `ResumeDB` to use `PgVectorStore`
- Keep same public API
- Remove JSON file reads/writes

### Phase 5: Migration & Cleanup
- Migrate existing JSON data to pgvector (if not already done)
- Remove JSON file dependencies
- Update tests

## Benefits

✅ **Single Source of Truth**: No sync issues
✅ **ACID Transactions**: Database guarantees
✅ **Efficient Queries**: JSONB indexes for structured queries
✅ **Semantic Search**: Vector similarity for natural language
✅ **Scalability**: PostgreSQL handles large datasets
✅ **Backup/Restore**: Standard database tools

## Considerations

⚠️ **Migration**: Need to migrate all existing JSON data
⚠️ **Performance**: JSONB queries are fast but may be slower than direct JSON reads for very simple queries
⚠️ **Backup Strategy**: Need database backups instead of file backups
⚠️ **Testing**: Need to update all tests

## Example: Structured Query

```python
# Old way (JSON files)
db = JobSearchDB()
apps = db.list_applications(status="applied", company="Google")

# New way (pgvector)
vector_store = PgVectorStore(collection_name="applications")
apps = vector_store.list_records(
    record_type="application",
    filters={"status": "applied", "company": "Google"},
    sort_by="applied_date",
    reverse=True
)
```

## Example: Hybrid Query (Structured + Semantic)

```python
# Find applications semantically similar to "remote backend engineer"
# but filter to only "applied" status
vector_store = PgVectorStore(collection_name="applications")

# Semantic search
similar_docs = vector_store.similarity_search("remote backend engineer", k=10)

# Filter by structured data
filtered = [
    doc for doc in similar_docs
    if doc.metadata.get('data', {}).get('status') == 'applied'
]
```

