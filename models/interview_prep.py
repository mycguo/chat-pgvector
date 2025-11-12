"""
Interview Preparation Data Models

Models for storing interview questions, answers, technical concepts,
company research, and practice sessions.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
import uuid


@dataclass
class InterviewQuestion:
    """
    Interview question with prepared answer.

    Supports behavioral, technical, and system design questions
    with STAR format answers and practice tracking.
    """
    question: str
    type: str  # behavioral, technical, system-design, case-study
    category: str  # leadership, conflict, algorithms, system-design, etc.
    difficulty: str  # easy, medium, hard
    answer_full: str
    id: str = field(default_factory=lambda: f"iq_{uuid.uuid4().hex[:8]}")
    answer_star: Optional[Dict] = None  # {situation, task, action, result}
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    companies: List[str] = field(default_factory=list)
    last_practiced: Optional[str] = None
    practice_count: int = 0
    confidence_level: int = 3  # 1-5 scale
    importance: int = 5  # 1-10 scale
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'InterviewQuestion':
        """Create from dictionary"""
        # Set default importance for existing questions
        if 'importance' not in data:
            data['importance'] = 5
        return InterviewQuestion(**data)

    def get_display_type(self) -> str:
        """Get formatted type for display"""
        type_map = {
            'behavioral': '🗣️ Behavioral',
            'technical': '💻 Technical',
            'system-design': '🏗️ System Design',
            'case-study': '📊 Case Study'
        }
        return type_map.get(self.type, self.type.title())

    def get_difficulty_emoji(self) -> str:
        """Get emoji for difficulty level"""
        difficulty_map = {
            'easy': '🟢',
            'medium': '🟡',
            'hard': '🔴'
        }
        return difficulty_map.get(self.difficulty, '⚪')

    def get_confidence_emoji(self) -> str:
        """Get emoji for confidence level"""
        if self.confidence_level >= 4:
            return '😊'
        elif self.confidence_level >= 3:
            return '😐'
        else:
            return '😰'

    def mark_practiced(self):
        """Mark question as practiced"""
        self.last_practiced = datetime.now().isoformat()
        self.practice_count += 1
        self.updated_at = datetime.now().isoformat()

    def update_confidence(self, level: int):
        """Update confidence level (1-5)"""
        self.confidence_level = max(1, min(5, level))
        self.updated_at = datetime.now().isoformat()

    def update_importance(self, level: int):
        """Update importance level (1-10)"""
        self.importance = max(1, min(10, level))
        self.updated_at = datetime.now().isoformat()

    def get_importance_emoji(self) -> str:
        """Get emoji for importance level"""
        if self.importance >= 8:
            return '🔥'
        elif self.importance >= 5:
            return '⭐'
        else:
            return '💡'


@dataclass
class TechnicalConcept:
    """
    Technical knowledge for interview prep.

    Stores explanations, code examples, and related questions.
    """
    concept: str
    category: str  # algorithms, system-design, databases, api-design, etc.
    content: str
    id: str = field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:8]}")
    code_examples: List[Dict] = field(default_factory=list)  # [{language, code, explanation}]
    key_points: List[str] = field(default_factory=list)
    related_questions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)  # Links to articles, docs, etc.
    last_reviewed: Optional[str] = None
    review_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'TechnicalConcept':
        """Create from dictionary"""
        return TechnicalConcept(**data)

    def get_category_emoji(self) -> str:
        """Get emoji for category"""
        category_map = {
            'algorithms': '🧮',
            'system-design': '🏗️',
            'databases': '🗄️',
            'api-design': '🔌',
            'networking': '🌐',
            'security': '🔒',
            'cloud': '☁️',
            'devops': '⚙️'
        }
        return category_map.get(self.category.lower(), '💻')

    def mark_reviewed(self):
        """Mark concept as reviewed"""
        self.last_reviewed = datetime.now().isoformat()
        self.review_count += 1
        self.updated_at = datetime.now().isoformat()


@dataclass
class CompanyResearch:
    """
    Company-specific interview preparation.

    Stores interview process, culture, tech stack, and interview experiences.
    """
    company: str
    id: str = field(default_factory=lambda: f"cr_{uuid.uuid4().hex[:8]}")
    culture: str = ""
    interview_process: Dict = field(default_factory=dict)  # {stages, duration, notes}
    tech_stack: List[str] = field(default_factory=list)
    interviewer_notes: Dict = field(default_factory=dict)  # {name: notes}
    questions_to_ask: List[str] = field(default_factory=list)
    my_experience: str = ""
    tips: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    application_ids: List[str] = field(default_factory=list)  # Link to applications
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'CompanyResearch':
        """Create from dictionary"""
        return CompanyResearch(**data)

    def link_application(self, app_id: str):
        """Link to an application"""
        if app_id not in self.application_ids:
            self.application_ids.append(app_id)
            self.updated_at = datetime.now().isoformat()


@dataclass
class PracticeSession:
    """
    Track practice sessions.

    Records questions practiced, performance, and notes.
    """
    date: str
    id: str = field(default_factory=lambda: f"ps_{uuid.uuid4().hex[:8]}")
    questions_practiced: List[str] = field(default_factory=list)  # Question IDs
    duration_minutes: int = 0
    performance: Dict = field(default_factory=dict)  # {question_id: {rating, notes}}
    notes: str = ""
    areas_to_improve: List[str] = field(default_factory=list)
    next_goals: List[str] = field(default_factory=list)
    session_type: str = "general"  # general, company-specific, topic-specific
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'PracticeSession':
        """Create from dictionary"""
        return PracticeSession(**data)

    def add_question(self, question_id: str, rating: int = 3, notes: str = ""):
        """Add question to practice session"""
        self.questions_practiced.append(question_id)
        self.performance[question_id] = {
            'rating': rating,
            'notes': notes,
            'timestamp': datetime.now().isoformat()
        }

    def get_average_rating(self) -> float:
        """Calculate average performance rating"""
        if not self.performance:
            return 0.0
        ratings = [p['rating'] for p in self.performance.values() if 'rating' in p]
        return sum(ratings) / len(ratings) if ratings else 0.0


# Helper functions for creating instances

def create_interview_question(
    question: str,
    type: str,
    category: str,
    difficulty: str,
    answer_full: str,
    answer_star: Optional[Dict] = None,
    notes: str = "",
    tags: Optional[List[str]] = None,
    companies: Optional[List[str]] = None,
    confidence_level: int = 3,
    importance: int = 5
) -> InterviewQuestion:
    """
    Create a new interview question.

    Args:
        question: The interview question text
        type: behavioral, technical, system-design, case-study
        category: leadership, conflict, algorithms, etc.
        difficulty: easy, medium, hard
        answer_full: Your complete answer
        answer_star: Optional STAR format answer {situation, task, action, result}
        notes: Additional notes
        tags: List of tags for categorization
        companies: Companies that ask this question
        confidence_level: 1-5 confidence in your answer
        importance: 1-10 importance level

    Returns:
        InterviewQuestion instance
    """
    return InterviewQuestion(
        question=question,
        type=type,
        category=category,
        difficulty=difficulty,
        answer_full=answer_full,
        answer_star=answer_star,
        notes=notes,
        tags=tags or [],
        companies=companies or [],
        confidence_level=confidence_level,
        importance=importance
    )


def create_technical_concept(
    concept: str,
    category: str,
    content: str,
    code_examples: Optional[List[Dict]] = None,
    key_points: Optional[List[str]] = None,
    related_questions: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    resources: Optional[List[str]] = None
) -> TechnicalConcept:
    """
    Create a new technical concept.

    Args:
        concept: Name of the concept
        category: algorithms, system-design, databases, etc.
        content: Detailed explanation
        code_examples: List of code examples
        key_points: Key takeaways
        related_questions: Related interview questions
        tags: Tags for categorization
        resources: Links to additional resources

    Returns:
        TechnicalConcept instance
    """
    return TechnicalConcept(
        concept=concept,
        category=category,
        content=content,
        code_examples=code_examples or [],
        key_points=key_points or [],
        related_questions=related_questions or [],
        tags=tags or [],
        resources=resources or []
    )


def create_company_research(
    company: str,
    culture: str = "",
    interview_process: Optional[Dict] = None,
    tech_stack: Optional[List[str]] = None,
    questions_to_ask: Optional[List[str]] = None,
    my_experience: str = "",
    tips: Optional[List[str]] = None
) -> CompanyResearch:
    """
    Create new company research entry.

    Args:
        company: Company name
        culture: Culture description
        interview_process: Interview process details
        tech_stack: Technologies they use
        questions_to_ask: Questions to ask interviewers
        my_experience: Your interview experience
        tips: Interview tips for this company

    Returns:
        CompanyResearch instance
    """
    return CompanyResearch(
        company=company,
        culture=culture,
        interview_process=interview_process or {},
        tech_stack=tech_stack or [],
        questions_to_ask=questions_to_ask or [],
        my_experience=my_experience,
        tips=tips or []
    )


def create_practice_session(
    date: Optional[str] = None,
    session_type: str = "general",
    duration_minutes: int = 0
) -> PracticeSession:
    """
    Create new practice session.

    Args:
        date: Session date (defaults to now)
        session_type: general, company-specific, topic-specific
        duration_minutes: Session duration

    Returns:
        PracticeSession instance
    """
    return PracticeSession(
        date=date or datetime.now().strftime("%Y-%m-%d"),
        session_type=session_type,
        duration_minutes=duration_minutes
    )
