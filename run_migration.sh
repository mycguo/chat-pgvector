#!/bin/bash
# Helper script to run migration with proper environment setup

set -e

echo "🚀 Running Vector Store Migration to PostgreSQL"
echo ""

# Set database URL if not already set
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL=postgresql://postgres@localhost:5432/chat_pgvector
    echo "Using default DATABASE_URL: $DATABASE_URL"
else
    echo "Using DATABASE_URL from environment"
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run migration script with all arguments passed through
python storage/migrations/migrate_to_pgvector.py "$@"

