# Query Architecture: pgvector as Single Source of Truth

## 🎯 Overview

The application uses **PostgreSQL + pgvector as the single source of truth** for all data:

1. **Structured Data** → Stored in `metadata['data']` JSONB field
2. **Semantic Search** → Formatted text in `metadata['text']` with vector embeddings
3. **Both queries** → Use the same pgvector database

## 🔄 Current Query Flow

### Path 1: Structured Data Queries (pgvector JSONB)

**When**: User asks about specific data ("show my applications", "what interviews do I have?")

**Flow**:
```
User Question → detect_data_query_intent() 
              → answer_data_query() 
              → JobSearchDB / InterviewDB 
              → PgVectorStore.list_records()
              → PostgreSQL JSONB query
              → Return structured data from metadata['data']
```

**Example**:
```python
def answer_data_query(question: str, query_type: str):
    db = JobSearchDB()  # Uses pgvector
    
    if query_type == 'application':
        # Queries pgvector with JSONB filters
        applications = db.list_applications()  
        # Returns Application objects from metadata['data']
```

**What gets queried** (all from pgvector):
- Applications → `applications` collection
- Questions → `interview_prep` collection
- Contacts → `contacts` collection
- Companies → `companies` collection
- Resumes → `resumes` collection

**Implementation**:
```python
# Structured query with filters
apps = db.applications_store.list_records(
    record_type='application',
    filters={'status': 'applied', 'company': 'Google'},
    sort_by='applied_date',
    reverse=True,
    limit=10
)
```

---

### Path 2: Semantic Search Queries (Vector Similarity)

**When**: User asks general questions ("what should I know about leadership?", "tell me about system design")

**Flow**:
```
User Question → PgVectorStore.similarity_search() 
              → Generate query embedding
              → PostgreSQL vector cosine similarity
              → Returns top-k similar documents
              → Extract text from metadata['text']
              → Pass to LLM for answer
```

**Example**:
```python
# Semantic similarity search
vector_store = PgVectorStore(collection_name="personal_assistant")
docs = vector_store.similarity_search(user_question, k=5)

# Combine with web search if needed
combined_context = docs.copy()
if web_results_text:
    combined_context = [web_doc] + docs

# Pass to LLM
chain = get_chat_chain()
response = chain.invoke({"context": combined_context, "questions": user_question})
```

**What gets queried**:
- `vector_documents` table in PostgreSQL
- Text content that was embedded (conversations, uploaded docs, interview Q&A text)

**Result**: Text documents returned, passed to LLM for answer generation

---

## 🔗 How They're Linked (Currently Limited)

### When Adding Interview Questions

**Dual Storage** (`pages/interview_prep.py:89-118`):

1. **Structured Storage** (JSON):
```python
# Save to JSON file
question = {
    "id": "q_123",
    "question": "Tell me about...",
    "answer": "...",
    "type": "behavioral",
    # ... other fields
}
db.add_question(question)  # Saves to questions.json
```

2. **Vector Storage** (pgvector):
```python
# Format as text and embed
content = f"""Interview Question: {question}
Answer: {answer}
Type: {type}
Category: {category}"""

# Add to vector store with metadata link
vector_store.add_texts(
    texts=[content],
    metadatas=[{
        'source': 'interview_question',
        'question_id': question['id'],  # ← Link to JSON!
        'type': 'interview_prep',
        # ...
    }]
)
```

### The Link Exists But Isn't Used

**Metadata contains `question_id`** that could link back to JSON, but:

❌ **Current behavior**: Vector search returns text only, doesn't fetch full JSON record
✅ **Potential**: Could use `question_id` to fetch full structured data from JSON

---

## 📊 Query Examples

### Example 1: "Show my applications"
```
Query Type: Structured (data_query)
Path: answer_data_query() → JobSearchDB → applications.json
Result: Direct JSON data returned
Vector Store: Not used
```

### Example 2: "What should I know about leadership?"
```
Query Type: Semantic (general question)
Path: similarity_search() → pgvector → text documents → LLM
Result: LLM-generated answer from text context
JSON Files: Not queried directly
```

### Example 3: "Tell me about conflict resolution"
```
Query Type: Semantic (general question)
Path: similarity_search() → finds interview Q&A text → LLM
Result: Answer based on embedded interview question text
JSON Files: Not queried (but could be via question_id metadata)
```

---

## 🚧 Current Limitations

### 1. No Automatic Linking
- Vector search results have `question_id` in metadata
- But the app doesn't use it to fetch full JSON records
- Only text content is returned

### 2. Two Separate Systems
- JSON queries = structured data only
- Vector queries = text content only
- No hybrid queries that combine both

### 3. Potential Enhancement

**Could implement**:
```python
def enhanced_similarity_search(query: str, k: int = 4):
    # 1. Vector search
    docs = vector_store.similarity_search(query, k=k)
    
    # 2. Extract question_ids from metadata
    question_ids = [doc.metadata.get('question_id') 
                   for doc in docs 
                   if doc.metadata.get('question_id')]
    
    # 3. Fetch full JSON records
    if question_ids:
        db = InterviewDB()
        full_questions = [db.get_question(qid) for qid in question_ids]
        
        # 4. Combine text + structured data
        enhanced_docs = []
        for doc, question in zip(docs, full_questions):
            if question:
                # Add structured fields to metadata
                doc.metadata.update({
                    'full_question': question.question,
                    'answer_full': question.answer_full,
                    'companies': question.companies,
                    # ... other structured fields
                })
            enhanced_docs.append(doc)
        
        return enhanced_docs
    
    return docs
```

---

## ✅ Summary

| Query Type | Storage Used | How It Works |
|------------|--------------|--------------|
| **Structured queries** | JSON files | Direct read via `JobSearchDB` / `InterviewDB` |
| **Semantic queries** | pgvector | Vector similarity search → text → LLM |
| **Hybrid queries** | ❌ Not implemented | Could link via `question_id` metadata |

### Key Points:

1. **JSON files are NOT embedded** - they're queried directly for structured data
2. **Vector store contains TEXT** - formatted text content from questions/documents
3. **Metadata links exist** - `question_id` in vector metadata can link to JSON
4. **Currently separate** - no automatic linking between vector results and JSON records
5. **Both are used** - just for different query types

---

## 🎯 Answer to Your Question

**"If those JSON files are not in the vector store, how can it be used in query time?"**

**Answer**: They're used **separately**:

- **Structured queries** → Query JSON files directly (no vector search)
- **Semantic queries** → Use vector store (text content only)
- **The link**: Metadata in vector store can reference JSON IDs, but currently isn't used to fetch full records

The JSON data is **always accessible** via direct database queries (`JobSearchDB`, `InterviewDB`, `ResumeDB`), regardless of what's in the vector store.

