"""
Vector Store Synchronization

Automatically sync JSON database records to the vector store for semantic search.
This allows structured data (applications, resumes, interview questions) to be
searchable via semantic queries.
"""

from typing import Optional, Dict, List
from datetime import datetime
import os

try:
    from storage.pg_vector_store import PgVectorStore
    from storage.user_utils import get_user_id
    HAS_VECTOR_STORE = True
except ImportError:
    HAS_VECTOR_STORE = False

try:
    from models.application import Application
    from models.interview_prep import InterviewQuestion
    from models.resume import Resume
    HAS_MODELS = True
except ImportError:
    HAS_MODELS = False
    Application = None
    InterviewQuestion = None
    Resume = None


def format_application_text(app: 'Application') -> str:
    """
    Format application data as searchable text.
    
    Args:
        app: Application instance
        
    Returns:
        Formatted text string
    """
    if not HAS_MODELS:
        return ""
    
    parts = [
        f"Job Application: {app.company} - {app.role}",
        f"Status: {app.status}",
        f"Applied Date: {app.applied_date}",
    ]
    
    if app.location:
        parts.append(f"Location: {app.location}")
    
    if app.salary_range:
        parts.append(f"Salary Range: {app.salary_range}")
    
    if app.job_description:
        parts.append(f"Job Description: {app.job_description}")
    
    if app.notes:
        parts.append(f"Notes: {app.notes}")
    
    if app.job_requirements:
        reqs = app.job_requirements
        if isinstance(reqs, dict):
            if reqs.get('skills'):
                parts.append(f"Required Skills: {', '.join(reqs['skills'])}")
            if reqs.get('experience'):
                parts.append(f"Experience Required: {reqs['experience']}")
    
    if app.timeline:
        events = [f"{e.event_type} on {e.date}" for e in app.timeline[-3:]]  # Last 3 events
        parts.append(f"Recent Timeline: {', '.join(events)}")
    
    return "\n".join(parts)


def format_interview_question_text(question: 'InterviewQuestion') -> str:
    """
    Format interview question data as searchable text.
    
    Args:
        question: InterviewQuestion instance
        
    Returns:
        Formatted text string
    """
    if not HAS_MODELS:
        return ""
    
    parts = [
        f"Interview Question: {question.question}",
        f"Type: {question.type}",
        f"Category: {question.category}",
        f"Difficulty: {question.difficulty}",
    ]
    
    if question.answer_full:
        parts.append(f"Answer: {question.answer_full}")
    
    if question.answer_star:
        star = question.answer_star
        if isinstance(star, dict):
            if star.get('situation'):
                parts.append(f"Situation: {star['situation']}")
            if star.get('task'):
                parts.append(f"Task: {star['task']}")
            if star.get('action'):
                parts.append(f"Action: {star['action']}")
            if star.get('result'):
                parts.append(f"Result: {star['result']}")
    
    if question.companies:
        parts.append(f"Companies: {', '.join(question.companies)}")
    
    if question.tags:
        parts.append(f"Tags: {', '.join(question.tags)}")
    
    if question.notes:
        parts.append(f"Notes: {question.notes}")
    
    return "\n".join(parts)


def format_resume_text(resume: 'Resume') -> str:
    """
    Format resume data as searchable text.
    
    Args:
        resume: Resume instance
        
    Returns:
        Formatted text string
    """
    if not HAS_MODELS:
        return ""
    
    parts = [
        f"Resume: {resume.name}",
        f"Type: {'Master Resume' if resume.is_master else 'Tailored Resume'}",
    ]
    
    if resume.tailored_for_company:
        parts.append(f"Tailored for: {resume.tailored_for_company}")
    
    if resume.full_text:
        # Use first 500 chars of full text as summary
        summary = resume.full_text[:500] + "..." if len(resume.full_text) > 500 else resume.full_text
        parts.append(f"Content: {summary}")
    
    if resume.skills:
        parts.append(f"Skills: {', '.join(resume.skills)}")
    
    if resume.experience_years:
        parts.append(f"Experience: {resume.experience_years} years")
    
    if resume.education:
        parts.append(f"Education: {', '.join(resume.education)}")
    
    return "\n".join(parts)


def format_contact_text(contact: Dict) -> str:
    """Format contact data as searchable text."""
    parts = [f"Contact: {contact.get('name', 'Unknown')}"]
    
    if contact.get('company'):
        parts.append(f"Company: {contact['company']}")
    
    if contact.get('email'):
        parts.append(f"Email: {contact['email']}")
    
    if contact.get('phone'):
        parts.append(f"Phone: {contact['phone']}")
    
    if contact.get('role'):
        parts.append(f"Role: {contact['role']}")
    
    if contact.get('notes'):
        parts.append(f"Notes: {contact['notes']}")
    
    return "\n".join(parts)


def format_company_text(company: Dict) -> str:
    """Format company data as searchable text."""
    parts = [f"Company: {company.get('name', 'Unknown')}"]
    
    if company.get('industry'):
        parts.append(f"Industry: {company['industry']}")
    
    if company.get('size'):
        parts.append(f"Size: {company['size']}")
    
    if company.get('location'):
        parts.append(f"Location: {company['location']}")
    
    if company.get('notes'):
        parts.append(f"Notes: {company['notes']}")
    
    if company.get('research'):
        parts.append(f"Research: {company['research']}")
    
    return "\n".join(parts)


def sync_application_to_vector_store(app: 'Application', user_id: Optional[str] = None) -> bool:
    """
    Sync an application to the vector store.
    
    Args:
        app: Application instance
        user_id: Optional user ID
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_VECTOR_STORE:
        return False
    
    try:
        if user_id is None:
            try:
                user_id = get_user_id()
            except:
                user_id = "default_user"
        
        vector_store = PgVectorStore(collection_name="applications", user_id=user_id)
        
        text = format_application_text(app)
        if not text:
            return False
        
        metadata = {
            'source': 'application',
            'application_id': app.id,
            'company': app.company,
            'role': app.role,
            'status': app.status,
            'type': 'job_application',
            'timestamp': datetime.now().isoformat(),
        }
        
        # Delete old entry if exists (by application_id)
        _delete_by_metadata(vector_store, {'application_id': app.id})
        
        # Add new entry
        vector_store.add_texts([text], metadatas=[metadata])
        return True
    except Exception as e:
        print(f"Error syncing application to vector store: {e}")
        return False


def sync_interview_question_to_vector_store(question: 'InterviewQuestion', user_id: Optional[str] = None) -> bool:
    """
    Sync an interview question to the vector store.
    
    Args:
        question: InterviewQuestion instance
        user_id: Optional user ID
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_VECTOR_STORE:
        return False
    
    try:
        if user_id is None:
            try:
                user_id = get_user_id()
            except:
                user_id = "default_user"
        
        vector_store = PgVectorStore(collection_name="interview_prep", user_id=user_id)
        
        text = format_interview_question_text(question)
        if not text:
            return False
        
        metadata = {
            'source': 'interview_question',
            'question_id': question.id,
            'type': question.type,
            'category': question.category,
            'difficulty': question.difficulty,
            'companies': question.companies,
            'tags': question.tags,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Delete old entry if exists (by question_id)
        _delete_by_metadata(vector_store, {'question_id': question.id})
        
        # Add new entry
        vector_store.add_texts([text], metadatas=[metadata])
        return True
    except Exception as e:
        print(f"Error syncing interview question to vector store: {e}")
        return False


def sync_resume_to_vector_store(resume: 'Resume', user_id: Optional[str] = None) -> bool:
    """
    Sync a resume to the vector store.
    
    Args:
        resume: Resume instance
        user_id: Optional user ID
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_VECTOR_STORE:
        return False
    
    try:
        if user_id is None:
            try:
                user_id = get_user_id()
            except:
                user_id = "default_user"
        
        vector_store = PgVectorStore(collection_name="resumes", user_id=user_id)
        
        text = format_resume_text(resume)
        if not text:
            return False
        
        metadata = {
            'source': 'resume',
            'resume_id': resume.id,
            'name': resume.name,
            'is_master': resume.is_master,
            'tailored_for_company': resume.tailored_for_company,
            'type': 'resume',
            'timestamp': datetime.now().isoformat(),
        }
        
        # Delete old entry if exists (by resume_id)
        _delete_by_metadata(vector_store, {'resume_id': resume.id})
        
        # Add new entry
        vector_store.add_texts([text], metadatas=[metadata])
        return True
    except Exception as e:
        print(f"Error syncing resume to vector store: {e}")
        return False


def sync_contact_to_vector_store(contact: Dict, user_id: Optional[str] = None) -> bool:
    """
    Sync a contact to the vector store.
    
    Args:
        contact: Contact dictionary
        user_id: Optional user ID
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_VECTOR_STORE:
        return False
    
    try:
        if user_id is None:
            try:
                user_id = get_user_id()
            except:
                user_id = "default_user"
        
        vector_store = PgVectorStore(collection_name="contacts", user_id=user_id)
        
        text = format_contact_text(contact)
        if not text:
            return False
        
        contact_id = contact.get('id', contact.get('name', 'unknown'))
        
        metadata = {
            'source': 'contact',
            'contact_id': contact_id,
            'name': contact.get('name'),
            'company': contact.get('company'),
            'type': 'contact',
            'timestamp': datetime.now().isoformat(),
        }
        
        # Delete old entry if exists
        _delete_by_metadata(vector_store, {'contact_id': contact_id})
        
        # Add new entry
        vector_store.add_texts([text], metadatas=[metadata])
        return True
    except Exception as e:
        print(f"Error syncing contact to vector store: {e}")
        return False


def sync_company_to_vector_store(company: Dict, user_id: Optional[str] = None) -> bool:
    """
    Sync a company to the vector store.
    
    Args:
        company: Company dictionary
        user_id: Optional user ID
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_VECTOR_STORE:
        return False
    
    try:
        if user_id is None:
            try:
                user_id = get_user_id()
            except:
                user_id = "default_user"
        
        vector_store = PgVectorStore(collection_name="companies", user_id=user_id)
        
        text = format_company_text(company)
        if not text:
            return False
        
        company_id = company.get('id', company.get('name', 'unknown'))
        
        metadata = {
            'source': 'company',
            'company_id': company_id,
            'name': company.get('name'),
            'industry': company.get('industry'),
            'type': 'company',
            'timestamp': datetime.now().isoformat(),
        }
        
        # Delete old entry if exists
        _delete_by_metadata(vector_store, {'company_id': company_id})
        
        # Add new entry
        vector_store.add_texts([text], metadatas=[metadata])
        return True
    except Exception as e:
        print(f"Error syncing company to vector store: {e}")
        return False


def delete_from_vector_store(source_type: str, record_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a record from the vector store by ID.
    
    Args:
        source_type: Type of record ('application', 'question', 'resume', 'contact', 'company')
        record_id: Record ID
        user_id: Optional user ID
        
    Returns:
        True if successful, False otherwise
    """
    if not HAS_VECTOR_STORE:
        return False
    
    try:
        if user_id is None:
            try:
                user_id = get_user_id()
            except:
                user_id = "default_user"
        
        collection_map = {
            'application': 'applications',
            'question': 'interview_prep',
            'resume': 'resumes',
            'contact': 'contacts',
            'company': 'companies',
        }
        
        collection_name = collection_map.get(source_type, 'personal_assistant')
        vector_store = PgVectorStore(collection_name=collection_name, user_id=user_id)
        
        id_field_map = {
            'application': 'application_id',
            'question': 'question_id',
            'resume': 'resume_id',
            'contact': 'contact_id',
            'company': 'company_id',
        }
        
        id_field = id_field_map.get(source_type)
        if not id_field:
            return False
        
        return _delete_by_metadata(vector_store, {id_field: record_id})
    except Exception as e:
        print(f"Error deleting from vector store: {e}")
        return False


def _delete_by_metadata(vector_store: 'PgVectorStore', metadata_filter: Dict) -> bool:
    """
    Delete documents from vector store matching metadata filter.
    
    Args:
        vector_store: PgVectorStore instance
        metadata_filter: Dictionary of metadata fields to match
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from storage.pg_connection import get_connection
        import json
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause for metadata matching
            conditions = []
            params = [vector_store.user_id, vector_store.collection_name]
            
            for key, value in metadata_filter.items():
                conditions.append(f"metadata->>%s = %s")
                params.extend([key, str(value)])
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                DELETE FROM vector_documents
                WHERE user_id = %s 
                AND collection_name = %s
                AND {where_clause}
            """
            
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting by metadata: {e}")
        return False

