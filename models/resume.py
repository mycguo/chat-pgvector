"""
Resume Data Models

Models for managing resumes, versions, and tailored variations.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
import uuid


@dataclass
class Resume:
    """
    Resume with version control and tailoring support.

    Stores both raw content and structured data for easy editing
    and AI-powered tailoring.
    """
    name: str  # Resume name/title (e.g., "Software Engineer Resume", "ML Engineer Resume")
    id: str = field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")

    # Content
    full_text: str = ""  # Full text content extracted from file
    original_filename: Optional[str] = None
    file_type: Optional[str] = None  # pdf, docx, txt
    file_path: Optional[str] = None  # Path to stored file

    # Structured sections (for future AI editing)
    sections: Dict = field(default_factory=dict)  # {section_name: content}

    # Metadata
    skills: List[str] = field(default_factory=list)
    experience_years: Optional[int] = None
    education: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

    # Version control
    version: str = "1.0"
    is_master: bool = True  # Master/template resume
    parent_id: Optional[str] = None  # If tailored, ID of master resume

    # Tailoring info
    tailored_for_job: Optional[str] = None  # Job ID if tailored for specific job
    tailored_for_company: Optional[str] = None
    tailoring_notes: str = ""

    # Status
    is_active: bool = True
    last_used: Optional[str] = None

    # Analytics
    applications_count: int = 0  # Number of applications using this resume
    success_rate: float = 0.0  # Interview rate with this resume

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'Resume':
        """Create from dictionary"""
        return Resume(**data)

    def mark_used(self):
        """Mark resume as used"""
        self.last_used = datetime.now().isoformat()
        self.applications_count += 1
        self.updated_at = datetime.now().isoformat()

    def update_success_rate(self, interviews: int, applications: int):
        """Update success rate based on interview results"""
        if applications > 0:
            self.success_rate = (interviews / applications) * 100
            self.updated_at = datetime.now().isoformat()

    def get_summary(self) -> str:
        """Get brief summary of resume"""
        summary = f"{self.name} (v{self.version})"
        if self.tailored_for_company:
            summary += f" - Tailored for {self.tailored_for_company}"
        if self.is_master:
            summary += " [Master]"
        return summary

    def get_status_emoji(self) -> str:
        """Get emoji for status"""
        if not self.is_active:
            return "⚫"
        if self.is_master:
            return "⭐"
        if self.tailored_for_job:
            return "🎯"
        return "📄"


@dataclass
class ResumeVersion:
    """
    Track resume versions and changes.

    Useful for maintaining history and reverting changes.
    """
    resume_id: str
    version: str
    id: str = field(default_factory=lambda: f"rv_{uuid.uuid4().hex[:8]}")

    # Content snapshot
    full_text: str = ""
    sections: Dict = field(default_factory=dict)

    # Change tracking
    changes_summary: str = ""
    changed_by: str = "user"  # user or ai

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'ResumeVersion':
        """Create from dictionary"""
        return ResumeVersion(**data)


# Helper functions

def create_resume(
    name: str,
    full_text: str,
    original_filename: Optional[str] = None,
    file_type: Optional[str] = None,
    file_path: Optional[str] = None,
    skills: Optional[List[str]] = None,
    is_master: bool = True
) -> Resume:
    """
    Create a new resume.

    Args:
        name: Resume name/title
        full_text: Full text content
        original_filename: Original uploaded filename
        file_type: File type (pdf, docx, txt)
        file_path: Path to stored file
        skills: List of skills
        is_master: Whether this is a master/template resume

    Returns:
        Resume instance
    """
    return Resume(
        name=name,
        full_text=full_text,
        original_filename=original_filename,
        file_type=file_type,
        file_path=file_path,
        skills=skills or [],
        is_master=is_master
    )


def create_tailored_resume(
    master_resume: Resume,
    job_id: str,
    company: str,
    tailoring_notes: str = ""
) -> Resume:
    """
    Create a tailored version of a master resume.

    Args:
        master_resume: The master resume to tailor from
        job_id: Job application ID
        company: Company name
        tailoring_notes: Notes about tailoring

    Returns:
        New tailored Resume instance
    """
    # Create new version with incremented version number
    major, minor = master_resume.version.split('.')
    new_version = f"{major}.{int(minor) + 1}"

    return Resume(
        name=f"{master_resume.name} - {company}",
        full_text=master_resume.full_text,  # Start with same content
        original_filename=master_resume.original_filename,
        file_type=master_resume.file_type,
        file_path=master_resume.file_path,
        sections=master_resume.sections.copy(),
        skills=master_resume.skills.copy(),
        experience_years=master_resume.experience_years,
        education=master_resume.education.copy(),
        certifications=master_resume.certifications.copy(),
        version=new_version,
        is_master=False,
        parent_id=master_resume.id,
        tailored_for_job=job_id,
        tailored_for_company=company,
        tailoring_notes=tailoring_notes
    )


def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract common skills from resume text.

    This is a simple keyword-based extraction. Can be enhanced with AI.

    Args:
        text: Resume text

    Returns:
        List of detected skills
    """
    # Common tech skills to look for
    common_skills = [
        # Programming languages
        'python', 'java', 'javascript', 'typescript', 'go', 'rust',
        'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',

        # Frameworks/Libraries
        'react', 'vue', 'angular', 'node', 'django', 'flask',
        'spring', 'express', 'fastapi', 'next.js', 'svelte',

        # Databases
        'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
        'dynamodb', 'elasticsearch', 'cassandra',

        # Cloud/DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'jenkins', 'github actions', 'ci/cd', 'linux',

        # AI/ML
        'machine learning', 'deep learning', 'tensorflow', 'pytorch',
        'scikit-learn', 'nlp', 'computer vision', 'llm',

        # Other
        'git', 'agile', 'scrum', 'rest api', 'graphql',
        'microservices', 'system design', 'architecture'
    ]

    text_lower = text.lower()
    found_skills = []

    for skill in common_skills:
        if skill in text_lower:
            found_skills.append(skill.title())

    return list(set(found_skills))  # Remove duplicates
