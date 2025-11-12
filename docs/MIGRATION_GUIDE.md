# Data Migration Guide

## Overview

This guide explains how to migrate your existing vector store data from file-based storage (SimpleVectorStore) to PostgreSQL with pgvector.

## Prerequisites

1. ✅ PostgreSQL with pgvector installed and running
2. ✅ Database connection configured (DATABASE_URL or POSTGRES_* env vars)
3. ✅ Python dependencies installed (`pip install -r requirements.txt`)
4. ✅ Existing vector store data in `user_data/` directory

## Migration Steps

### Step 1: Test Database Connection

```bash
source .venv/bin/activate
export DATABASE_URL=postgresql://postgres@localhost:5432/chat_pgvector
python -c "from storage.pg_connection import test_connection; test_connection()"
```

**Or use the helper script** (automatically sets DATABASE_URL):
```bash
./run_migration.sh --dry-run
```

### Step 2: Dry Run (Recommended)

Test the migration without actually migrating:

**Option 1: Using helper script** (recommended):
```bash
./run_migration.sh --dry-run
```

**Option 2: Manual**:
```bash
source .venv/bin/activate
export DATABASE_URL=postgresql://postgres@localhost:5432/chat_pgvector
python storage/migrations/migrate_to_pgvector.py --dry-run
```

This will:
- Find all vector stores
- Load and verify data
- Show what would be migrated
- **Not** actually migrate anything

### Step 3: Run Migration

Once you're satisfied with the dry run:

**Option 1: Using helper script** (recommended):
```bash
./run_migration.sh
```

**Option 2: Manual**:
```bash
source .venv/bin/activate
export DATABASE_URL=postgresql://postgres@localhost:5432/chat_pgvector
python storage/migrations/migrate_to_pgvector.py
```

This will:
- Create backups of all vector store files
- Migrate data to PostgreSQL
- Verify data integrity
- Show migration summary

### Step 4: Verify Migration

Check that data was migrated correctly:

```python
from storage.pg_vector_store import PgVectorStore

# Check your user's data
store = PgVectorStore(collection_name="personal_assistant", user_id="your_user_id")
stats = store.get_collection_stats()
print(f"Documents: {stats['document_count']}")

# Test a search
results = store.similarity_search("test query", k=5)
print(f"Found {len(results)} results")
```

## Migration Details

### What Gets Migrated

- **Vectors**: Original embeddings are regenerated using the current embedding model
- **Metadata**: All metadata fields (except internal IDs) are preserved
- **Text Content**: Document text is extracted from metadata and re-embedded

### Important Notes

1. **Embeddings are regenerated**: The migration script extracts text from metadata and generates new embeddings. This ensures consistency with your current embedding model.

2. **Dimensionality reduction**: If your embeddings exceed 2000 dimensions, they will be automatically reduced to 2000 for pgvector indexing.

3. **Backups**: Original files are backed up to `migration_backup/` before migration.

4. **User isolation**: Each user's data is migrated separately with proper user_id isolation.

### Migration Options

```bash
# Dry run only
python storage/migrations/migrate_to_pgvector.py --dry-run

# Skip backups (not recommended)
python storage/migrations/migrate_to_pgvector.py --no-backup

# Custom directories
python storage/migrations/migrate_to_pgvector.py \
    --user-data-dir ./custom_user_data \
    --backup-dir ./custom_backup
```

## Rollback

If you need to rollback:

1. **Stop using PgVectorStore**: Switch back to SimpleVectorStore in your code
2. **Restore backups**: Copy files from `migration_backup/` back to original locations
3. **Delete PostgreSQL data** (if needed):
   ```sql
   DELETE FROM vector_documents WHERE user_id = 'your_user_id';
   ```

## Troubleshooting

### "No vector stores found"

- Check that `user_data/` directory exists
- Verify vector store paths: `user_data/{user_id}/vector_store_{collection_name}/`

### "Database connection failed"

- Verify DATABASE_URL environment variable
- Check PostgreSQL is running: `pg_isready`
- Test connection: `python -c "from storage.pg_connection import test_connection; test_connection()"`

### "Error loading metadata"

- Check if encryption is enabled
- Verify user_id matches the encryption key
- Try reading metadata.json manually to check format

### "No text content found"

- Check that metadata.json contains "text" field
- Verify metadata structure matches expected format

## Post-Migration

After successful migration:

1. ✅ Update application code to use PgVectorStore (Phase 4)
2. ✅ Test all functionality
3. ✅ Keep backups for at least a few days
4. ✅ Monitor performance
5. ✅ Consider removing old file-based stores after verification

## Migration Script Output

Example output:

```
============================================================
Vector Store Migration to PostgreSQL
============================================================
User data directory: user_data
Backup directory: migration_backup
Mode: LIVE MIGRATION
============================================================

Found 1 vector store(s) to migrate:
  - mycguo_gmail_com/personal_assistant

Creating backups in migration_backup...
  Backup created: migration_backup/20250112_143022/mycguo_gmail_com/personal_assistant

Migrating store: mycguo_gmail_com/personal_assistant
  Path: user_data/mycguo_gmail_com/vector_store_personal_assistant
  Loaded 116 vectors from ...
  Loaded 116 metadata entries (decrypted)
  Adding 116 documents to PostgreSQL...
  Fitting PCA model to reduce from 3072 to 2000 dimensions...
  Saved PCA model to ...

============================================================
Migration Summary
============================================================
Total stores: 1
Successful: 1
Failed: 0
Total documents migrated: 116

✅ Migration completed successfully!
```

