#!/bin/bash
# Install PostgreSQL and pgvector on macOS using Homebrew

set -e

echo "🍺 Installing PostgreSQL and pgvector on macOS..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install Homebrew first:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "✅ Homebrew found"

# Install PostgreSQL
echo ""
echo "📦 Installing PostgreSQL..."
brew install postgresql@16

# Install pgvector
echo ""
echo "📦 Installing pgvector..."
brew install pgvector

# Start PostgreSQL service
echo ""
echo "🚀 Starting PostgreSQL service..."
brew services start postgresql@16

# Wait a moment for PostgreSQL to start
echo "⏳ Waiting for PostgreSQL to start..."
sleep 3

# Check if PostgreSQL is ready
if pg_isready -q 2>/dev/null; then
    echo "✅ PostgreSQL is running!"
else
    echo "⚠️  PostgreSQL may still be starting. Please wait a moment and run:"
    echo "   pg_isready"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Run: ./setup_postgres_local.sh"
echo "  2. Or manually create database:"
echo "     psql postgres -c 'CREATE DATABASE chat_pgvector;'"
echo "     psql chat_pgvector -c 'CREATE EXTENSION vector;'"
echo ""
echo "To stop PostgreSQL: brew services stop postgresql@16"
echo "To start PostgreSQL: brew services start postgresql@16"

