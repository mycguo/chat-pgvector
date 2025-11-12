#!/bin/bash
# Setup script for PostgreSQL with pgvector using Docker
# For local PostgreSQL installation, use setup_postgres_local.sh instead

set -e

echo "🚀 Setting up PostgreSQL with pgvector (Docker)..."
echo ""
echo "Note: If you prefer local PostgreSQL installation, use:"
echo "  ./setup_postgres_local.sh"
echo ""

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "✅ Docker found"
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^pgvector-db$"; then
        echo "📦 Container 'pgvector-db' already exists"
        read -p "Do you want to remove and recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🗑️  Removing existing container..."
            docker stop pgvector-db 2>/dev/null || true
            docker rm pgvector-db 2>/dev/null || true
        else
            echo "▶️  Starting existing container..."
            docker start pgvector-db
            echo "✅ Container started. Database should be ready at localhost:5432"
            exit 0
        fi
    fi
    
    # Set default password if not provided
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    POSTGRES_DB=${POSTGRES_DB:-chat_pgvector}
    
    echo "🐳 Starting PostgreSQL container with pgvector..."
    docker run -d \
        --name pgvector-db \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e POSTGRES_DB="$POSTGRES_DB" \
        -p 5432:5432 \
        pgvector/pgvector:pg16
    
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Wait for PostgreSQL to be ready
    for i in {1..30}; do
        if docker exec pgvector-db pg_isready -U postgres > /dev/null 2>&1; then
            echo "✅ PostgreSQL is ready!"
            break
        fi
        echo "   Waiting... ($i/30)"
        sleep 1
    done
    
    # Enable pgvector extension
    echo "📦 Enabling pgvector extension..."
    docker exec pgvector-db psql -U postgres -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;" || true
    
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Connection details:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: $POSTGRES_DB"
    echo "  User: postgres"
    echo "  Password: $POSTGRES_PASSWORD"
    echo ""
    echo "Set these environment variables:"
    echo "  export POSTGRES_HOST=localhost"
    echo "  export POSTGRES_PORT=5432"
    echo "  export POSTGRES_DB=$POSTGRES_DB"
    echo "  export POSTGRES_USER=postgres"
    echo "  export POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
    echo ""
    echo "Or use connection string:"
    echo "  export DATABASE_URL=postgresql://postgres:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB"
    
else
    echo "❌ Docker not found."
    echo ""
    echo "Options:"
    echo "  1. Install Docker: https://www.docker.com/get-started"
    echo "  2. Use local PostgreSQL: ./setup_postgres_local.sh"
    echo "  3. Manual setup: See docs/PGVECTOR_SETUP.md"
    exit 1
fi

