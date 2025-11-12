# Database Schema Documentation

**Last Updated**: After complete migration to pgvector-only architecture

## Overview

The application uses **PostgreSQL with pgvector extension** as the single source of truth for all structured data. The database uses a single-table design where all document types are stored in the `vector_documents` table with JSONB metadata for flexible querying.

**Database Name**: `chat_pgvector`  
**PostgreSQL Extension**: `pgvector` (for vector similarity search)

---

## Table: `vector_documents`

The main table storing all application data with vector embeddings for semantic search.

### Table Structure

```sql
CREATE TABLE vector_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL DEFAULT 'personal_assistant',
    text TEXT NOT NULL,
    embedding vector(768) NOT NULL,  -- Dynamic: 768 (default) or up to 2000 (with PCA reduction)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Column Descriptions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier for each document (auto-generated) |
| `user_id` | VARCHAR(255) | NOT NULL | User identifier for data isolation (e.g., "mycguo_gmail_com", "default_user") |
| `collection_name` | VARCHAR(255) | NOT NULL, DEFAULT 'personal_assistant' | Collection/namespace grouping documents by type |
| `text` | TEXT | NOT NULL | Formatted text content used for semantic search and embedding generation |
| `embedding` | vector(N) | NOT NULL | Vector embedding (N = 768 default, or up to 2000 with PCA reduction) |
| `metadata` | JSONB | DEFAULT '{}' | Flexible JSONB structure containing full record data and search metadata |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | Timestamp when document was created |
| `updated_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | Timestamp when document was last updated (auto-updated via trigger) |

### Metadata Structure

The `metadata` JSONB field contains structured data with the following standard structure:

```json
{
  "record_type": "application|question|resume|company|quick_note|concept|practice_session|resume_version",
  "record_id": "app_abc123...",
  "data": {
    // Full structured object matching the Python model
  },
  "text": "Formatted text for semantic search"
}
```

**Key Metadata Fields:**
- `record_type`: Type of record (required for filtering)
- `record_id`: Unique identifier for the record (matches model ID)
- `data`: Complete structured data object (matches Python dataclass)
- `text`: Formatted text representation for semantic search

---

## Collections

Documents are organized into collections via the `collection_name` column:

| Collection Name | Record Types | Description |
|----------------|--------------|-------------|
| `applications` | `application` | Job applications |
| `companies` | `company` | Company information (job search) |
| `contacts` | `contact` | Contact persons |
| `quick_notes` | `quick_note` | Quick notes and reminders |
| `interview_prep` | `question`, `concept`, `practice_session` | Interview questions, technical concepts, practice sessions |
| `resumes` | `resume`, `resume_version` | Resumes and resume versions |
| `personal_assistant` | Various | Uploaded documents (PDFs, Word docs, URLs, audio/video) |

---

## Indexes

### Primary Indexes

#### 1. User/Collection Lookup Index
```sql
CREATE INDEX idx_vector_documents_user_collection 
ON vector_documents(user_id, collection_name);
```
**Purpose**: Fast filtering by user and collection  
**Used For**: User isolation and collection-based queries

#### 2. Vector Similarity Index

**HNSW Index** (for dimensions ≤ 1000):
```sql
CREATE INDEX idx_vector_documents_embedding_hnsw 
ON vector_documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
**Purpose**: Fast approximate nearest neighbor search using cosine similarity  
**Algorithm**: Hierarchical Navigable Small World (HNSW)  
**Used For**: Semantic similarity search queries

**IVFFlat Index** (for dimensions 1000-2000):
```sql
CREATE INDEX idx_vector_documents_embedding_ivfflat 
ON vector_documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```
**Purpose**: Fast approximate nearest neighbor search for higher-dimensional vectors  
**Algorithm**: Inverted File with Flat compression (IVFFlat)  
**Used For**: Semantic similarity search when dimensions exceed 1000

#### 3. JSONB Metadata Index
```sql
CREATE INDEX idx_vector_documents_metadata_gin 
ON vector_documents USING gin (metadata);
```
**Purpose**: Fast JSONB queries and filtering  
**Used For**: Filtering by metadata fields, JSONB path queries

### Specialized Indexes (from migration 002)

#### Record Type Index
```sql
CREATE INDEX idx_vector_documents_record_type 
ON vector_documents ((metadata->>'record_type'));
```
**Purpose**: Fast filtering by record type  
**Used For**: Queries filtering by `record_type` (e.g., all applications, all questions)

#### Application-Specific Indexes
```sql
-- Filter by application status
CREATE INDEX idx_vector_documents_app_status 
ON vector_documents ((metadata->'data'->>'status'))
WHERE metadata->>'record_type' = 'application';

-- Filter by application company
CREATE INDEX idx_vector_documents_app_company 
ON vector_documents ((metadata->'data'->>'company'))
WHERE metadata->>'record_type' = 'application';
```
**Purpose**: Optimized queries for application filtering  
**Used For**: Filtering applications by status or company name

#### Question-Specific Indexes
```sql
-- Filter by question type
CREATE INDEX idx_vector_documents_question_type 
ON vector_documents ((metadata->'data'->>'type'))
WHERE metadata->>'record_type' = 'question';

-- Filter by question category
CREATE INDEX idx_vector_documents_question_category 
ON vector_documents ((metadata->'data'->>'category'))
WHERE metadata->>'record_type' = 'question';

-- Filter by question difficulty
CREATE INDEX idx_vector_documents_question_difficulty 
ON vector_documents ((metadata->'data'->>'difficulty'))
WHERE metadata->>'record_type' = 'question';
```
**Purpose**: Optimized queries for interview question filtering  
**Used For**: Filtering questions by type, category, or difficulty

#### Resume-Specific Indexes
```sql
-- Filter by master resume flag
CREATE INDEX idx_vector_documents_resume_is_master 
ON vector_documents ((metadata->'data'->>'is_master'))
WHERE metadata->>'record_type' = 'resume';

-- Filter by tailored company
CREATE INDEX idx_vector_documents_resume_tailored_for 
ON vector_documents ((metadata->'data'->>'tailored_for_company'))
WHERE metadata->>'record_type' = 'resume';
```
**Purpose**: Optimized queries for resume filtering  
**Used For**: Finding master resumes or resumes tailored for specific companies

#### Record ID Index
```sql
CREATE INDEX idx_vector_documents_record_id 
ON vector_documents ((metadata->>'record_id'));
```
**Purpose**: Fast lookups by record ID  
**Used For**: Direct record retrieval by ID

#### Composite User/Record Index
```sql
CREATE INDEX idx_vector_documents_user_record 
ON vector_documents (user_id, (metadata->>'record_type'), (metadata->>'record_id'));
```
**Purpose**: Fast user-scoped record lookups  
**Used For**: Efficient queries combining user, record type, and record ID

---

## Triggers

### Auto-Update Timestamp Trigger

**Function**:
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';
```

**Trigger**:
```sql
CREATE TRIGGER update_vector_documents_updated_at 
BEFORE UPDATE ON vector_documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Purpose**: Automatically update `updated_at` timestamp on row updates

---

## Record Type Schemas

### Application (`record_type: 'application'`)

**Collection**: `applications`  
**Model**: `models.application.Application`

**Metadata Structure**:
```json
{
  "record_type": "application",
  "record_id": "app_abc123",
  "data": {
    "id": "app_abc123",
    "company": "Google",
    "role": "Software Engineer",
    "status": "applied|screening|interview|offer|accepted|rejected|withdrawn",
    "applied_date": "2024-01-15",
    "job_url": "https://...",
    "job_description": "...",
    "location": "Mountain View, CA",
    "salary_range": "$150k-$200k",
    "match_score": 0.85,
    "notes": "...",
    "cover_letter": "...",
    "timeline": [
      {
        "date": "2024-01-15",
        "event_type": "applied",
        "notes": "..."
      }
    ],
    "job_requirements": {...},
    "recruiter_contact": {
      "name": "...",
      "email": "...",
      "url": "...",
      "notes": "..."
    },
    "hiring_manager_contact": {...},
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
  },
  "text": "Job Application: Google - Software Engineer\nStatus: applied\n..."
}
```

**Indexed Fields**: `status`, `company`

---

### Company (`record_type: 'company'`)

**Collection**: `companies`  
**Model**: `models.company.Company`

**Metadata Structure**:
```json
{
  "record_type": "company",
  "record_id": "comp_xyz789",
  "data": {
    "id": "comp_xyz789",
    "name": "Google",
    "status": "target|applied|interviewing|offer|rejected|accepted",
    "website": "https://google.com",
    "industry": "Technology",
    "size": "large",
    "location": "Mountain View, CA",
    "description": "...",
    "culture_notes": "...",
    "tech_stack": ["Python", "Go", "Kubernetes"],
    "pros": [...],
    "cons": [...],
    "contacts": [...],
    "application_ids": ["app_abc123"],
    "notes": "...",
    "priority": 8,
    "tags": [...],
    "created_at": "2024-01-10T10:00:00",
    "updated_at": "2024-01-10T10:00:00"
  },
  "text": "Company: Google\nIndustry: Technology\n..."
}
```

---

### Interview Question (`record_type: 'question'`)

**Collection**: `interview_prep`  
**Model**: `models.interview_prep.InterviewQuestion`

**Metadata Structure**:
```json
{
  "record_type": "question",
  "record_id": "iq_def456",
  "data": {
    "id": "iq_def456",
    "question": "Tell me about a time you handled a conflict",
    "type": "behavioral|technical|system-design|case-study",
    "category": "leadership|conflict|algorithms|system-design",
    "difficulty": "easy|medium|hard",
    "answer_full": "...",
    "answer_star": {
      "situation": "...",
      "task": "...",
      "action": "...",
      "result": "..."
    },
    "notes": "...",
    "tags": [...],
    "companies": ["Google", "Meta"],
    "last_practiced": "2024-01-20T10:00:00",
    "practice_count": 5,
    "confidence_level": 4,
    "importance": 8,
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-20T10:00:00"
  },
  "text": "Interview Question: Tell me about a time...\nType: behavioral\n..."
}
```

**Indexed Fields**: `type`, `category`, `difficulty`

---

### Technical Concept (`record_type: 'concept'`)

**Collection**: `interview_prep`  
**Model**: `models.interview_prep.TechnicalConcept`

**Metadata Structure**:
```json
{
  "record_type": "concept",
  "record_id": "tc_ghi789",
  "data": {
    "id": "tc_ghi789",
    "concept": "Load Balancing",
    "category": "system-design|algorithms|databases|api-design",
    "content": "...",
    "code_examples": [
      {
        "language": "python",
        "code": "...",
        "explanation": "..."
      }
    ],
    "key_points": [...],
    "related_questions": ["iq_def456"],
    "tags": [...],
    "resources": ["https://..."],
    "last_reviewed": "2024-01-18T10:00:00",
    "review_count": 3,
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-18T10:00:00"
  },
  "text": "Technical Concept: Load Balancing\nCategory: system-design\n..."
}
```

---

### Practice Session (`record_type: 'practice_session'`)

**Collection**: `interview_prep`  
**Model**: `models.interview_prep.PracticeSession`

**Metadata Structure**:
```json
{
  "record_type": "practice_session",
  "record_id": "ps_jkl012",
  "data": {
    "id": "ps_jkl012",
    "date": "2024-01-20",
    "questions_practiced": ["iq_def456", "iq_mno345"],
    "duration_minutes": 45,
    "performance": {
      "iq_def456": {
        "rating": 4,
        "notes": "...",
        "timestamp": "2024-01-20T10:00:00"
      }
    },
    "notes": "...",
    "areas_to_improve": [...],
    "next_goals": [...],
    "session_type": "general|company-specific|topic-specific",
    "created_at": "2024-01-20T10:00:00"
  },
  "text": "Practice Session: 2024-01-20\nDuration: 45 minutes\n..."
}
```

---

### Resume (`record_type: 'resume'`)

**Collection**: `resumes`  
**Model**: `models.resume.Resume`

**Metadata Structure**:
```json
{
  "record_type": "resume",
  "record_id": "res_mno345",
  "data": {
    "id": "res_mno345",
    "name": "Software Engineer Resume",
    "full_text": "...",
    "original_filename": "resume.pdf",
    "file_type": "pdf",
    "file_path": "user_data/.../resume_data/files/res_abc123.pdf",
    "sections": {...},
    "skills": ["Python", "JavaScript"],
    "experience_years": 5,
    "education": [...],
    "certifications": [...],
    "version": "1.0",
    "is_master": true,
    "parent_id": null,
    "tailored_for_job": null,
    "tailored_for_company": null,
    "tailoring_notes": "",
    "is_active": true,
    "last_used": "2024-01-15T10:00:00",
    "applications_count": 3,
    "success_rate": 0.67,
    "created_at": "2024-01-10T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
  },
  "text": "Resume: Software Engineer Resume\nSkills: Python, JavaScript\n..."
}
```

**Indexed Fields**: `is_master`, `tailored_for_company`

---

### Resume Version (`record_type: 'resume_version'`)

**Collection**: `resumes`  
**Model**: `models.resume.ResumeVersion`

**Metadata Structure**:
```json
{
  "record_type": "resume_version",
  "record_id": "rv_pqr678",
  "data": {
    "id": "rv_pqr678",
    "resume_id": "res_mno345",
    "version": "1.1",
    "full_text": "...",
    "sections": {...},
    "changes_summary": "Updated experience section",
    "changed_by": "user|ai",
    "created_at": "2024-01-12T10:00:00"
  },
  "text": "Resume Version: 1.1\nResume: Software Engineer Resume\n..."
}
```

---

### Quick Note (`record_type: 'quick_note'`)

**Collection**: `quick_notes`  
**Model**: Dictionary (no formal model class)

**Metadata Structure**:
```json
{
  "record_type": "quick_note",
  "record_id": "qn_stu901",
  "data": {
    "id": "qn_stu901",
    "content": "Follow up with recruiter next week",
    "tags": ["follow-up"],
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
  },
  "text": "Quick Note: Follow up with recruiter next week\n..."
}
```

---

### Contact (`record_type: 'contact'`)

**Collection**: `contacts`  
**Model**: Dictionary (no formal model class)

**Metadata Structure**:
```json
{
  "record_type": "contact",
  "record_id": "contact_vwx234",
  "data": {
    "id": "contact_vwx234",
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Google",
    "role": "Recruiter",
    "linkedin_url": "https://linkedin.com/...",
    "notes": "...",
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
  },
  "text": "Contact: John Doe\nCompany: Google\nRole: Recruiter\n..."
}
```

---

## Relationships

### Implicit Relationships

The database uses **implicit relationships** via ID references stored in JSONB data:

1. **Application → Company**: `application.data.company` (string name) + `application.data.company_id` (if exists)
2. **Application → Contact**: `application.data.recruiter_contact`, `application.data.hiring_manager_contact`
3. **Company → Applications**: `company.data.application_ids` (array of application IDs)
4. **Resume Version → Resume**: `resume_version.data.resume_id`
5. **Resume → Applications**: Via `resume.data.applications_count` (denormalized count)
6. **Practice Session → Questions**: `practice_session.data.questions_practiced` (array of question IDs)
7. **Question → Companies**: `question.data.companies` (array of company names)

**Note**: These relationships are maintained in application code, not via foreign keys.

---

## Query Patterns

### 1. Get All Records of a Type

```sql
SELECT metadata->'data' as data
FROM vector_documents
WHERE user_id = 'mycguo_gmail_com'
  AND collection_name = 'applications'
  AND metadata->>'record_type' = 'application';
```

### 2. Get Record by ID

```sql
SELECT metadata->'data' as data
FROM vector_documents
WHERE user_id = 'mycguo_gmail_com'
  AND collection_name = 'applications'
  AND metadata->>'record_type' = 'application'
  AND metadata->>'record_id' = 'app_abc123';
```

### 3. Filter by Status (Applications)

```sql
SELECT metadata->'data' as data
FROM vector_documents
WHERE user_id = 'mycguo_gmail_com'
  AND collection_name = 'applications'
  AND metadata->>'record_type' = 'application'
  AND metadata->'data'->>'status' = 'applied';
```

### 4. Semantic Similarity Search

```sql
SELECT 
  id,
  text,
  metadata->'data' as data,
  1 - (embedding <=> %s::vector) as similarity
FROM vector_documents
WHERE user_id = 'mycguo_gmail_com'
  AND collection_name = 'applications'
ORDER BY embedding <=> %s::vector
LIMIT 10;
```

**Note**: `<=>` is the cosine distance operator in pgvector.

### 5. Filter Questions by Type and Difficulty

```sql
SELECT metadata->'data' as data
FROM vector_documents
WHERE user_id = 'mycguo_gmail_com'
  AND collection_name = 'interview_prep'
  AND metadata->>'record_type' = 'question'
  AND metadata->'data'->>'type' = 'technical'
  AND metadata->'data'->>'difficulty' = 'hard';
```

### 6. Find Master Resumes

```sql
SELECT metadata->'data' as data
FROM vector_documents
WHERE user_id = 'mycguo_gmail_com'
  AND collection_name = 'resumes'
  AND metadata->>'record_type' = 'resume'
  AND (metadata->'data'->>'is_master')::boolean = true;
```

### 7. Get Recent Records (Sorted by Date)

```sql
SELECT metadata->'data' as data
FROM vector_documents
WHERE user_id = 'mycguo_gmail_com'
  AND collection_name = 'applications'
  AND metadata->>'record_type' = 'application'
ORDER BY (metadata->'data'->>'created_at') DESC
LIMIT 10;
```

---

## Vector Embeddings

### Embedding Model

- **Model**: Google Gemini Embedding (`models/gemini-embedding-001`)
- **Original Dimension**: 768 dimensions
- **Reduced Dimension**: Up to 2000 dimensions (if PCA reduction is applied)
- **Distance Metric**: Cosine similarity (`vector_cosine_ops`)

### Dimensionality Reduction

For embeddings exceeding 2000 dimensions (pgvector index limit), PCA reduction is applied:
- **Original**: 3072 dimensions (if using different model)
- **Reduced**: 2000 dimensions (maximum for pgvector indexing)
- **Method**: Principal Component Analysis (PCA)
- **Storage**: PCA model cached per collection/user

### Vector Index Selection

- **Dimensions ≤ 1000**: HNSW index (faster, more memory)
- **Dimensions 1000-2000**: IVFFlat index (more efficient for higher dimensions)
- **Dimensions > 2000**: No index (sequential scan, should not occur)

---

## Constraints and Validation

### Application-Level Constraints

1. **User Isolation**: All queries must filter by `user_id`
2. **Record Type**: Must match collection (e.g., `applications` collection only contains `application` records)
3. **Record ID Uniqueness**: Enforced per user/collection/record_type combination
4. **Metadata Structure**: `record_type` and `record_id` are required in metadata

### Database-Level Constraints

1. **Primary Key**: `id` (UUID, auto-generated)
2. **NOT NULL**: `user_id`, `collection_name`, `text`, `embedding`
3. **Default Values**: `collection_name` = 'personal_assistant', `metadata` = '{}'
4. **Auto Timestamps**: `created_at` and `updated_at` (via trigger)

---

## Performance Considerations

### Index Usage

- **Vector searches**: Use HNSW/IVFFlat indexes for similarity queries
- **Structured queries**: Use JSONB path indexes for filtering
- **Composite queries**: Combine user_id + collection_name index with JSONB indexes

### Query Optimization Tips

1. **Always filter by user_id first** (uses composite index)
2. **Use collection_name** to narrow scope early
3. **Leverage partial indexes** (WHERE clauses in index definitions)
4. **Limit results** for similarity searches (use LIMIT clause)
5. **Use JSONB path operators** (`->`, `->>`) for efficient filtering

### Maintenance

- **VACUUM ANALYZE**: Run periodically to update statistics
- **Index Rebuild**: May be needed after large data imports
- **Connection Pooling**: Uses ThreadedConnectionPool (1-10 connections)

---

## Migration Files

### 001_create_vector_tables.sql
Creates the `vector_documents` table, basic indexes, and triggers.

### 002_add_jsonb_indexes.sql
Adds specialized JSONB path indexes for common query patterns.

---

## Related Documentation

- `docs/ARCHITECTURE.md` - Overall architecture overview
- `docs/QUERY_ARCHITECTURE.md` - Query patterns and examples
- `docs/CURRENT_STATE.md` - Current implementation state
- `docs/PGVECTOR_SETUP.md` - PostgreSQL + pgvector setup guide

---

## Schema Version History

- **v1.0** (Initial): Single `vector_documents` table with basic indexes
- **v1.1** (Migration 002): Added specialized JSONB path indexes for performance

---

## Notes

- **No Foreign Keys**: Relationships are maintained in application code
- **Flexible Schema**: JSONB allows schema evolution without migrations
- **Single Table Design**: All document types share the same table structure
- **User Isolation**: Multi-tenancy via `user_id` column (no separate schemas)
- **Collection Organization**: Logical grouping via `collection_name` (not enforced at DB level)

