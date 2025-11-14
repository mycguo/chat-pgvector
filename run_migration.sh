#!/bin/bash
# Helper script to run migration with proper environment setup

set -e

echo "🚀 Running Vector Store Migration to PostgreSQL"
echo ""

# Check if NEON_DATABASE_URL is set (required for Neon.tech)
if [ -z "$NEON_DATABASE_URL" ]; then
    # Check for legacy DATABASE_URL
    if [ -n "$DATABASE_URL" ]; then
        echo "⚠️  Using legacy DATABASE_URL. Consider migrating to NEON_DATABASE_URL."
        export NEON_DATABASE_URL="$DATABASE_URL"
    else
        echo "⚠️  WARNING: NEON_DATABASE_URL not set!"
        echo ""
        echo "This application uses Neon.tech (serverless PostgreSQL)."
        echo "Please set NEON_DATABASE_URL with your Neon connection string:"
        echo ""
        echo "  export NEON_DATABASE_URL=\"postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require\""
        echo ""
        echo "For local development only, you can use:"
        echo "  export NEON_DATABASE_URL=postgresql://postgres@localhost:5432/chat_pgvector"
        echo ""
        exit 1
    fi
else
    echo "Using NEON_DATABASE_URL from environment"
    # Warn if pointing to localhost
    if echo "$NEON_DATABASE_URL" | grep -q "localhost\|127.0.0.1"; then
        echo "⚠️  WARNING: NEON_DATABASE_URL points to localhost. This application uses Neon.tech."
    fi
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run migration script with all arguments passed through
python storage/migrations/migrate_to_pgvector.py "$@"

