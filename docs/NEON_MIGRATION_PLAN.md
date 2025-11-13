# Migration Plan: Local PostgreSQL to Neon.tech

**Status**: Planning Document  
**Target**: Migrate from local PostgreSQL to Neon.tech serverless PostgreSQL

## Overview

This document outlines the step-by-step plan to migrate the application's database from local PostgreSQL to [Neon.tech](https://neon.tech/), a serverless PostgreSQL platform that supports pgvector.

### Why Neon.tech?

- ✅ **Serverless**: Auto-scaling, pay-per-use pricing
- ✅ **pgvector Support**: Native support for vector similarity search
- ✅ **Branching**: Create database branches for testing/staging
- ✅ **Managed**: No server management required
- ✅ **Free Tier**: Generous free tier for development
- ✅ **SSL**: Built-in SSL/TLS encryption

---

## Prerequisites

### 1. Neon.tech Account Setup

1. **Sign up** at [neon.tech](https://neon.tech/)
2. **Create a new project** (or use existing)
3. **Create a database** named `chat_pgvector` (or your preferred name)
4. **Note connection details**:
   - Host (e.g., `ep-xxx.us-east-2.aws.neon.tech`)
   - Port (usually `5432`)
   - Database name
   - Username
   - Password
   - Connection string (provided in Neon dashboard)

### 2. Required Tools

Ensure you have:
- `pg_dump` (PostgreSQL client tools)
- `psql` (PostgreSQL client)
- `pg_restore` (PostgreSQL client tools)
- Python environment with `psycopg2` installed

**Check installation**:
```bash
which pg_dump psql pg_restore
```

**Install if missing** (macOS):
```bash
brew install postgresql@16
```

---

## Migration Strategy

### Option A: Full Migration (Recommended for First Time)

**Best for**: Initial migration, small to medium datasets  
**Downtime**: Minimal (during data transfer)  
**Complexity**: Low

### Option B: Zero-Downtime Migration (Advanced)

**Best for**: Production environments, large datasets  
**Downtime**: None (with careful planning)  
**Complexity**: High (requires dual-write period)

---

## Phase 1: Pre-Migration Preparation

### Step 1.1: Backup Local Database

**Create a full backup** of your local database:

```bash
# Set local database connection details
export LOCAL_DB_USER=postgres
export LOCAL_DB_NAME=chat_pgvector
export LOCAL_DB_HOST=localhost
export LOCAL_DB_PORT=5432

# Create backup directory
mkdir -p backups
BACKUP_FILE="backups/local_db_$(date +%Y%m%d_%H%M%S).dump"

# Create custom-format backup (includes schema + data)
pg_dump \
  -U "$LOCAL_DB_USER" \
  -h "$LOCAL_DB_HOST" \
  -p "$LOCAL_DB_PORT" \
  -d "$LOCAL_DB_NAME" \
  -F c \
  -b \
  -v \
  -f "$BACKUP_FILE"

echo "✅ Backup created: $BACKUP_FILE"
```

**Verify backup**:
```bash
pg_restore --list "$BACKUP_FILE" | head -20
```

### Step 1.2: Document Current State

**Record current database stats**:

```bash
# Connect to local database
psql -U postgres -d chat_pgvector <<EOF
-- Count records per collection
SELECT 
  collection_name,
  COUNT(*) as record_count,
  pg_size_pretty(pg_total_relation_size('vector_documents')) as table_size
FROM vector_documents
GROUP BY collection_name
ORDER BY record_count DESC;

-- Check pgvector extension version
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- List all indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'vector_documents';
EOF
```

**Save output** to `backups/pre_migration_stats.txt`

### Step 1.3: Test Neon Connection

**Get Neon connection string** from Neon dashboard (format):
```
postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require
```

**Test connection**:
```bash
# Set Neon connection string
export NEON_DATABASE_URL="postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require"

# Test connection
psql "$NEON_DATABASE_URL" -c "SELECT version();"
```

**Expected output**: PostgreSQL version information

---

## Phase 2: Neon Database Setup

### Step 2.1: Create Database Schema in Neon

**Enable pgvector extension**:
```bash
psql "$NEON_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Verify extension**:
```bash
psql "$NEON_DATABASE_URL" -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

**Run migrations**:
```bash
# Run migration 001: Create tables
psql "$NEON_DATABASE_URL" -f storage/migrations/001_create_vector_tables.sql

# Run migration 002: Add JSONB indexes
psql "$NEON_DATABASE_URL" -f storage/migrations/002_add_jsonb_indexes.sql
```

**Verify schema**:
```bash
psql "$NEON_DATABASE_URL" <<EOF
-- Check table exists
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'vector_documents';

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'vector_documents';

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';
EOF
```

### Step 2.2: Test Empty Database

**Verify application can connect**:
```python
# test_neon_connection.py
import os
os.environ['DATABASE_URL'] = os.getenv('NEON_DATABASE_URL')

from storage.pg_connection import test_connection, ensure_pgvector_extension

if test_connection():
    print("✅ Neon connection successful")
    ensure_pgvector_extension()
    print("✅ pgvector extension ready")
else:
    print("❌ Connection failed")
```

---

## Phase 3: Data Migration

### Step 3.1: Export Data from Local Database

**Option A: Full Database Export** (Recommended)
```bash
# Export entire database
pg_dump \
  -U "$LOCAL_DB_USER" \
  -h "$LOCAL_DB_HOST" \
  -p "$LOCAL_DB_PORT" \
  -d "$LOCAL_DB_NAME" \
  -F c \
  -b \
  -v \
  -f backups/full_migration.dump
```

**Option B: Table-Only Export** (If you only want data)
```bash
# Export only vector_documents table data
pg_dump \
  -U "$LOCAL_DB_USER" \
  -h "$LOCAL_DB_HOST" \
  -p "$LOCAL_DB_PORT" \
  -d "$LOCAL_DB_NAME" \
  -t vector_documents \
  -F c \
  -b \
  -v \
  -f backups/vector_documents_only.dump
```

### Step 3.2: Import Data to Neon

**Restore data**:
```bash
# Restore full database
pg_restore \
  -d "$NEON_DATABASE_URL" \
  -v \
  --no-owner \
  --no-acl \
  backups/full_migration.dump

# Or restore table-only
pg_restore \
  -d "$NEON_DATABASE_URL" \
  -v \
  --no-owner \
  --no-acl \
  --table=vector_documents \
  backups/vector_documents_only.dump
```

**Note**: `--no-owner` and `--no-acl` flags are important for Neon (managed service)

### Step 3.3: Verify Data Migration

**Compare record counts**:
```bash
# Local database
psql -U postgres -d chat_pgvector -c "
  SELECT collection_name, COUNT(*) as count 
  FROM vector_documents 
  GROUP BY collection_name;
"

# Neon database
psql "$NEON_DATABASE_URL" -c "
  SELECT collection_name, COUNT(*) as count 
  FROM vector_documents 
  GROUP BY collection_name;
"
```

**Sample data verification**:
```bash
# Check a few sample records
psql "$NEON_DATABASE_URL" <<EOF
-- Sample applications
SELECT id, user_id, collection_name, 
       metadata->>'record_type' as record_type,
       created_at
FROM vector_documents 
WHERE collection_name = 'applications'
LIMIT 5;

-- Check vector embeddings exist
SELECT COUNT(*) as total_records,
       COUNT(embedding) as records_with_embeddings
FROM vector_documents;
EOF
```

---

## Phase 4: Application Configuration

### Step 4.1: Update Connection Configuration

**Update `storage/pg_connection.py`** to support SSL for Neon:

The current code already supports `DATABASE_URL`, but we should ensure SSL is properly handled:

```python
# storage/pg_connection.py - No changes needed!
# The code already supports DATABASE_URL with SSL parameters
# Neon connection strings include ?sslmode=require
```

**Verify SSL support**:
- Neon connection strings include `?sslmode=require`
- `psycopg2` automatically handles SSL when present in connection string

### Step 4.2: Update Environment Variables

**Local development** (`.env` file):
```bash
# Neon connection string (includes SSL)
DATABASE_URL=postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require

# Or individual components (if preferred)
POSTGRES_HOST=ep-xxx.us-east-2.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_DB=chat_pgvector
POSTGRES_USER=username
POSTGRES_PASSWORD=password
# Note: SSL will need to be added manually if using individual components
```

**Streamlit Cloud** (`.streamlit/secrets.toml`):
```toml
DATABASE_URL = "postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require"
```

**Production** (Environment variables):
```bash
export DATABASE_URL="postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require"
```

### Step 4.3: Test Application with Neon

**Run connection test**:
```python
# test_neon_app.py
import os
os.environ['DATABASE_URL'] = 'postgresql://...'  # Your Neon URL

from storage.pg_connection import test_connection, ensure_pgvector_extension
from storage.pg_vector_store import PgVectorStore

# Test connection
if test_connection():
    print("✅ Connection successful")
    ensure_pgvector_extension()
    
    # Test vector store operations
    store = PgVectorStore(collection_name="test", user_id="test_user")
    
    # Test add
    ids = store.add_texts(["Test document"], [{"test": True}])
    print(f"✅ Added document: {ids}")
    
    # Test search
    results = store.similarity_search("test", k=1)
    print(f"✅ Search results: {len(results)}")
    
    # Test delete
    store.delete(ids)
    print("✅ Deleted test document")
    
    print("\n✅ All tests passed!")
else:
    print("❌ Connection failed")
```

---

## Phase 5: Validation & Testing

### Step 5.1: Functional Testing

**Test all database operations**:

```python
# validate_neon_migration.py
import os
os.environ['DATABASE_URL'] = os.getenv('NEON_DATABASE_URL')

from storage.json_db import JobSearchDB
from storage.interview_db import InterviewDB
from storage.resume_db import ResumeDB

# Test JobSearchDB
print("Testing JobSearchDB...")
db = JobSearchDB()
apps = db.list_applications()
print(f"✅ Applications: {len(apps)}")

companies = db.list_companies()
print(f"✅ Companies: {len(companies)}")

# Test InterviewDB
print("\nTesting InterviewDB...")
interview_db = InterviewDB()
questions = interview_db.list_questions()
print(f"✅ Questions: {len(questions)}")

# Test ResumeDB
print("\nTesting ResumeDB...")
resume_db = ResumeDB()
resumes = resume_db.list_resumes()
print(f"✅ Resumes: {len(resumes)}")

print("\n✅ All database operations working!")
```

### Step 5.2: Performance Testing

**Test vector similarity search**:
```python
from storage.pg_vector_store import PgVectorStore
import time

store = PgVectorStore(collection_name="applications")

# Test search performance
start = time.time()
results = store.similarity_search("software engineer", k=10)
elapsed = time.time() - start

print(f"Search returned {len(results)} results in {elapsed:.2f}s")
print(f"Average: {elapsed/len(results)*1000:.2f}ms per result")
```

### Step 5.3: Data Integrity Check

**Compare critical data**:
```bash
# Create comparison script
cat > compare_databases.sh <<'EOF'
#!/bin/bash

LOCAL_URL="postgresql://postgres@localhost:5432/chat_pgvector"
NEON_URL="$NEON_DATABASE_URL"

echo "Comparing databases..."

# Count records
echo "Record counts:"
echo "Local:"
psql "$LOCAL_URL" -c "SELECT COUNT(*) FROM vector_documents;"
echo "Neon:"
psql "$NEON_URL" -c "SELECT COUNT(*) FROM vector_documents;"

# Check collections
echo "Collections:"
echo "Local:"
psql "$LOCAL_URL" -c "SELECT collection_name, COUNT(*) FROM vector_documents GROUP BY collection_name;"
echo "Neon:"
psql "$NEON_URL" -c "SELECT collection_name, COUNT(*) FROM vector_documents GROUP BY collection_name;"
EOF

chmod +x compare_databases.sh
./compare_databases.sh
```

---

## Phase 6: Cutover (Production Migration)

### Step 6.1: Pre-Cutover Checklist

- [ ] All data migrated and verified
- [ ] Application tested with Neon connection
- [ ] Performance benchmarks acceptable
- [ ] Backup of local database created
- [ ] Rollback plan documented
- [ ] Team notified of migration window

### Step 6.2: Update Production Environment

**Update environment variables**:
```bash
# Stop application (if running)
# Update DATABASE_URL to Neon connection string
# Restart application
```

**Monitor application logs** for errors

### Step 6.3: Post-Cutover Verification

**Monitor for 24-48 hours**:
- Application functionality
- Query performance
- Error rates
- Connection pool usage

---

## Phase 7: Cleanup (Optional)

### Step 7.1: Archive Local Database

**Keep local database as backup** (recommended for 30 days):
```bash
# Compress backup
gzip backups/local_db_*.dump

# Store in safe location
```

### Step 7.2: Update Documentation

**Update setup documentation**:
- `docs/PGVECTOR_SETUP.md` - Add Neon.tech setup option
- `README.md` - Update connection instructions
- `docs/DATABASE_SCHEMA.md` - Note Neon.tech compatibility

---

## Rollback Plan

If issues occur, rollback to local PostgreSQL:

### Quick Rollback Steps

1. **Revert environment variables**:
   ```bash
   export DATABASE_URL=postgresql://postgres@localhost:5432/chat_pgvector
   ```

2. **Restart application**

3. **Verify local database** is still running and accessible

### Data Recovery

If Neon data needs to be recovered:
```bash
# Export from Neon
pg_dump "$NEON_DATABASE_URL" -F c -b -f backups/neon_recovery.dump

# Restore to local
pg_restore -d postgresql://postgres@localhost:5432/chat_pgvector \
  --no-owner --no-acl backups/neon_recovery.dump
```

---

## Neon.tech Specific Considerations

### Connection Pooling

**Neon connection limits**:
- Free tier: Limited concurrent connections
- Paid tiers: Higher limits

**Current implementation**:
- Uses `ThreadedConnectionPool` with `maxconn=10`
- Should work well with Neon's connection limits
- Consider reducing `maxconn` if hitting limits

**Update if needed** (`storage/pg_connection.py`):
```python
_connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=5,  # Reduced for Neon free tier
    dsn=conn_string
)
```

### SSL/TLS

**Neon requires SSL**:
- Connection strings include `?sslmode=require`
- `psycopg2` handles SSL automatically
- No code changes needed

### Branching (Neon Feature)

**Create branches for testing**:
```bash
# Create branch via Neon dashboard or API
# Use branch connection string for staging/testing
```

### Performance Tuning

**Neon auto-scaling**:
- Automatically scales based on load
- No manual configuration needed
- Monitor via Neon dashboard

**Index optimization**:
- Existing indexes should work well
- Monitor query performance in Neon dashboard
- Adjust HNSW/IVFFlat parameters if needed

---

## Migration Script

**Automated migration script** (`scripts/migrate_to_neon.sh`):

```bash
#!/bin/bash
# Automated migration script: Local PostgreSQL → Neon.tech

set -e

# Configuration
LOCAL_DB_USER=${LOCAL_DB_USER:-postgres}
LOCAL_DB_NAME=${LOCAL_DB_NAME:-chat_pgvector}
LOCAL_DB_HOST=${LOCAL_DB_HOST:-localhost}
LOCAL_DB_PORT=${LOCAL_DB_PORT:-5432}

# Check Neon URL provided
if [ -z "$NEON_DATABASE_URL" ]; then
    echo "❌ Error: NEON_DATABASE_URL not set"
    echo "Set it with: export NEON_DATABASE_URL='postgresql://...'"
    exit 1
fi

echo "🚀 Starting migration to Neon.tech..."
echo ""

# Step 1: Backup local database
echo "📦 Step 1: Backing up local database..."
BACKUP_FILE="backups/local_db_$(date +%Y%m%d_%H%M%S).dump"
mkdir -p backups

pg_dump \
  -U "$LOCAL_DB_USER" \
  -h "$LOCAL_DB_HOST" \
  -p "$LOCAL_DB_PORT" \
  -d "$LOCAL_DB_NAME" \
  -F c \
  -b \
  -v \
  -f "$BACKUP_FILE"

echo "✅ Backup created: $BACKUP_FILE"
echo ""

# Step 2: Setup Neon database
echo "📦 Step 2: Setting up Neon database schema..."
psql "$NEON_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" || true
psql "$NEON_DATABASE_URL" -f storage/migrations/001_create_vector_tables.sql || true
psql "$NEON_DATABASE_URL" -f storage/migrations/002_add_jsonb_indexes.sql || true
echo "✅ Schema setup complete"
echo ""

# Step 3: Migrate data
echo "📦 Step 3: Migrating data..."
pg_restore \
  -d "$NEON_DATABASE_URL" \
  -v \
  --no-owner \
  --no-acl \
  "$BACKUP_FILE"

echo "✅ Data migration complete"
echo ""

# Step 4: Verify migration
echo "📦 Step 4: Verifying migration..."
LOCAL_COUNT=$(psql -U "$LOCAL_DB_USER" -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -d "$LOCAL_DB_NAME" -t -c "SELECT COUNT(*) FROM vector_documents;")
NEON_COUNT=$(psql "$NEON_DATABASE_URL" -t -c "SELECT COUNT(*) FROM vector_documents;")

echo "Local records: $LOCAL_COUNT"
echo "Neon records: $NEON_COUNT"

if [ "$LOCAL_COUNT" -eq "$NEON_COUNT" ]; then
    echo "✅ Record counts match!"
else
    echo "⚠️  Warning: Record counts don't match"
fi

echo ""
echo "✅ Migration complete!"
echo ""
echo "Next steps:"
echo "1. Update DATABASE_URL environment variable to: $NEON_DATABASE_URL"
echo "2. Test application with: python test_neon_app.py"
echo "3. Monitor application for 24-48 hours"
```

**Make executable**:
```bash
chmod +x scripts/migrate_to_neon.sh
```

---

## Troubleshooting

### Connection Issues

**Error**: `SSL connection required`
- **Solution**: Ensure connection string includes `?sslmode=require`

**Error**: `Connection timeout`
- **Solution**: Check Neon dashboard for service status, verify firewall settings

**Error**: `Too many connections`
- **Solution**: Reduce `maxconn` in connection pool, check Neon tier limits

### Data Migration Issues

**Error**: `Extension "vector" does not exist`
- **Solution**: Run `CREATE EXTENSION vector;` in Neon database

**Error**: `Permission denied`
- **Solution**: Use `--no-owner --no-acl` flags with `pg_restore`

**Error**: `Vector dimension mismatch`
- **Solution**: Verify embedding dimensions match between local and Neon

### Performance Issues

**Slow queries**:
- Check Neon dashboard for query performance
- Verify indexes exist: `SELECT indexname FROM pg_indexes WHERE tablename = 'vector_documents';`
- Consider Neon tier upgrade if needed

**Connection pool exhaustion**:
- Reduce `maxconn` in connection pool
- Check for connection leaks in application code

---

## Timeline Estimate

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1: Preparation | 30-60 min | Backup, documentation, Neon setup |
| Phase 2: Neon Setup | 15-30 min | Schema creation, extension setup |
| Phase 3: Data Migration | 10-60 min | Export/import (depends on data size) |
| Phase 4: Configuration | 15-30 min | Environment variables, testing |
| Phase 5: Validation | 30-60 min | Functional and performance testing |
| Phase 6: Cutover | 15-30 min | Production switchover |
| **Total** | **2-4 hours** | For typical migration |

**Large datasets** (>10GB): May take longer for data transfer

---

## Success Criteria

✅ **Migration successful when**:
- All data migrated (record counts match)
- Application connects successfully
- All CRUD operations work
- Vector similarity search works
- Performance acceptable (<2x slower than local)
- No errors in application logs

---

## Additional Resources

- [Neon.tech Documentation](https://neon.tech/docs)
- [Neon Migration Guides](https://neon.tech/docs/import/migrate-intro)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Migration Best Practices](https://www.postgresql.org/docs/current/backup.html)

---

## Next Steps After Migration

1. **Monitor performance** via Neon dashboard
2. **Set up automated backups** (Neon provides this)
3. **Explore Neon features**:
   - Database branching for testing
   - Time-travel queries
   - Auto-scaling
4. **Optimize queries** based on Neon analytics
5. **Consider Neon tier upgrade** if hitting limits

---

**Last Updated**: Migration plan created  
**Status**: Ready for execution

