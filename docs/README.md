# Documentation Index

## 🎯 Getting Started

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete architecture overview
- **[CURRENT_STATE.md](CURRENT_STATE.md)** - Current implementation state and migration status
- **[PGVECTOR_SETUP.md](PGVECTOR_SETUP.md)** - PostgreSQL + pgvector setup guide

## 📊 Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, data flow, and design decisions
- **[QUERY_ARCHITECTURE.md](QUERY_ARCHITECTURE.md)** - Query patterns for structured and semantic search
- **[PGVECTOR_ONLY_ARCHITECTURE.md](PGVECTOR_ONLY_ARCHITECTURE.md)** - Design decisions for pgvector-only architecture

## 🔄 Migration & Implementation

- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Complete migration summary
- **[COMPLETE_JSON_TO_PGVECTOR_MIGRATION.md](COMPLETE_JSON_TO_PGVECTOR_MIGRATION.md)** - Detailed migration process
- **[MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)** - Migration status and file structure
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Step-by-step migration guide
- **[PGVECTOR_MIGRATION_PLAN.md](PGVECTOR_MIGRATION_PLAN.md)** - Original migration plan

## 🔧 Technical Details

- **[JSON_VECTOR_SYNC.md](JSON_VECTOR_SYNC.md)** - How JSON data is synced to vector store
- **[DEPENDENCY_NOTES.md](DEPENDENCY_NOTES.md)** - Dependency management notes

## 🔐 Security & Configuration

- **[ENCRYPTION_SETUP.md](ENCRYPTION_SETUP.md)** - Encryption setup guide
- **[OAUTH_REDIRECT_URI_SETUP.md](OAUTH_REDIRECT_URI_SETUP.md)** - OAuth configuration

## 📝 Features

- **[REMEMBER_FEATURE.md](REMEMBER_FEATURE.md)** - Remember feature documentation
- **[REMEMBER_FEATURE_QUICKSTART.md](REMEMBER_FEATURE_QUICKSTART.md)** - Quick start for remember feature
- **[INTERVIEW_PREP_REPLAN.md](INTERVIEW_PREP_REPLAN.md)** - Interview prep feature details

## 📚 Quick Reference

### Current Architecture
- **Storage**: PostgreSQL + pgvector (single source of truth)
- **Data**: All structured data in `vector_documents` table
- **Collections**: applications, companies, contacts, quick_notes, interview_prep, resumes, personal_assistant
- **Remaining JSON**: Only `profile.json` and `interview_data/companies.json`

### Key Files
- `storage/pg_vector_store.py` - PgVectorStore implementation
- `storage/json_db.py` - JobSearchDB (uses pgvector)
- `storage/interview_db.py` - InterviewDB (uses pgvector)
- `storage/resume_db.py` - ResumeDB (uses pgvector)
- `storage/vector_sync.py` - Automatic sync to pgvector

### Database Schema
- Table: `vector_documents`
- Key columns: `id`, `user_id`, `collection_name`, `text`, `embedding`, `metadata`
- Indexes: Vector (IVFFlat), JSONB (GIN), Path indexes for structured queries

## 🚀 Next Steps

1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system overview
2. Check [CURRENT_STATE.md](CURRENT_STATE.md) for migration status
3. See [QUERY_ARCHITECTURE.md](QUERY_ARCHITECTURE.md) for query patterns
4. Refer to [PGVECTOR_SETUP.md](PGVECTOR_SETUP.md) for setup instructions
