-- Migration: Add JSONB path indexes for structured queries
-- Run this migration to enable efficient filtering and sorting on structured data

-- Index for filtering by record_type
CREATE INDEX IF NOT EXISTS idx_vector_documents_record_type 
ON vector_documents ((metadata->>'record_type'));

-- Index for filtering applications by status
CREATE INDEX IF NOT EXISTS idx_vector_documents_app_status 
ON vector_documents ((metadata->'data'->>'status'))
WHERE metadata->>'record_type' = 'application';

-- Index for filtering applications by company
CREATE INDEX IF NOT EXISTS idx_vector_documents_app_company 
ON vector_documents ((metadata->'data'->>'company'))
WHERE metadata->>'record_type' = 'application';

-- Index for filtering questions by type
CREATE INDEX IF NOT EXISTS idx_vector_documents_question_type 
ON vector_documents ((metadata->'data'->>'type'))
WHERE metadata->>'record_type' = 'question';

-- Index for filtering questions by category
CREATE INDEX IF NOT EXISTS idx_vector_documents_question_category 
ON vector_documents ((metadata->'data'->>'category'))
WHERE metadata->>'record_type' = 'question';

-- Index for filtering questions by difficulty
CREATE INDEX IF NOT EXISTS idx_vector_documents_question_difficulty 
ON vector_documents ((metadata->'data'->>'difficulty'))
WHERE metadata->>'record_type' = 'question';

-- Index for filtering resumes by is_master
CREATE INDEX IF NOT EXISTS idx_vector_documents_resume_is_master 
ON vector_documents ((metadata->'data'->>'is_master'))
WHERE metadata->>'record_type' = 'resume';

-- Index for filtering resumes by tailored_for_company
CREATE INDEX IF NOT EXISTS idx_vector_documents_resume_tailored_for 
ON vector_documents ((metadata->'data'->>'tailored_for_company'))
WHERE metadata->>'record_type' = 'resume';

-- Index for record_id lookups (for get_by_id queries)
CREATE INDEX IF NOT EXISTS idx_vector_documents_record_id 
ON vector_documents ((metadata->>'record_id'));

-- Composite index for user + record_type + record_id (for fast lookups)
CREATE INDEX IF NOT EXISTS idx_vector_documents_user_record 
ON vector_documents (user_id, (metadata->>'record_type'), (metadata->>'record_id'));

