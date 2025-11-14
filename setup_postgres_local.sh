#!/bin/bash
# Setup script for local PostgreSQL with pgvector (non-Docker)

set -e

echo "🚀 Setting up PostgreSQL with pgvector (local installation)..."

# Check for Homebrew PostgreSQL installation (common on macOS)
if command -v brew &> /dev/null; then
    POSTGRES_PREFIX=$(brew --prefix postgresql@16 2>/dev/null || brew --prefix postgresql@15 2>/dev/null || brew --prefix postgresql 2>/dev/null || echo "")
    if [ -n "$POSTGRES_PREFIX" ] && [ -f "$POSTGRES_PREFIX/bin/psql" ]; then
        echo "✅ Found PostgreSQL via Homebrew at $POSTGRES_PREFIX"
        export PATH="$POSTGRES_PREFIX/bin:$PATH"
    fi
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL client (psql) not found"
    echo ""
    echo "Please install PostgreSQL first:"
    echo ""
    echo "macOS (Homebrew):"
    echo "  brew install postgresql@16"
    echo "  brew services start postgresql@16"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt install postgresql-16 postgresql-16-pgvector"
    echo ""
    echo "Or download from: https://www.postgresql.org/download/"
    exit 1
fi

echo "✅ PostgreSQL client found: $(which psql)"

# Check if PostgreSQL server is running
if ! pg_isready -q 2>/dev/null; then
    echo "⚠️  PostgreSQL server doesn't appear to be running"
    echo ""
    echo "Start PostgreSQL:"
    echo "  macOS: brew services start postgresql@16"
    echo "  Linux: sudo systemctl start postgresql"
    echo ""
    read -p "Do you want to start PostgreSQL now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v brew &> /dev/null; then
            echo "🚀 Starting PostgreSQL service..."
            brew services start postgresql@16 2>/dev/null || brew services start postgresql@15 2>/dev/null || brew services start postgresql 2>/dev/null
            echo "⏳ Waiting for PostgreSQL to start..."
            sleep 3
        else
            echo "Please start PostgreSQL manually and run this script again"
            exit 1
        fi
    else
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Get database connection details
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-chat_pgvector}

echo ""
echo "Using connection details:"
echo "  User: $POSTGRES_USER"
echo "  Database: $POSTGRES_DB"
echo ""

# Check if database exists
if psql -U "$POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -qw "$POSTGRES_DB"; then
    echo "✅ Database '$POSTGRES_DB' already exists"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Dropping existing database..."
        psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
    else
        echo "Using existing database"
    fi
fi

# Create database if it doesn't exist
if ! psql -U "$POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -qw "$POSTGRES_DB"; then
    echo "📦 Creating database '$POSTGRES_DB'..."
    psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"
    echo "✅ Database created"
fi

# Enable pgvector extension
echo "📦 Enabling pgvector extension..."
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;" || {
    echo "❌ Failed to create pgvector extension"
    echo ""
    echo "Install pgvector:"
    echo "  macOS: brew install pgvector"
    echo "  Ubuntu/Debian: sudo apt install postgresql-16-pgvector"
    echo "  Or build from source: https://github.com/pgvector/pgvector"
    exit 1
}

echo "✅ pgvector extension enabled"

# Run migration
MIGRATION_FILE="storage/migrations/001_create_vector_tables.sql"
if [ -f "$MIGRATION_FILE" ]; then
    echo "📋 Running migration..."
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$MIGRATION_FILE"
    echo "✅ Migration complete"
else
    echo "⚠️  Migration file not found: $MIGRATION_FILE"
    echo "   Tables will be created automatically on first use"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Connection details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: $POSTGRES_DB"
echo "  User: $POSTGRES_USER"
echo ""
echo "Set these environment variables:"
echo "  export POSTGRES_HOST=localhost"
echo "  export POSTGRES_PORT=5432"
echo "  export POSTGRES_DB=$POSTGRES_DB"
echo "  export POSTGRES_USER=$POSTGRES_USER"
echo ""
echo "Or use connection string (for local development only):"
echo "  export NEON_DATABASE_URL=postgresql://$POSTGRES_USER@localhost:5432/$POSTGRES_DB"
echo ""
echo "Note: For production, use Neon.tech and set NEON_DATABASE_URL with your Neon connection string."

