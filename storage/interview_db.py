"""
Interview Preparation Database

Uses PostgreSQL + pgvector as the single source of truth.
Maintains backward compatibility with existing API.
"""

import os
import json
from typing import List, Optional, Dict
from datetime import datetime

from models.interview_prep import (
    InterviewQuestion,
    TechnicalConcept,
    CompanyResearch,
    PracticeSession
)
from storage.user_utils import get_user_data_dir
from storage.encryption import encrypt_data, decrypt_data, is_encryption_enabled
from storage.pg_vector_store import PgVectorStore


class InterviewDB:
    """Database for interview preparation materials"""

    def __init__(self, data_dir: str = None, user_id: str = None):
        """
        Initialize interview database.

        Args:
            data_dir: Directory for storing JSON files (deprecated, kept for compatibility)
            user_id: Optional user ID (if None, will try to get from Streamlit)
        """
        if data_dir is None:
            data_dir = get_user_data_dir("interview_data", user_id)
        
        self.data_dir = data_dir
        self.user_id = user_id
        self._encryption_enabled = is_encryption_enabled()
        
        # Initialize pgvector stores for all collections
        self.questions_store = PgVectorStore(collection_name="interview_prep", user_id=user_id)
        # Concepts and practice sessions also use interview_prep collection
        
        # Keep JSON files for companies (interview research, not job search companies)
        self.companies_file = os.path.join(data_dir, "companies.json")

        # Create directory and initialize files
        self._initialize()

    def _initialize(self):
        """Create data directory and initialize JSON files"""
        os.makedirs(self.data_dir, exist_ok=True)

        if not os.path.exists(self.companies_file):
            self._write_json(self.companies_file, [])

    def _read_json(self, file_path: str) -> List[dict]:
        """Read JSON file (with optional decryption)"""
        try:
            if self._encryption_enabled:
                with open(file_path, 'rb') as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        decrypted_data = decrypt_data(encrypted_data, self.user_id)
                        return json.loads(decrypted_data.decode('utf-8'))
                    else:
                        return []
            else:
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            # If decryption fails, try reading as plain JSON (for migration)
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except:
                print(f"Error reading {file_path}: {e}")
                return []

    def _write_json(self, file_path: str, data: List[dict]):
        """Write JSON file (with optional encryption)"""
        try:
            json_data = json.dumps(data, indent=2)
            
            if self._encryption_enabled:
                encrypted_data = encrypt_data(json_data.encode('utf-8'), self.user_id)
                with open(file_path, 'wb') as f:
                    f.write(encrypted_data)
            else:
                with open(file_path, 'w') as f:
                    f.write(json_data)
        except Exception as e:
            print(f"Error writing {file_path}: {e}")

    # ========== Interview Questions ==========

    def add_question(self, question: InterviewQuestion) -> str:
        """
        Add interview question.

        Args:
            question: InterviewQuestion instance

        Returns:
            Question ID
        """
        # Add to vector store (which stores full structured data)
        try:
            from storage.vector_sync import sync_interview_question_to_vector_store
            sync_interview_question_to_vector_store(question, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add question to vector store: {e}")
            raise
        
        return question.id

    def get_question(self, question_id: str) -> Optional[InterviewQuestion]:
        """Get question by ID"""
        q_dict = self.questions_store.get_by_record_id('question', question_id)
        if q_dict:
            return InterviewQuestion.from_dict(q_dict)
        return None

    def list_questions(
        self,
        type: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        company: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[InterviewQuestion]:
        """
        List questions with optional filters.

        Args:
            type: Filter by type
            category: Filter by category
            difficulty: Filter by difficulty
            company: Filter by company
            tag: Filter by tag

        Returns:
            List of InterviewQuestion instances
        """
        # Build filters
        filters = {}
        if type:
            filters['type'] = type
        if category:
            filters['category'] = category
        if difficulty:
            filters['difficulty'] = difficulty
        
        # Query from pgvector
        q_dicts = self.questions_store.list_records(
            record_type='question',
            filters=filters if filters else None,
            limit=1000
        )
        
        result = []
        for q_dict in q_dicts:
            q = InterviewQuestion.from_dict(q_dict)
            
            # Apply array filters (company, tag) that can't be done in SQL easily
            if company and company not in q.companies:
                continue
            if tag and tag not in q.tags:
                continue
            
            result.append(q)

        return result

    def update_question(self, question: InterviewQuestion):
        """Update question"""
        # Check if exists
        existing = self.questions_store.get_by_record_id('question', question.id)
        if not existing:
            return False
        
        question.updated_at = datetime.now().isoformat()
        
        # Update in vector store
        try:
            from storage.vector_sync import sync_interview_question_to_vector_store
            sync_interview_question_to_vector_store(question, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update question in vector store: {e}")
            return False
        
        return True

    def delete_question(self, question_id: str) -> bool:
        """Delete question"""
        # Check if exists
        existing = self.questions_store.get_by_record_id('question', question_id)
        if not existing:
            return False
        
        # Delete from vector store
        try:
            from storage.vector_sync import delete_from_vector_store
            success = delete_from_vector_store('question', question_id, self.user_id)
            return success
        except Exception as e:
            print(f"Warning: Could not delete question from vector store: {e}")
            return False

    def mark_question_practiced(self, question_id: str):
        """Mark question as practiced"""
        question = self.get_question(question_id)
        if question:
            question.mark_practiced()
            self.update_question(question)

    # ========== Technical Concepts ==========

    def add_concept(self, concept: TechnicalConcept) -> str:
        """Add technical concept"""
        # Add to vector store
        try:
            from storage.vector_sync import sync_concept_to_vector_store
            sync_concept_to_vector_store(concept, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add concept to vector store: {e}")
            raise
        return concept.id

    def get_concept(self, concept_id: str) -> Optional[TechnicalConcept]:
        """Get concept by ID"""
        c_dict = self.questions_store.get_by_record_id('concept', concept_id)
        if c_dict:
            return TechnicalConcept.from_dict(c_dict)
        return None

    def list_concepts(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[TechnicalConcept]:
        """List technical concepts with optional filters"""
        # Build filters
        filters = {}
        if category:
            filters['category'] = category
        
        # Query from pgvector
        c_dicts = self.questions_store.list_records(
            record_type='concept',
            filters=filters if filters else None,
            limit=1000
        )
        
        result = []
        for c_dict in c_dicts:
            c = TechnicalConcept.from_dict(c_dict)
            
            # Apply tag filter (array filter)
            if tag and tag not in c.tags:
                continue
            
            result.append(c)

        return result

    def update_concept(self, concept: TechnicalConcept):
        """Update concept"""
        # Check if exists
        existing = self.questions_store.get_by_record_id('concept', concept.id)
        if not existing:
            return False
        
        concept.updated_at = datetime.now().isoformat()
        
        # Update in vector store
        try:
            from storage.vector_sync import sync_concept_to_vector_store
            sync_concept_to_vector_store(concept, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update concept in vector store: {e}")
            return False
        
        return True

    def delete_concept(self, concept_id: str) -> bool:
        """Delete concept"""
        # Check if exists
        existing = self.questions_store.get_by_record_id('concept', concept_id)
        if not existing:
            return False
        
        # Delete from vector store
        try:
            from storage.vector_sync import delete_from_vector_store
            success = delete_from_vector_store('concept', concept_id, self.user_id)
            return success
        except Exception as e:
            print(f"Warning: Could not delete concept from vector store: {e}")
            return False

    # ========== Company Research ==========

    def add_company(self, company: CompanyResearch) -> str:
        """Add company research"""
        companies = self._read_json(self.companies_file)

        # Check for duplicate
        for existing in companies:
            if existing['company'].lower() == company.company.lower():
                raise ValueError(f"Company research for {company.company} already exists")

        companies.append(company.to_dict())
        self._write_json(self.companies_file, companies)
        return company.id

    def get_company(self, company_id: str) -> Optional[CompanyResearch]:
        """Get company by ID"""
        companies = self._read_json(self.companies_file)
        for c in companies:
            if c['id'] == company_id:
                return CompanyResearch.from_dict(c)
        return None

    def get_company_by_name(self, company_name: str) -> Optional[CompanyResearch]:
        """Get company research by company name"""
        companies = self._read_json(self.companies_file)
        for c in companies:
            if c['company'].lower() == company_name.lower():
                return CompanyResearch.from_dict(c)
        return None

    def list_companies(self) -> List[CompanyResearch]:
        """List all company research"""
        companies = self._read_json(self.companies_file)
        return [CompanyResearch.from_dict(c) for c in companies]

    def update_company(self, company: CompanyResearch):
        """Update company research"""
        companies = self._read_json(self.companies_file)

        for i, c in enumerate(companies):
            if c['id'] == company.id:
                company.updated_at = datetime.now().isoformat()
                companies[i] = company.to_dict()
                self._write_json(self.companies_file, companies)
                return True

        return False

    def delete_company(self, company_id: str) -> bool:
        """Delete company research"""
        companies = self._read_json(self.companies_file)
        filtered = [c for c in companies if c['id'] != company_id]

        if len(filtered) < len(companies):
            self._write_json(self.companies_file, filtered)
            return True
        return False

    # ========== Practice Sessions ==========

    def add_practice_session(self, session: PracticeSession) -> str:
        """Add practice session"""
        # Add to vector store
        try:
            from storage.vector_sync import sync_practice_session_to_vector_store
            sync_practice_session_to_vector_store(session, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add practice session to vector store: {e}")
            raise
        return session.id

    def get_practice_session(self, session_id: str) -> Optional[PracticeSession]:
        """Get practice session by ID"""
        s_dict = self.questions_store.get_by_record_id('practice_session', session_id)
        if s_dict:
            return PracticeSession.from_dict(s_dict)
        return None

    def list_practice_sessions(
        self,
        session_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[PracticeSession]:
        """List practice sessions"""
        # Build filters
        filters = {}
        if session_type:
            filters['session_type'] = session_type
        
        # Query from pgvector
        s_dicts = self.questions_store.list_records(
            record_type='practice_session',
            filters=filters if filters else None,
            sort_by='date',
            reverse=True,
            limit=limit or 1000
        )
        
        return [PracticeSession.from_dict(s_dict) for s_dict in s_dicts]

    def update_practice_session(self, session: PracticeSession):
        """Update practice session"""
        # Check if exists
        existing = self.questions_store.get_by_record_id('practice_session', session.id)
        if not existing:
            return False
        
        # Update in vector store
        try:
            from storage.vector_sync import sync_practice_session_to_vector_store
            sync_practice_session_to_vector_store(session, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update practice session in vector store: {e}")
            return False
        
        return True

    def delete_practice_session(self, session_id: str) -> bool:
        """Delete practice session"""
        # Check if exists
        existing = self.questions_store.get_by_record_id('practice_session', session_id)
        if not existing:
            return False
        
        # Delete from vector store
        try:
            from storage.vector_sync import delete_from_vector_store
            success = delete_from_vector_store('practice_session', session_id, self.user_id)
            return success
        except Exception as e:
            print(f"Warning: Could not delete practice session from vector store: {e}")
            return False

    # ========== Statistics ==========

    def get_stats(self) -> Dict:
        """Get interview prep statistics"""
        # Get data from pgvector
        questions = self.list_questions()
        concepts = self.list_concepts()
        sessions = self.list_practice_sessions()
        companies = self._read_json(self.companies_file)  # Company research still uses JSON

        # Question stats
        total_questions = len(questions)
        questions_by_type = {}
        questions_by_difficulty = {}
        practiced_questions = 0

        for q in questions:
            # By type
            q_type = q.type
            questions_by_type[q_type] = questions_by_type.get(q_type, 0) + 1

            # By difficulty
            difficulty = q.difficulty
            questions_by_difficulty[difficulty] = questions_by_difficulty.get(difficulty, 0) + 1

            # Practiced
            if q.practice_count > 0:
                practiced_questions += 1

        # Concept stats
        total_concepts = len(concepts)
        concepts_by_category = {}

        for c in concepts:
            category = c.category
            concepts_by_category[category] = concepts_by_category.get(category, 0) + 1

        # Practice stats
        total_sessions = len(sessions)
        total_practice_time = sum(s.duration_minutes for s in sessions)

        return {
            'total_questions': total_questions,
            'questions_by_type': questions_by_type,
            'questions_by_difficulty': questions_by_difficulty,
            'practiced_questions': practiced_questions,
            'practice_percentage': (practiced_questions / total_questions * 100) if total_questions > 0 else 0,
            'total_concepts': total_concepts,
            'concepts_by_category': concepts_by_category,
            'total_companies': len(companies),
            'total_practice_sessions': total_sessions,
            'total_practice_time_minutes': total_practice_time,
            'total_practice_time_hours': total_practice_time / 60 if total_practice_time > 0 else 0
        }
