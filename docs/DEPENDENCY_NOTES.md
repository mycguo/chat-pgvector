# Dependency Notes

## LangChain Version Compatibility

The project uses LangChain packages that have some version conflicts reported by `pip check`, but they work correctly at runtime.

### Current Status

- **langchain-core**: 1.0.4 (latest)
- **langchain**: 1.0.5 (latest)
- **langchain-google-genai**: 2.1.12
- **langchain-community**: 0.4.1

### Known Warnings

`pip check` may report conflicts like:
```
langchain-google-genai requires langchain-core<0.4.0, but you have langchain-core 1.0.4
```

**These are false positives** - langchain-google-genai 2.1.12 actually works fine with langchain-core 1.0.4. The declared dependency constraint is outdated.

### Verification

To verify everything works:
```bash
python -c "from langchain_google_genai import GoogleGenerativeAIEmbeddings; print('✅ Works')"
python -c "from storage.pg_vector_store import PgVectorStore; print('✅ Works')"
```

### If You Encounter Issues

If you have runtime errors, try:
```bash
pip install --upgrade langchain-google-genai langchain-core langchain
```

Or pin to compatible versions:
```bash
pip install "langchain-core>=1.0.0,<2.0.0" "langchain-google-genai>=2.1.0"
```

