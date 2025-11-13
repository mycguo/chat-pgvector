#!/bin/bash
# Automated migration script: Local PostgreSQL → Neon.tech
# Usage: NEON_DATABASE_URL="postgresql://..." ./scripts/migrate_to_neon.sh

set -e

# Configuration
LOCAL_DB_USER=${LOCAL_DB_USER:-postgres}
LOCAL_DB_NAME=${LOCAL_DB_NAME:-chat_pgvector}
LOCAL_DB_HOST=${LOCAL_DB_HOST:-localhost}
LOCAL_DB_PORT=${LOCAL_DB_PORT:-5432}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to find any available psql
find_psql() {
    # Check Postgres.app first
    if [ -d "/Applications/Postgres.app" ]; then
        for VERSION_DIR in /Applications/Postgres.app/Contents/Versions/*/bin; do
            if [ -f "$VERSION_DIR/psql" ]; then
                echo "$VERSION_DIR/psql"
                return 0
            fi
        done
    fi
    
    # Check Homebrew
    if command -v brew &> /dev/null; then
        for VERSION in 17 16 15; do
            PREFIX=$(brew --prefix "postgresql@${VERSION}" 2>/dev/null || echo "")
            if [ -n "$PREFIX" ] && [ -f "$PREFIX/bin/psql" ]; then
                echo "$PREFIX/bin/psql"
                return 0
            fi
        done
    fi
    
    # Check PATH
    if command -v psql &> /dev/null; then
        echo "psql"
        return 0
    fi
    
    return 1
}

# Function to detect PostgreSQL server version
detect_server_version() {
    PSQL_CMD=$(find_psql 2>/dev/null || echo "")
    if [ -z "$PSQL_CMD" ]; then
        return 1
    fi
    
    # Try to connect and get version
    VERSION=$($PSQL_CMD -U "$LOCAL_DB_USER" -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -d postgres -t -c "SELECT version();" 2>/dev/null | head -1)
    if [ -n "$VERSION" ]; then
        # Extract major version (e.g., "PostgreSQL 17.5" -> "17")
        MAJOR_VERSION=$(echo "$VERSION" | grep -oE 'PostgreSQL [0-9]+' | grep -oE '[0-9]+' | head -1)
        echo "$MAJOR_VERSION"
        return 0
    fi
    return 1
}

# Function to check for PostgreSQL tools
check_postgres_tools() {
    # First, try to detect server version
    SERVER_VERSION=$(detect_server_version 2>/dev/null || echo "")
    
    # Check for Postgres.app (common on macOS)
    if [ -d "/Applications/Postgres.app" ]; then
        # Find Postgres.app versions
        for VERSION_DIR in /Applications/Postgres.app/Contents/Versions/*/bin; do
            if [ -f "$VERSION_DIR/pg_dump" ] && [ -f "$VERSION_DIR/psql" ] && [ -f "$VERSION_DIR/pg_restore" ]; then
                # If we know server version, prefer matching version
                if [ -n "$SERVER_VERSION" ]; then
                    VERSION_NUM=$(basename "$(dirname "$VERSION_DIR")")
                    if [ "$VERSION_NUM" = "$SERVER_VERSION" ] || [ "$VERSION_NUM" = "${SERVER_VERSION}.0" ]; then
                        echo -e "${GREEN}✅ Found matching PostgreSQL tools via Postgres.app (version $VERSION_NUM)${NC}"
                        export PATH="$VERSION_DIR:$PATH"
                        return 0
                    fi
                fi
                # Use latest available version if no match
                echo -e "${GREEN}✅ Found PostgreSQL tools via Postgres.app at $VERSION_DIR${NC}"
                export PATH="$VERSION_DIR:$PATH"
                return 0
            fi
        done
    fi
    
    # Check for Homebrew PostgreSQL installation (common on macOS)
    if command -v brew &> /dev/null; then
        # Try to match server version first
        if [ -n "$SERVER_VERSION" ]; then
            POSTGRES_PREFIX=$(brew --prefix "postgresql@${SERVER_VERSION}" 2>/dev/null || echo "")
            if [ -n "$POSTGRES_PREFIX" ] && [ -f "$POSTGRES_PREFIX/bin/pg_dump" ]; then
                echo -e "${GREEN}✅ Found matching PostgreSQL tools via Homebrew (version ${SERVER_VERSION})${NC}"
                export PATH="$POSTGRES_PREFIX/bin:$PATH"
                return 0
            fi
        fi
        
        # Fallback to available Homebrew versions (prefer newer)
        POSTGRES_PREFIX=$(brew --prefix postgresql@17 2>/dev/null || \
                         brew --prefix postgresql@16 2>/dev/null || \
                         brew --prefix postgresql@15 2>/dev/null || \
                         brew --prefix postgresql 2>/dev/null || \
                         echo "")
        if [ -n "$POSTGRES_PREFIX" ] && [ -f "$POSTGRES_PREFIX/bin/pg_dump" ]; then
            echo -e "${GREEN}✅ Found PostgreSQL tools via Homebrew at $POSTGRES_PREFIX${NC}"
            export PATH="$POSTGRES_PREFIX/bin:$PATH"
            return 0
        fi
    fi
    
    # Check if tools are in PATH
    if command -v pg_dump &> /dev/null && \
       command -v psql &> /dev/null && \
       command -v pg_restore &> /dev/null; then
        return 0
    fi
    
    return 1
}

# Function to verify tool version compatibility
verify_tool_compatibility() {
    if ! command -v pg_dump &> /dev/null; then
        return 1
    fi
    
    # Get pg_dump version
    DUMP_VERSION_FULL=$(pg_dump --version 2>/dev/null | head -1 || echo "")
    DUMP_VERSION=$(echo "$DUMP_VERSION_FULL" | grep -oE '[0-9]+\.[0-9]+' | head -1)
    DUMP_MAJOR=$(echo "$DUMP_VERSION" | cut -d. -f1)
    
    # Get server version if available
    SERVER_VERSION=$(detect_server_version 2>/dev/null || echo "")
    if [ -n "$SERVER_VERSION" ] && [ -n "$DUMP_MAJOR" ]; then
        if [ "$DUMP_MAJOR" -lt "$SERVER_VERSION" ]; then
            echo -e "${RED}⚠️  Version mismatch detected${NC}"
            echo "  Server version: PostgreSQL $SERVER_VERSION"
            echo "  pg_dump version: $DUMP_VERSION (major: $DUMP_MAJOR)"
            echo ""
            echo "pg_dump must be same or newer version than server."
            echo ""
            return 1
        fi
    fi
    
    return 0
}

# Check for PostgreSQL tools
if ! check_postgres_tools; then
    echo -e "${RED}❌ PostgreSQL client tools not found${NC}"
    echo ""
    echo "Required tools: pg_dump, psql, pg_restore"
    echo ""
    echo "Install PostgreSQL client tools:"
    echo ""
    echo "macOS (Homebrew):"
    echo "  brew install postgresql@17  # or postgresql@16"
    echo ""
    echo "macOS (Postgres.app):"
    echo "  Download from: https://postgresapp.com/"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt install postgresql-client-17  # or postgresql-client-16"
    echo ""
    echo "Or download from: https://www.postgresql.org/download/"
    exit 1
fi

# Verify version compatibility
if ! verify_tool_compatibility; then
    SERVER_VERSION=$(detect_server_version 2>/dev/null || echo "unknown")
    echo -e "${YELLOW}To fix version mismatch:${NC}"
    echo ""
    
    # Check if Postgres.app has matching version
    if [ -d "/Applications/Postgres.app" ] && [ "$SERVER_VERSION" != "unknown" ]; then
        POSTGRES_APP_PATH="/Applications/Postgres.app/Contents/Versions/${SERVER_VERSION}/bin"
        if [ -f "$POSTGRES_APP_PATH/pg_dump" ]; then
            echo -e "${GREEN}Found matching Postgres.app tools!${NC}"
            echo "Run this command and try again:"
            echo ""
            echo "  export PATH=\"$POSTGRES_APP_PATH:\$PATH\""
            echo "  ./scripts/migrate_to_neon.sh"
            echo ""
        else
            echo "Postgres.app detected but version ${SERVER_VERSION} tools not found."
            echo "Available versions in Postgres.app:"
            ls -d /Applications/Postgres.app/Contents/Versions/*/bin 2>/dev/null | sed 's|.*/Versions/\([^/]*\)/bin|  - \1|' || echo "  (none found)"
            echo ""
            echo "Use latest available version:"
            LATEST=$(ls -d /Applications/Postgres.app/Contents/Versions/*/bin 2>/dev/null | tail -1)
            if [ -n "$LATEST" ]; then
                echo "  export PATH=\"$LATEST:\$PATH\""
            fi
        fi
    else
        if [ "$SERVER_VERSION" != "unknown" ]; then
            echo "Install matching version via Homebrew:"
            echo "  brew install postgresql@${SERVER_VERSION}"
        else
            echo "Could not detect server version. Install PostgreSQL 17 client tools:"
            echo "  brew install postgresql@17"
        fi
    fi
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo -e "${GREEN}✅ PostgreSQL tools found${NC}"
DUMP_VERSION=$(pg_dump --version 2>/dev/null | head -1 || echo "unknown")
echo "  pg_dump: $(which pg_dump) ($DUMP_VERSION)"
echo "  psql: $(which psql)"
echo "  pg_restore: $(which pg_restore)"
echo ""

# Check Neon URL provided
if [ -z "$NEON_DATABASE_URL" ]; then
    echo -e "${RED}❌ Error: NEON_DATABASE_URL not set${NC}"
    echo "Set it with: export NEON_DATABASE_URL='postgresql://...'"
    echo ""
    echo "Get your Neon connection string from: https://console.neon.tech/"
    exit 1
fi

echo -e "${GREEN}🚀 Starting migration to Neon.tech...${NC}"
echo ""

# Step 1: Backup local database
echo -e "${YELLOW}📦 Step 1: Backing up local database...${NC}"
BACKUP_FILE="backups/local_db_$(date +%Y%m%d_%H%M%S).dump"
mkdir -p backups

# Check if local database is accessible (if pg_isready is available)
if command -v pg_isready &> /dev/null; then
    if ! pg_isready -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" &>/dev/null; then
        echo -e "${RED}❌ Local PostgreSQL server is not running or not accessible${NC}"
        echo "  Host: $LOCAL_DB_HOST"
        echo "  Port: $LOCAL_DB_PORT"
        echo ""
        echo "Start PostgreSQL:"
        echo "  macOS: brew services start postgresql@16"
        echo "  Linux: sudo systemctl start postgresql"
        exit 1
    fi
    echo -e "${GREEN}✅ Local PostgreSQL server is accessible${NC}"
fi

echo "Creating backup..."
if pg_dump \
  -U "$LOCAL_DB_USER" \
  -h "$LOCAL_DB_HOST" \
  -p "$LOCAL_DB_PORT" \
  -d "$LOCAL_DB_NAME" \
  -F c \
  -b \
  -v \
  -f "$BACKUP_FILE" 2>&1; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup created: $BACKUP_FILE (${BACKUP_SIZE})${NC}"
else
    echo -e "${RED}❌ Backup failed${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Database doesn't exist: Create it with 'createdb $LOCAL_DB_NAME'"
    echo "  - Wrong credentials: Check LOCAL_DB_USER environment variable"
    echo "  - Connection refused: Ensure PostgreSQL is running"
    exit 1
fi
echo ""

# Step 2: Detect vector dimension from local database
echo -e "${YELLOW}📦 Step 2: Detecting vector dimension...${NC}"

# Get vector dimension from local database
VECTOR_DIM=$(psql -U "$LOCAL_DB_USER" -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -d "$LOCAL_DB_NAME" -t -c "
    SELECT format_type(atttypid, atttypmod) 
    FROM pg_attribute 
    WHERE attrelid = 'vector_documents'::regclass 
    AND attname = 'embedding';
" 2>/dev/null | grep -oE '[0-9]+' | head -1)

if [ -z "$VECTOR_DIM" ]; then
    echo -e "${YELLOW}⚠️  Could not detect vector dimension, using default 768${NC}"
    VECTOR_DIM=768
else
    echo -e "${GREEN}✅ Detected vector dimension: $VECTOR_DIM${NC}"
fi
echo ""

# Step 3: Setup Neon database schema
echo -e "${YELLOW}📦 Step 3: Setting up Neon database schema...${NC}"

# Enable pgvector extension
if psql "$NEON_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1 >/dev/null; then
    echo -e "${GREEN}✅ pgvector extension enabled${NC}"
fi

# Drop existing table if it exists (to avoid dimension mismatch)
echo "Checking for existing table..."
TABLE_EXISTS=$(psql "$NEON_DATABASE_URL" -t -c "
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vector_documents'
    );
" 2>/dev/null | tr -d ' ')

if [ "$TABLE_EXISTS" = "t" ]; then
    echo -e "${YELLOW}⚠️  Table vector_documents already exists${NC}"
    echo "Dropping existing table to ensure correct vector dimension..."
    psql "$NEON_DATABASE_URL" -c "DROP TABLE IF EXISTS vector_documents CASCADE;" 2>&1 >/dev/null
    echo -e "${GREEN}✅ Dropped existing table${NC}"
fi

# Create table with correct vector dimension
echo "Creating table with vector($VECTOR_DIM)..."
TABLE_SQL="
SET search_path TO public;

CREATE TABLE vector_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL DEFAULT 'personal_assistant',
    text TEXT NOT NULL,
    embedding vector($VECTOR_DIM) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_vector_documents_user_collection 
    ON vector_documents(user_id, collection_name);
"

TABLE_OUTPUT=$(echo "$TABLE_SQL" | psql "$NEON_DATABASE_URL" 2>&1)
TABLE_EXIT=$?

if [ $TABLE_EXIT -eq 0 ]; then
    echo -e "${GREEN}✅ Table created${NC}"
else
    echo -e "${RED}❌ Failed to create table${NC}"
    echo "$TABLE_OUTPUT" | tail -5
    exit 1
fi

# Drop any existing indexes before creating new ones
echo "Cleaning up any existing indexes..."
psql "$NEON_DATABASE_URL" -c "
    DROP INDEX IF EXISTS idx_vector_documents_embedding_hnsw;
    DROP INDEX IF EXISTS idx_vector_documents_embedding_ivfflat;
    DROP INDEX IF EXISTS idx_vector_documents_metadata_gin;
" 2>&1 >/dev/null

# Create vector index based on dimension
if [ "$VECTOR_DIM" -le 1000 ]; then
    if psql "$NEON_DATABASE_URL" -c "
        CREATE INDEX idx_vector_documents_embedding_hnsw 
        ON vector_documents USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    " 2>&1 >/dev/null; then
        echo -e "${GREEN}✅ Created HNSW index${NC}"
    else
        echo -e "${YELLOW}⚠️  HNSW index creation failed${NC}"
    fi
elif [ "$VECTOR_DIM" -le 2000 ]; then
    if psql "$NEON_DATABASE_URL" -c "
        CREATE INDEX idx_vector_documents_embedding_ivfflat 
        ON vector_documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    " 2>&1 >/dev/null; then
        echo -e "${GREEN}✅ Created IVFFlat index${NC}"
    else
        echo -e "${YELLOW}⚠️  IVFFlat index creation failed${NC}"
    fi
fi

# Create GIN index for metadata
if psql "$NEON_DATABASE_URL" -c "
    CREATE INDEX idx_vector_documents_metadata_gin 
    ON vector_documents USING gin (metadata);
" 2>&1 >/dev/null; then
    echo -e "${GREEN}✅ Created GIN index${NC}"
else
    echo -e "${YELLOW}⚠️  GIN index creation failed${NC}"
fi

# Create trigger function and trigger
TRIGGER_SQL="
SET search_path TO public;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS \$\$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
\$\$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_vector_documents_updated_at ON vector_documents;
CREATE TRIGGER update_vector_documents_updated_at 
    BEFORE UPDATE ON vector_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"

TRIGGER_OUTPUT=$(echo "$TRIGGER_SQL" | psql "$NEON_DATABASE_URL" 2>&1)
TRIGGER_EXIT=$?

if [ $TRIGGER_EXIT -eq 0 ]; then
    echo -e "${GREEN}✅ Created trigger${NC}"
else
    echo -e "${YELLOW}⚠️  Trigger creation failed (may already exist)${NC}"
    echo "$TRIGGER_OUTPUT" | grep -i error | head -2 || true
fi

# Run migration 002 for JSONB indexes (if exists)
MIGRATION_DIR="storage/migrations"
if [ -f "$MIGRATION_DIR/002_add_jsonb_indexes.sql" ]; then
    if psql "$NEON_DATABASE_URL" -f "$MIGRATION_DIR/002_add_jsonb_indexes.sql" 2>&1 >/dev/null; then
        echo -e "${GREEN}✅ Migration 002 complete${NC}"
    fi
fi

echo -e "${GREEN}✅ Schema setup complete${NC}"
echo ""

# Step 4: Migrate data (data only, schema already created)
echo -e "${YELLOW}📦 Step 4: Migrating data...${NC}"
echo "Restoring data (schema already exists)..."

# Verify table exists before restoring data
TABLE_CHECK=$(psql "$NEON_DATABASE_URL" -t -c "
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vector_documents'
    );
" 2>/dev/null | tr -d ' ')

if [ "$TABLE_CHECK" != "t" ]; then
    echo -e "${RED}❌ Error: vector_documents table does not exist in Neon${NC}"
    echo "Schema setup may have failed. Please check Step 3 output above."
    exit 1
fi

# Run pg_restore with data-only flag
RESTORE_OUTPUT=$(pg_restore \
  -d "$NEON_DATABASE_URL" \
  --data-only \
  --no-owner \
  --no-acl \
  -v \
  "$BACKUP_FILE" 2>&1)

RESTORE_EXIT_CODE=$?

# Wait a moment for data to be committed
sleep 1

# Check if data was restored (even if there were warnings)
NEON_COUNT=$(psql "$NEON_DATABASE_URL" -t -c "SELECT COUNT(*) FROM vector_documents;" 2>/dev/null | tr -d ' ' || echo "0")
NEON_COUNT=${NEON_COUNT:-0}

# Verify table still exists after restore
TABLE_CHECK_AFTER=$(psql "$NEON_DATABASE_URL" -t -c "
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vector_documents'
    );
" 2>/dev/null | tr -d ' ')

if [ "$TABLE_CHECK_AFTER" != "t" ]; then
    echo -e "${RED}❌ Error: Table was dropped during data migration${NC}"
    echo "This should not happen. Check Neon logs for errors."
    exit 1
fi

if [ "$NEON_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✅ Data migration complete (${NEON_COUNT} records restored)${NC}"
    # Show warnings if any (but don't fail)
    if echo "$RESTORE_OUTPUT" | grep -q "WARNING\|ERROR"; then
        echo -e "${YELLOW}⚠️  Some warnings occurred (may be expected):${NC}"
        echo "$RESTORE_OUTPUT" | grep -E "WARNING|ERROR" | head -5
    fi
elif [ "$RESTORE_EXIT_CODE" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Data migration completed but no records found${NC}"
    echo "This may be expected if the local database is empty."
else
    echo -e "${RED}❌ Data migration failed${NC}"
    echo "Exit code: $RESTORE_EXIT_CODE"
    echo ""
    echo "Last 20 lines of restore output:"
    echo "$RESTORE_OUTPUT" | tail -20
    exit 1
fi
echo ""

# Step 5: Verify migration
echo -e "${YELLOW}📦 Step 5: Verifying migration...${NC}"

# Check if Neon table exists
NEON_TABLE_EXISTS=$(psql "$NEON_DATABASE_URL" -t -c "
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vector_documents'
    );
" 2>/dev/null | tr -d ' ')

if [ "$NEON_TABLE_EXISTS" != "t" ]; then
    echo -e "${RED}❌ Error: vector_documents table does not exist in Neon${NC}"
    echo "The data migration may have failed. Check the error messages above."
    exit 1
fi

# Get record counts
LOCAL_COUNT=$(psql -U "$LOCAL_DB_USER" -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -d "$LOCAL_DB_NAME" -t -c "SELECT COUNT(*) FROM vector_documents;" 2>/dev/null | tr -d ' ' || echo "0")
NEON_COUNT=$(psql "$NEON_DATABASE_URL" -t -c "SELECT COUNT(*) FROM vector_documents;" 2>/dev/null | tr -d ' ' || echo "0")

# Ensure counts are numeric
LOCAL_COUNT=${LOCAL_COUNT:-0}
NEON_COUNT=${NEON_COUNT:-0}

echo "Local records: $LOCAL_COUNT"
echo "Neon records: $NEON_COUNT"

# Compare counts (handle empty strings)
if [ -n "$LOCAL_COUNT" ] && [ -n "$NEON_COUNT" ] && [ "$LOCAL_COUNT" -eq "$NEON_COUNT" ] 2>/dev/null; then
    echo -e "${GREEN}✅ Record counts match!${NC}"
elif [ "$NEON_COUNT" -eq "0" ]; then
    echo -e "${RED}❌ Error: No records migrated to Neon${NC}"
    echo "The data migration may have failed. Check Step 4 output above."
    exit 1
else
    echo -e "${YELLOW}⚠️  Warning: Record counts don't match${NC}"
    echo "  Local: $LOCAL_COUNT"
    echo "  Neon: $NEON_COUNT"
    echo ""
    echo "This may be expected if:"
    echo "  - Some records failed to migrate"
    echo "  - Data was modified during migration"
    echo "  - Partial migration occurred"
fi

# Check collections
echo ""
echo "Collection breakdown:"
COLLECTION_OUTPUT=$(psql "$NEON_DATABASE_URL" -c "SELECT collection_name, COUNT(*) as count FROM vector_documents GROUP BY collection_name ORDER BY count DESC;" 2>&1)
if echo "$COLLECTION_OUTPUT" | grep -q "ERROR"; then
    echo -e "${RED}❌ Error querying collections${NC}"
    echo "$COLLECTION_OUTPUT" | grep -i error
else
    echo "$COLLECTION_OUTPUT"
fi

echo ""
echo -e "${GREEN}✅ Migration complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Update DATABASE_URL environment variable:"
echo "   export DATABASE_URL=\"$NEON_DATABASE_URL\""
echo ""
echo "2. Test application connection:"
echo "   python -c \"from storage.pg_connection import test_connection; print('✅ Connected' if test_connection() else '❌ Failed')\""
echo ""
echo "3. Monitor application for 24-48 hours"
echo ""
echo "Backup saved at: $BACKUP_FILE"

