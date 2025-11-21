# Google Models Test Suite

This test suite validates the integration of Google's latest AI models:
- **LLM**: Gemini 2.5 Flash
- **Embeddings**: gemini-embedding-001

## Test Coverage

### 1. **TestGeminiLLM** - Gemini 2.5 Flash LLM Tests
- `test_gemini_flash_initialization`: Validates model initialization
- `test_gemini_flash_basic_generation`: Tests text generation capability

### 2. **TestGeminiEmbeddings** - Embedding Model Tests
- `test_gemini_embeddings_initialization`: Validates embeddings initialization
- `test_gemini_embeddings_single_text`: Tests single query embedding (3072 dimensions)
- `test_gemini_embeddings_multiple_documents`: Tests batch document embedding

### 3. **TestSimpleVectorStore** - Vector Store Integration
- `test_simple_vector_store_initialization`: Validates vector store setup
- `test_simple_vector_store_add_texts`: Tests document ingestion
- `test_simple_vector_store_similarity_search`: Tests semantic search
- `test_simple_vector_store_persistence`: Tests data persistence

### 4. **TestRAGPipeline** - End-to-End RAG Tests
- `test_rag_chain_initialization`: Validates RAG chain setup
- `test_rag_pipeline_end_to_end`: Tests complete pipeline (ingest → search → generate)

### 5. **TestModelCompatibility** - Configuration Tests
- `test_simple_vector_store_default_model`: Validates default model configuration
- `test_gemini_model_name_format`: Ensures correct model naming conventions

## Running Tests

### Without API Key (Limited Tests)
Tests that don't require API calls will run:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests (API-dependent tests will be skipped)
pytest tests/test_google_models.py -v

# Run only compatibility tests
pytest tests/test_google_models.py::TestModelCompatibility -v
```

### With Google API Key (Full Test Suite)
To run all tests including API-dependent ones:

```bash
# Set your Google API key
export GOOGLE_API_KEY="your_google_api_key_here"

# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/test_google_models.py -v -s

# Run specific test class
pytest tests/test_google_models.py::TestGeminiLLM -v -s
pytest tests/test_google_models.py::TestGeminiEmbeddings -v -s
pytest tests/test_google_models.py::TestSimpleVectorStore -v -s
pytest tests/test_google_models.py::TestRAGPipeline -v -s

# Run individual test
pytest tests/test_google_models.py::TestRAGPipeline::test_rag_pipeline_end_to_end -v -s
```

### Show Configuration Info
```bash
source .venv/bin/activate
pytest tests/test_google_models.py::test_print_configuration_info -v -s
```

## Test Output

### Without API Key
```
⚠️  WARNING: Most tests will be skipped without Google API key
Set GOOGLE_API_KEY environment variable to run all tests

2 passed, 11 skipped
```

### With API Key
```
============================================================
Google Models Test Configuration
============================================================
Google API Key Available: True
LLM Model: gemini-2.5-flash
Embedding Model: models/gemini-embedding-001
Embedding Dimensions: 3072
============================================================

13 passed
```

## Expected Results

When running with a valid Google API key, all tests should pass and you should see:

1. **Embeddings**: 3072-dimensional vectors generated for queries and documents
2. **LLM**: Text responses generated from Gemini 2.5 Flash
3. **Vector Store**: Documents successfully added, retrieved, and persisted
4. **RAG Pipeline**: Complete workflow from document ingestion to question answering

## Troubleshooting

### "No module named pytest"
```bash
source .venv/bin/activate
pip install pytest
```

### "Module not found" errors
Install all dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### API Key Issues
Ensure your Google API key is valid and has access to:
- Gemini 2.5 Flash model
- gemini-embedding-001 embeddings

Get your API key at: https://ai.google.dev/

### Tests timing out
The full test suite with API calls may take 30-60 seconds to complete. This is normal.

## Integration with CI/CD

To run these tests in CI/CD without API keys:
```bash
pytest tests/test_google_models.py::TestModelCompatibility -v
```

To run with API keys (store securely in CI secrets):
```bash
export GOOGLE_API_KEY="${{ secrets.GOOGLE_API_KEY }}"
pytest tests/test_google_models.py -v
```

## Notes

- Tests use temporary directories for vector store data (cleaned up automatically)
- API-dependent tests are automatically skipped when API key is not available
- All tests are idempotent and can be run multiple times
- Vector store dimension is validated to be 3072 (gemini-embedding-001 default)
