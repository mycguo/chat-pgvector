# Job Search Agent

A comprehensive job search management application with:
- Resume management
- Interview question bank
- Job application tracking
- Document upload and semantic search
- Google Doc Integration

## 🏗️ Architecture

**PostgreSQL + pgvector** is used as the single source of truth for all structured data and semantic search. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete architecture details.

## 🚀 Quick Start

### Prerequisites

1. **PostgreSQL** with pgvector extension installed
2. **Python 3.10+**
3. **Google API Key** for embeddings

### Setup

```sh
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL (see docs/PGVECTOR_SETUP.md)
# Configure environment variables (DATABASE_URL, GOOGLE_API_KEY)

# Run migrations
psql -d chat_pgvector -f storage/migrations/001_create_vector_tables.sql
psql -d chat_pgvector -f storage/migrations/002_add_jsonb_indexes.sql

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
## PostgreSQL: 
Primary database for all structured data and vector storage