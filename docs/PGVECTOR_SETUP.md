# Neon.tech (PostgreSQL + pgvector) Setup Guide

## Quick Start

**This application uses Neon.tech (serverless PostgreSQL) as the primary database.**

You have three options:
- **Neon.tech** (serverless, **recommended and primary**) - See [NEON_MIGRATION_PLAN.md](NEON_MIGRATION_PLAN.md)
- **Docker** (quick local setup for development)
- **Local PostgreSQL** (for local development only)

### Option A: Neon.tech (Serverless PostgreSQL) ⭐ **PRIMARY**

**This is the recommended and primary database for this application.**

Neon.tech provides a fully managed PostgreSQL service with pgvector support, auto-scaling, and a generous free tier.

**Quick Setup:**
1. Sign up at [neon.tech](https://neon.tech/)
2. Create a new project and database
3. Get your connection string from the dashboard
4. Set `NEON_DATABASE_URL` in Streamlit secrets or environment variable (includes SSL)

**Connection String Format:**
```
postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require
```

**For detailed migration guide**, see [NEON_MIGRATION_PLAN.md](NEON_MIGRATION_PLAN.md)

---

### Option B: Docker Setup (Local Development Only)

**Note**: This is for local development. Production uses Neon.tech.

If you have Docker installed, use the automated script:
```bash
./setup_postgres.sh
```

Or manually:
```bash
docker run -d \
  --name pgvector-db \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=chat_pgvector \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### Option C: Local PostgreSQL (Local Development Only)

**Note**: This is for local development. Production uses Neon.tech.

**Only use this if you already have PostgreSQL installed locally.**

#### Step 1: Install PostgreSQL and pgvector

**macOS (Homebrew):**
```bash
# Install PostgreSQL
brew install postgresql@16

# Install pgvector extension
brew install pgvector

# Start PostgreSQL service
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
# Install PostgreSQL with pgvector
sudo apt update
sudo apt install postgresql-16 postgresql-16-pgvector

# Start PostgreSQL service
sudo systemctl start postgresql
```

**From Source:**
```bash
# Install PostgreSQL first, then:
git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

#### Step 2: Setup Database

Use the automated script:
```bash
./setup_postgres_local.sh
```

Or manually:
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE chat_pgvector;

# Connect to database
\c chat_pgvector

# Enable pgvector extension
CREATE EXTENSION vector;

# Exit psql
\q
```

### 3. Configure Environment Variables

**For Neon.tech:**
```bash
# Get connection string from Neon dashboard (includes SSL)
export NEON_DATABASE_URL="postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require"
```

**Or set in Streamlit secrets** (`.streamlit/secrets.toml`):
```toml
NEON_DATABASE_URL = "postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require"
```

**For Local PostgreSQL (no password by default on macOS) - Development Only:**
```bash
# Option 1: Full connection string (no password needed if using peer auth)
export NEON_DATABASE_URL=postgresql://postgres@localhost:5432/chat_pgvector

# Option 2: Individual components
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=chat_pgvector
export POSTGRES_USER=postgres
# POSTGRES_PASSWORD not needed if using peer authentication
```

**For Docker or password-protected PostgreSQL - Development Only:**
```bash
export NEON_DATABASE_URL=postgresql://postgres:your_password@localhost:5432/chat_pgvector
# Or individual components with password
export POSTGRES_PASSWORD=your_password
```

**For Streamlit Cloud**, add to `.streamlit/secrets.toml`:
```toml
NEON_DATABASE_URL = "postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require"
```

### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 6. Test Connection

```python
from storage.pg_connection import test_connection, ensure_pgvector_extension

# Test connection
if test_connection():
    print("✅ Database connection successful")
    ensure_pgvector_extension()
    print("✅ pgvector extension ready")
else:
    print("❌ Database connection failed")
```

## Usage

### Basic Usage

```python
from storage.pg_vector_store import PgVectorStore

# Initialize vector store
store = PgVectorStore(
    collection_name="personal_assistant",
    user_id="user123"  # Optional, will auto-detect from Streamlit
)

# Add texts
ids = store.add_texts(
    ["Document 1", "Document 2"],
    metadatas=[{"source": "file1"}, {"source": "file2"}]
)

# Search
results = store.similarity_search("query text", k=5)

# Search with scores
results_with_scores = store.similarity_search_with_score("query", k=5)

# Delete
store.delete(ids)

# Get stats
stats = store.get_collection_stats()
```

### Migration from SimpleVectorStore

The `PgVectorStore` maintains the same interface as `SimpleVectorStore`, so you can replace it directly:

```python
# Old
from simple_vector_store import SimpleVectorStore
store = SimpleVectorStore()

# New
from storage.pg_vector_store import PgVectorStore
store = PgVectorStore()
```

## Troubleshooting

### Connection Errors

**Error**: `Connection refused` or `could not connect to server`
- Check PostgreSQL is running: `pg_isready` or `docker ps`
- Verify connection string/credentials
- Check firewall/network settings

### Extension Errors

**Error**: `extension "vector" does not exist`
- Ensure pgvector is installed: `SELECT * FROM pg_available_extensions WHERE name = 'vector';`
- Run: `CREATE EXTENSION vector;` in your database

### Vector Dimension Mismatch

**Error**: `vector dimension mismatch`
- Google `gemini-embedding-001` produces 768-dimensional vectors
- Ensure table schema uses `vector(768)`
- Check migration SQL was run correctly

### Performance Issues

- **Slow queries**: Ensure HNSW index exists
- **Large datasets**: Consider tuning HNSW parameters (m, ef_construction)
- **Connection pool**: Adjust pool size in `pg_connection.py`

## Architecture

### Database Schema

```
vector_documents
├── id (UUID, primary key)
├── user_id (VARCHAR, indexed)
├── collection_name (VARCHAR, indexed)
├── text (TEXT)
├── embedding (vector(768), HNSW indexed)
├── metadata (JSONB, GIN indexed)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

### Indexes

- **User/Collection Index**: Fast filtering by user and collection
- **HNSW Index**: Fast approximate nearest neighbor search
- **GIN Index**: Fast JSONB metadata queries

## Production Considerations

1. **Connection Pooling**: Already implemented with ThreadedConnectionPool
2. **SSL**: Add `sslmode=require` to connection string for production
3. **Backups**: Set up regular PostgreSQL backups
4. **Monitoring**: Monitor query performance and index usage
5. **Scaling**: Consider read replicas for high read loads

## Migration from File-Based Storage

See `docs/PGVECTOR_MIGRATION_PLAN.md` for detailed migration steps.

