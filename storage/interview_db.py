"""
Interview Preparation Database

JSON-based storage for interview questions, technical concepts,
company research, and practice sessions.
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


class InterviewDB:
    """Database for interview preparation materials"""

    def __init__(self, data_dir: str = None, user_id: str = None):
        """
        Initialize interview database.

        Args:
            data_dir: Directory for storing JSON files (if None, uses user-specific directory)
            user_id: Optional user ID (if None, will try to get from Streamlit)
        """
        if data_dir is None:
            data_dir = get_user_data_dir("interview_data", user_id)
        
        self.data_dir = data_dir
        self.user_id = user_id
        self._encryption_enabled = is_encryption_enabled()
        self.questions_file = os.path.join(data_dir, "questions.json")
        self.concepts_file = os.path.join(data_dir, "concepts.json")
        self.companies_file = os.path.join(data_dir, "companies.json")
        self.practice_file = os.path.join(data_dir, "practice.json")

        # Create directory and initialize files
        self._initialize()

    def _initialize(self):
        """Create data directory and initialize JSON files"""
        os.makedirs(self.data_dir, exist_ok=True)

        for file_path in [self.questions_file, self.concepts_file,
                          self.companies_file, self.practice_file]:
            if not os.path.exists(file_path):
                self._write_json(file_path, [])

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
        questions = self._read_json(self.questions_file)
        questions.append(question.to_dict())
        self._write_json(self.questions_file, questions)
        
        # Sync to vector store
        try:
            from storage.vector_sync import sync_interview_question_to_vector_store
            sync_interview_question_to_vector_store(question, self.user_id)
        except Exception as e:
            print(f"Warning: Could not sync question to vector store: {e}")
        
        return question.id

    def get_question(self, question_id: str) -> Optional[InterviewQuestion]:
        """Get question by ID"""
        questions = self._read_json(self.questions_file)
        for q in questions:
            if q['id'] == question_id:
                return InterviewQuestion.from_dict(q)
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
        questions = self._read_json(self.questions_file)
        result = []

        for q_data in questions:
            q = InterviewQuestion.from_dict(q_data)

            # Apply filters
            if type and q.type != type:
                continue
            if category and q.category != category:
                continue
            if difficulty and q.difficulty != difficulty:
                continue
            if company and company not in q.companies:
                continue
            if tag and tag not in q.tags:
                continue

            result.append(q)

        return result

    def update_question(self, question: InterviewQuestion):
        """Update question"""
        questions = self._read_json(self.questions_file)

        for i, q in enumerate(questions):
            if q['id'] == question.id:
                question.updated_at = datetime.now().isoformat()
                questions[i] = question.to_dict()
                self._write_json(self.questions_file, questions)
                
                # Sync to vector store
                try:
                    from storage.vector_sync import sync_interview_question_to_vector_store
                    sync_interview_question_to_vector_store(question, self.user_id)
                except Exception as e:
                    print(f"Warning: Could not sync question to vector store: {e}")
                
                return True

        return False

    def delete_question(self, question_id: str) -> bool:
        """Delete question"""
        questions = self._read_json(self.questions_file)
        filtered = [q for q in questions if q['id'] != question_id]

        if len(filtered) < len(questions):
            self._write_json(self.questions_file, filtered)
            
            # Delete from vector store
            try:
                from storage.vector_sync import delete_from_vector_store
                delete_from_vector_store('question', question_id, self.user_id)
            except Exception as e:
                print(f"Warning: Could not delete question from vector store: {e}")
            
            return True
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
        concepts = self._read_json(self.concepts_file)
        concepts.append(concept.to_dict())
        self._write_json(self.concepts_file, concepts)
        return concept.id

    def get_concept(self, concept_id: str) -> Optional[TechnicalConcept]:
        """Get concept by ID"""
        concepts = self._read_json(self.concepts_file)
        for c in concepts:
            if c['id'] == concept_id:
                return TechnicalConcept.from_dict(c)
        return None

    def list_concepts(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[TechnicalConcept]:
        """List technical concepts with optional filters"""
        concepts = self._read_json(self.concepts_file)
        result = []

        for c_data in concepts:
            c = TechnicalConcept.from_dict(c_data)

            if category and c.category != category:
                continue
            if tag and tag not in c.tags:
                continue

            result.append(c)

        return result

    def update_concept(self, concept: TechnicalConcept):
        """Update concept"""
        concepts = self._read_json(self.concepts_file)

        for i, c in enumerate(concepts):
            if c['id'] == concept.id:
                concept.updated_at = datetime.now().isoformat()
                concepts[i] = concept.to_dict()
                self._write_json(self.concepts_file, concepts)
                return True

        return False

    def delete_concept(self, concept_id: str) -> bool:
        """Delete concept"""
        concepts = self._read_json(self.concepts_file)
        filtered = [c for c in concepts if c['id'] != concept_id]

        if len(filtered) < len(concepts):
            self._write_json(self.concepts_file, filtered)
            return True
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
        sessions = self._read_json(self.practice_file)
        sessions.append(session.to_dict())
        self._write_json(self.practice_file, sessions)
        return session.id

    def get_practice_session(self, session_id: str) -> Optional[PracticeSession]:
        """Get practice session by ID"""
        sessions = self._read_json(self.practice_file)
        for s in sessions:
            if s['id'] == session_id:
                return PracticeSession.from_dict(s)
        return None

    def list_practice_sessions(
        self,
        session_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[PracticeSession]:
        """List practice sessions"""
        sessions = self._read_json(self.practice_file)
        result = []

        for s_data in sessions:
            s = PracticeSession.from_dict(s_data)

            if session_type and s.session_type != session_type:
                continue

            result.append(s)

        # Sort by date (most recent first)
        result.sort(key=lambda x: x.date, reverse=True)

        if limit:
            result = result[:limit]

        return result

    def update_practice_session(self, session: PracticeSession):
        """Update practice session"""
        sessions = self._read_json(self.practice_file)

        for i, s in enumerate(sessions):
            if s['id'] == session.id:
                sessions[i] = session.to_dict()
                self._write_json(self.practice_file, sessions)
                return True

        return False

    def delete_practice_session(self, session_id: str) -> bool:
        """Delete practice session"""
        sessions = self._read_json(self.practice_file)
        filtered = [s for s in sessions if s['id'] != session_id]

        if len(filtered) < len(sessions):
            self._write_json(self.practice_file, filtered)
            return True
        return False

    # ========== Statistics ==========

    def get_stats(self) -> Dict:
        """Get interview prep statistics"""
        questions = self._read_json(self.questions_file)
        concepts = self._read_json(self.concepts_file)
        companies = self._read_json(self.companies_file)
        sessions = self._read_json(self.practice_file)

        # Question stats
        total_questions = len(questions)
        questions_by_type = {}
        questions_by_difficulty = {}
        practiced_questions = 0

        for q in questions:
            # By type
            q_type = q.get('type', 'unknown')
            questions_by_type[q_type] = questions_by_type.get(q_type, 0) + 1

            # By difficulty
            difficulty = q.get('difficulty', 'unknown')
            questions_by_difficulty[difficulty] = questions_by_difficulty.get(difficulty, 0) + 1

            # Practiced
            if q.get('practice_count', 0) > 0:
                practiced_questions += 1

        # Concept stats
        total_concepts = len(concepts)
        concepts_by_category = {}

        for c in concepts:
            category = c.get('category', 'unknown')
            concepts_by_category[category] = concepts_by_category.get(category, 0) + 1

        # Practice stats
        total_sessions = len(sessions)
        total_practice_time = sum(s.get('duration_minutes', 0) for s in sessions)

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
