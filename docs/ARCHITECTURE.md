# Architecture Overview

## 🎯 Current Implementation

This application uses **PostgreSQL + pgvector as the single source of truth** for all structured data and semantic search. The architecture has been fully migrated from file-based storage to a database-backed system.

## 📊 Data Storage Architecture

### PostgreSQL + pgvector (Primary Storage)

**All application data is stored in PostgreSQL with pgvector extension:**

```
PostgreSQL Database (chat_pgvector)
└── vector_documents table
    ├── Applications (collection: "applications")
    ├── Companies (collection: "companies")
    ├── Contacts (collection: "contacts")
    ├── Quick Notes (collection: "quick_notes")
    ├── Interview Questions (collection: "interview_prep")
    ├── Technical Concepts (collection: "interview_prep")
    ├── Practice Sessions (collection: "interview_prep")
    ├── Resumes (collection: "resumes")
    ├── Resume Versions (collection: "resumes")
    └── Uploaded Documents (collection: "personal_assistant")
```

**Key Features:**
- **Vector embeddings**: 3072 dimensions (Google Gemini) → reduced to 2000 (PCA) for indexing
- **Full structured data**: Stored in `metadata['data']` JSONB field
- **Semantic search**: Formatted text in `metadata['text']` for similarity search
- **User isolation**: Each user's data is isolated via `user_id`
- **ACID compliance**: Full database transactions
- **Indexes**: JSONB path indexes for efficient structured queries
- **Vector indexes**: IVFFlat for dimensions 1000-2000

### File System (Minimal)

**Only two types of files remain:**

1. **User Profile** (`profile.json`)
   - Location: `user_data/{user_id}/job_search_data/profile.json`
   - Purpose: User-specific profile settings
   - Status: Still uses JSON (not migrated)

2. **Interview Research Companies** (`companies.json`)
   - Location: `user_data/{user_id}/interview_data/companies.json`
   - Purpose: Company research notes for interviews (different from job search companies)
   - Status: Still uses JSON (not migrated)

3. **Resume PDF Files** (`files/`)
   - Location: `user_data/{user_id}/resume_data/files/`
   - Purpose: Actual PDF resume files
   - Status: Binary files, stored on disk (not in database)

## 🔄 Data Flow

### Adding Data

```
User Action → Database Class (JobSearchDB/InterviewDB/ResumeDB)
           → PgVectorStore.add_texts()
           → Format text for semantic search
           → Store full structured data in metadata['data']
           → Generate embeddings (Google Gemini)
           → Reduce dimensions (PCA: 3072 → 2000)
           → Insert into PostgreSQL
```

### Querying Data

**Structured Queries** (filtering, sorting):
```
User Query → Database Class method
          → PgVectorStore.list_records()
          → PostgreSQL JSONB query
          → Filter by record_type, filters
          → Return structured data from metadata['data']
```

**Semantic Search**:
```
User Query → PgVectorStore.similarity_search()
          → Generate query embedding
          → Reduce dimensions (PCA)
          → PostgreSQL vector cosine similarity search
          → Return top-k similar documents
```

## 🗂️ Database Classes

### JobSearchDB (`storage/json_db.py`)

**Uses pgvector for:**
- ✅ Applications (`applications` collection)
- ✅ Companies (`companies` collection)
- ✅ Contacts (`contacts` collection)
- ✅ Quick Notes (`quick_notes` collection)

**Uses JSON for:**
- Profile data (`profile.json`)

### InterviewDB (`storage/interview_db.py`)

**Uses pgvector for:**
- ✅ Interview Questions (`interview_prep` collection)
- ✅ Technical Concepts (`interview_prep` collection)
- ✅ Practice Sessions (`interview_prep` collection)

**Uses JSON for:**
- Interview research companies (`companies.json`)

### ResumeDB (`storage/resume_db.py`)

**Uses pgvector for:**
- ✅ Resumes (`resumes` collection)
- ✅ Resume Versions (`resumes` collection)

**Uses file system for:**
- PDF resume files (`files/` directory)

## 🔍 Vector Store Implementation

### PgVectorStore (`storage/pg_vector_store.py`)

**Core Methods:**
- `add_texts()` - Add documents with embeddings
- `similarity_search()` - Semantic similarity search
- `get_by_record_id()` - Direct lookup by type and ID
- `list_records()` - Structured queries with filtering/sorting
- `delete()` - Delete documents

**Key Features:**
- Automatic dimensionality detection
- PCA-based dimension reduction (3072 → 2000)
- Dynamic table creation with correct vector dimensions
- User and collection isolation
- JSONB metadata storage

## 📝 Data Synchronization

### Vector Sync (`storage/vector_sync.py`)

All database operations automatically sync to pgvector:

- `sync_application_to_vector_store()` - Called on add/update
- `sync_company_to_vector_store()` - Called on add/update
- `sync_contact_to_vector_store()` - Called on add/update
- `sync_quick_note_to_vector_store()` - Called on add/update
- `sync_interview_question_to_vector_store()` - Called on add/update
- `sync_concept_to_vector_store()` - Called on add/update
- `sync_practice_session_to_vector_store()` - Called on add/update
- `sync_resume_to_vector_store()` - Called on add/update
- `sync_resume_version_to_vector_store()` - Called on add/update

**Format:**
- Full structured data → `metadata['data']`
- Formatted text → `metadata['text']`
- Record identification → `metadata['record_type']` and `metadata['record_id']`

## 🔐 Security & Encryption

- **Encryption**: Optional file-level encryption for JSON files (if enabled)
- **User Isolation**: Database-level isolation via `user_id`
- **Connection Security**: PostgreSQL connection string from environment variables

## 🚀 Performance Optimizations

1. **Vector Indexes**: IVFFlat index for 2000-dimensional vectors
2. **JSONB Indexes**: Path indexes for common query patterns
3. **Connection Pooling**: Threaded connection pool for database connections
4. **Batch Operations**: Efficient batch inserts for multiple documents
5. **PCA Caching**: Trained PCA model cached per collection

## 📦 Dependencies

- **PostgreSQL**: Database server
- **pgvector**: Vector similarity extension
- **psycopg2**: PostgreSQL adapter
- **langchain-google-genai**: Embeddings (Google Gemini)
- **numpy/scikit-learn**: PCA for dimensionality reduction

## 🔄 Migration Status

✅ **Completed Migrations:**
- Vector store (from pickle/JSON to PostgreSQL)
- Applications (from JSON to pgvector)
- Companies (from JSON to pgvector)
- Contacts (from JSON to pgvector)
- Quick Notes (from JSON to pgvector)
- Interview Questions (from JSON to pgvector)
- Technical Concepts (from JSON to pgvector)
- Practice Sessions (from JSON to pgvector)
- Resumes (from JSON to pgvector)
- Resume Versions (from JSON to pgvector)

⏳ **Not Migrated (Intentionally):**
- User profile data (`profile.json`)
- Interview research companies (`companies.json`)
- Resume PDF files (binary files on disk)

## 📚 Related Documentation

- `docs/DATABASE_SCHEMA.md` - Complete database schema documentation
- `docs/PGVECTOR_SETUP.md` - PostgreSQL + pgvector setup guide
- `docs/NEON_MIGRATION_PLAN.md` - Migration guide for Neon.tech (serverless PostgreSQL)
- `docs/PGVECTOR_ONLY_ARCHITECTURE.md` - Architecture design decisions
- `docs/COMPLETE_JSON_TO_PGVECTOR_MIGRATION.md` - Migration details
- `docs/QUERY_ARCHITECTURE.md` - Query patterns and examples

