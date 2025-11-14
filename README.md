# Job Search Agent

A comprehensive job search management application with:
- Resume management
- Interview question bank
- Job application tracking
- Document upload and semantic search
- Google Doc Integration

## 🏗️ Architecture

**Neon.tech (serverless PostgreSQL) + pgvector** is used as the single source of truth for all structured data and semantic search. 

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Complete architecture overview
- [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) - Detailed database schema documentation
- [docs/NEON_MIGRATION_PLAN.md](docs/NEON_MIGRATION_PLAN.md) - Migration guide for Neon.tech (serverless PostgreSQL)

## 🚀 Quick Start

### Prerequisites

1. **Neon.tech account** (free tier available) - [Sign up](https://neon.tech/)
2. **Python 3.10+**
3. **Google API Key** for embeddings

### Setup

```sh
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up Neon.tech database (see docs/PGVECTOR_SETUP.md)
# 1. Sign up at https://neon.tech/
# 2. Create a new project and database
# 3. Get your connection string from the dashboard
# 4. Set NEON_DATABASE_URL environment variable (or use Streamlit secrets):
export NEON_DATABASE_URL="postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech:5432/chat_pgvector?sslmode=require"

# Run migrations (using Neon connection string)
psql "$NEON_DATABASE_URL" -f storage/migrations/001_create_vector_tables.sql
psql "$NEON_DATABASE_URL" -f storage/migrations/002_add_jsonb_indexes.sql

# Start the application
streamlit run app.py
```

For detailed setup instructions, see [docs/PGVECTOR_SETUP.md](docs/PGVECTOR_SETUP.md).

# tech stack
## streamlit: 
web framework
## vector store: 
PostgreSQL + pgvector (vector similarity search)
## google.generativeai: 
embedding framework, models: "models/gemini-embedding-001"
## LangChain: 
Connect LLMs for Retrieval-Augmented Generation (RAG), memory, chaining and agent-based reasoning. 
## PyPDF2 and docx: 
documents import
## assemblyai: 
audio transcription
## moviepy: 
video processing
## Neon.tech (PostgreSQL): 
Serverless PostgreSQL database for all structured data and vector storage (managed, auto-scaling)