# 💾 Remember Feature - Conversational Knowledge Storage

The Remember feature allows you to save information to your knowledge base naturally, without uploading documents.

## Features

### 1. 🗣️ Natural Language Commands

Simply type phrases like:
- **"Remember that I prefer Python over JavaScript"**
- **"Remember: My favorite color is blue"**
- **"Save this: I graduated from MIT in 2020"**
- **"Store that Charles lives in San Francisco"**
- **"Note that I prefer working remotely"**

The system automatically detects these commands and saves the information.

### 2. 🤖 AI-Powered Enrichment

When you save information, the system can optionally use AI to:
- Expand and contextualize the information
- Add relevant synonyms and related terms
- Make it more searchable and discoverable
- Keep the core facts unchanged

**Example:**
```
You say: "Remember that I prefer Python"

AI enriches to: "The user prefers Python as their programming language.
Python is favored for its readability, extensive libraries, and versatility
in areas like web development, data science, and AI/machine learning."
```

### 3. 🎨 UI Interface in Sidebar

Don't want to type commands? Use the **Quick Save** panel in the sidebar:

1. Enter information in the text area
2. Choose whether to "Enhance with AI" (recommended)
3. Click "💾 Save to Knowledge Base"
4. See confirmation with what was saved

## How It Works

### Supported Patterns

The system recognizes these command patterns (case-insensitive):

| Pattern | Example |
|---------|---------|
| `remember that ...` | Remember that Charles lives in SF |
| `remember: ...` | Remember: I like pizza |
| `remember ...` | Remember coffee is my favorite |
| `save this: ...` | Save this: Important meeting tomorrow |
| `save that ...` | Save that I prefer emails |
| `store this: ...` | Store this: My birthday is May 5 |
| `store that ...` | Store that I work remotely |
| `keep in mind that ...` | Keep in mind that I'm allergic to peanuts |
| `note that ...` | Note that I prefer mornings |

### What Gets Saved

When you save information:

1. **Original text** is captured
2. **Enrichment** (optional): AI expands the information for better searchability
3. **Metadata** is added:
   - Source: `conversational_input`
   - Timestamp: When it was saved
   - Original: Your exact words (if enriched)
4. **Chunks** are created if the text is long
5. **Embeddings** are generated using Google's gemini-embedding-001
6. **Storage** in your vector store (same as documents)

### Retrieval

Once saved, the information is immediately available:

```
You: "Remember that I prefer Python"
System: ✅ Information saved!

[Later...]

You: "What programming language do I prefer?"
System: "Based on your knowledge base, you prefer Python..."
```

## Usage Examples

### Example 1: Personal Preferences
```
User: "Remember that I prefer dark mode in all applications"
System: 💾 Saving information: 'i prefer dark mode in all applications'
System: ✅ Information saved to knowledge base!
System: 📝 What was saved (enriched version):
        "The user prefers dark mode, also known as night mode or dark theme,
        in all applications. This preference indicates a desire for interfaces
        with dark backgrounds and light text, which can reduce eye strain
        and improve readability in low-light conditions."
```

### Example 2: Work Information
```
User: "Store this: I work at TechCorp as a Senior Software Engineer focusing on AI systems"
System: ✅ Information saved to knowledge base!
```

### Example 3: Quick Facts
```
User: "Note that my favorite coffee is cappuccino"
System: ✅ Information saved to knowledge base!
```

### Example 4: Using the UI
1. Open the sidebar
2. In "Quick Save" section, type: "I have a meeting every Monday at 10am"
3. Check "Enhance with AI" ✓
4. Click "💾 Save to Knowledge Base"
5. See confirmation: "✅ Saved successfully!"

## Integration with Existing Knowledge Base

The Remember feature integrates seamlessly with your existing documents:

- Saved information is stored in the same vector store as uploaded documents
- Uses the same search/retrieval mechanism
- Can be queried alongside PDFs, Word docs, web pages, etc.
- Maintains consistent metadata structure

## Technical Details

### Functions

**`detect_remember_intent(text)`**
- Detects if text contains a remember command
- Returns: `(is_remember: bool, extracted_info: str)`

**`enrich_information(text)`**
- Uses Gemini 2.5 Flash to expand information
- Makes it more searchable and contextual
- Returns: enriched text

**`save_to_knowledge_base(information, enrich=True)`**
- Saves information to vector store
- Optional AI enrichment
- Adds metadata
- Returns: `(success: bool, result: str)`

### Storage Location

Information is stored in:
```
./vector_store_personal_assistant/
├── metadata.json  (includes your saved information)
└── vectors.pkl    (embeddings)
```

### Metadata Structure

```json
{
  "source": "conversational_input",
  "timestamp": "2025-11-06T09:30:00",
  "original": "I prefer Python" (if enriched),
  "text": "The user prefers Python..." (enriched version)
}
```

## Testing

Run the test suite:

```bash
source .venv/bin/activate

# Test intent detection (no API key needed)
pytest tests/test_remember_feature.py::TestRememberIntentDetection -v

# Test with API (requires Google API key)
export GOOGLE_API_KEY="your_key"
pytest tests/test_remember_feature.py -v -s
```

## Tips & Best Practices

### ✅ DO:
- Use natural language - the system understands various phrasings
- Be specific and factual
- Use enrichment for better searchability
- Save personal preferences, facts, and context

### ❌ DON'T:
- Don't save extremely long text (use document upload instead)
- Don't save duplicates - the system doesn't deduplicate yet
- Don't save sensitive passwords or API keys
- Don't expect the system to execute commands (it only stores)

## Comparison with Document Upload

| Feature | Remember Command | Document Upload |
|---------|-----------------|-----------------|
| **Speed** | Instant | Requires processing |
| **Format** | Plain text | PDF, Word, Excel, etc. |
| **Size** | Short texts | Any size |
| **Use Case** | Quick facts | Formal documents |
| **UI** | Chat or sidebar | Admin page |
| **Enrichment** | Optional AI | Basic chunking |

## Future Enhancements

Potential improvements:
- [ ] Deduplication detection
- [ ] Edit/update saved information
- [ ] Delete specific saved items
- [ ] Category/tag system
- [ ] View all saved conversational information
- [ ] Export saved information
- [ ] Batch import from notes

## Troubleshooting

### "Information not found after saving"
- Wait a few seconds for indexing
- Check if enrichment is enabled (makes it more searchable)
- Try querying with related terms

### "Enrichment is slow"
- Enrichment uses an AI model call (~2-3 seconds)
- You can disable enrichment for instant saving
- Speed depends on Google API response time

### "Pattern not detected"
- Make sure command starts with a supported pattern
- Pattern must be at the beginning of the text
- Use the sidebar UI as an alternative

## Support

For issues or questions:
- Check test results: `pytest tests/test_remember_feature.py -v`
- Review logs in console output
- Ensure Google API key is configured
- Check vector store directory exists and is writable

---

**Version:** 1.0
**Last Updated:** November 2025
**Compatible with:** Gemini 2.5 Flash, gemini-embedding-001
