# JSON Data Vector Store Synchronization

## Overview

The application now automatically syncs JSON database records (applications, resumes, interview questions, companies) to the vector store for semantic search. This allows you to search your structured data using natural language queries.

## How It Works

### Automatic Synchronization

When you add, update, or delete records in the JSON databases, they are automatically synced to the vector store:

- **Applications** → `applications` collection
- **Interview Questions** → `interview_prep` collection  
- **Resumes** → `resumes` collection
- **Companies** → `companies` collection

### What Gets Embedded

Each record type is formatted as searchable text:

#### Applications
```
Job Application: {company} - {role}
Status: {status}
Applied Date: {date}
Location: {location}
Salary Range: {salary_range}
Job Description: {job_description}
Notes: {notes}
Required Skills: {skills}
Recent Timeline: {events}
```

#### Interview Questions
```
Interview Question: {question}
Type: {type}
Category: {category}
Difficulty: {difficulty}
Answer: {answer_full}
Situation: {situation}
Task: {task}
Action: {action}
Result: {result}
Companies: {companies}
Tags: {tags}
Notes: {notes}
```

#### Resumes
```
Resume: {title}
Type: {Master/Tailored}
Tailored for: {company}
Summary: {summary}
Skills: {skills}
Experience: {experience_summary}
Education: {education}
```

#### Companies
```
Company: {name}
Industry: {industry}
Size: {size}
Location: {location}
Notes: {notes}
Research: {research}
```

## Usage

### Automatic Sync (Default Behavior)

No action required! When you:
- Add an application → automatically embedded
- Update a question → automatically re-embedded
- Delete a resume → automatically removed from vector store

### Manual Migration (Existing Data)

To embed existing JSON data that was created before this feature:

```bash
# Dry run (see what would be embedded)
python storage/migrations/embed_existing_json_data.py --dry-run

# Actually embed the data
python storage/migrations/embed_existing_json_data.py
```

### Querying Embedded Data

The embedded data is automatically included in semantic searches:

```python
# In app.py - semantic search includes embedded JSON data
vector_store = PgVectorStore()
docs = vector_store.similarity_search("show me my Google applications")
# Returns: Text documents from applications, questions, resumes, etc.
```

## Architecture

### Components

1. **`storage/vector_sync.py`** - Core sync utilities
   - `format_application_text()` - Formats application as text
   - `sync_application_to_vector_store()` - Embeds application
   - `delete_from_vector_store()` - Removes from vector store

2. **Database Hooks** - Automatic sync on CRUD operations
   - `JobSearchDB.add_application()` → syncs to vector store
   - `InterviewDB.add_question()` → syncs to vector store
   - `ResumeDB.add_resume()` → syncs to vector store
   - All update/delete methods also sync

3. **Migration Script** - `storage/migrations/embed_existing_json_data.py`
   - Embeds all existing JSON data
   - Supports dry-run mode

### Metadata Linking

Each embedded document includes metadata linking back to the JSON record:

```python
metadata = {
    'source': 'application',  # or 'question', 'resume', 'company'
    'application_id': 'app_123',  # Links to JSON record
    'company': 'Google',
    'role': 'Software Engineer',
    'status': 'applied',
    'type': 'job_application',
    'timestamp': '2025-01-15T10:30:00'
}
```

This allows:
- Linking vector search results back to full JSON records
- Filtering by metadata (e.g., "show me applications for Google")
- Tracking which records are embedded

## Benefits

### 1. Unified Search
- Search all your data (applications, questions, resumes) with one query
- "What companies have I applied to?" → finds applications
- "Tell me about system design" → finds interview questions

### 2. Natural Language Queries
- "Show me my Google applications" → semantic search finds relevant apps
- "What should I know about leadership?" → finds interview prep content

### 3. Always Up-to-Date
- Automatic sync ensures vector store matches JSON data
- No manual steps required

### 4. Dual Storage
- JSON files = structured data (for CRUD operations)
- Vector store = semantic search (for queries)
- Best of both worlds!

## Collections

Data is organized into collections:

| Collection | Source | Purpose |
|------------|--------|---------|
| `applications` | `applications.json` | Job applications |
| `interview_prep` | `questions.json` | Interview questions |
| `resumes` | `resumes.json` | Resume data |
| `companies` | `companies.json` | Company research |
| `personal_assistant` | User conversations | General knowledge |

## Troubleshooting

### Sync Errors

If sync fails, you'll see warnings:
```
Warning: Could not sync application to vector store: {error}
```

Common causes:
- PostgreSQL not running
- pgvector extension not installed
- API key issues (for embeddings)

### Missing Data

If existing data isn't searchable:
1. Run the migration script: `python storage/migrations/embed_existing_json_data.py`
2. Check PostgreSQL connection
3. Verify embeddings are being generated

### Duplicate Entries

The sync automatically handles duplicates:
- On update: Old entry deleted, new one added
- Uses metadata IDs to identify records

## Future Enhancements

Potential improvements:
- [ ] Sync contacts to vector store
- [ ] Sync technical concepts
- [ ] Sync practice sessions
- [ ] Batch sync operations
- [ ] Sync status indicators in UI
- [ ] Selective sync (enable/disable per data type)

## Summary

✅ **Automatic**: JSON data automatically synced to vector store  
✅ **Searchable**: All structured data now searchable via semantic queries  
✅ **Linked**: Metadata links vector results back to JSON records  
✅ **Up-to-date**: Changes automatically reflected in vector store  
✅ **Dual Storage**: JSON for structure, vectors for search  

Your JSON data is now fully integrated with the vector store! 🎉

