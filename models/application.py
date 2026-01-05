"""
Application data model for tracking job applications.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict
import uuid


@dataclass
class ContactLink:
    """Reference to a single contact person"""
    name: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ApplicationEvent:
    """Timeline event for an application"""
    date: str
    event_type: str  # applied, screening, interview, offer, rejected, etc.
    notes: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Application:
    """
    Job application tracking model.

    Statuses:
    - tracking: Opportunity you're monitoring but haven't applied to yet
    - applied: Initial application submitted
    - screening: Phone/initial screening in progress
    - interview: Technical/onsite interview stage
    - offer: Offer received
    - accepted: Offer accepted
    - rejected: Application rejected
    - withdrawn: You withdrew application
    """

    company: str
    role: str
    status: str
    applied_date: str
    id: str = field(default_factory=lambda: f"app_{uuid.uuid4().hex[:8]}")
    job_url: Optional[str] = None
    job_description: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    match_score: Optional[float] = None
    notes: Optional[str] = None
    cover_letter: Optional[str] = None  # Generated cover letter
    timeline: List[ApplicationEvent] = field(default_factory=list)
    job_requirements: Optional[Dict] = None  # Extracted requirements
    recruiter_contact: Optional[ContactLink] = None
    hiring_manager_contact: Optional[ContactLink] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Validate data after initialization"""
        valid_statuses = ["tracking", "applied", "screening", "interview", "offer", "accepted", "rejected", "withdrawn"]
        if self.status.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")

        # Normalize status to lowercase
        self.status = self.status.lower()

        # Add initial event if timeline is empty
        if not self.timeline:
            if self.status == "tracking":
                initial_note = f"Tracking opportunity at {self.company} for {self.role}"
            else:
                initial_note = f"Applied to {self.company} for {self.role}"
            self.timeline.append(ApplicationEvent(
                date=self.applied_date,
                event_type=self.status,
                notes=initial_note
            ))

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert timeline events
        data['timeline'] = [event.to_dict() if isinstance(event, ApplicationEvent) else event
                           for event in self.timeline]
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Application':
        """Create Application from dictionary"""
        # Convert timeline events
        if 'timeline' in data and data['timeline']:
            timeline = [ApplicationEvent(**event) if isinstance(event, dict) else event
                       for event in data['timeline']]
            data['timeline'] = timeline

        # Normalize contact links
        for contact_field in ('recruiter_contact', 'hiring_manager_contact'):
            if contact_field in data and data[contact_field]:
                contact_data = data[contact_field]
                if isinstance(contact_data, dict):
                    data[contact_field] = ContactLink(**contact_data)
        return cls(**data)

    def add_event(self, event_type: str, notes: Optional[str] = None):
        """Add a timeline event"""
        event = ApplicationEvent(
            date=datetime.now().strftime("%Y-%m-%d"),
            event_type=event_type,
            notes=notes
        )
        self.timeline.append(event)
        self.updated_at = datetime.now().isoformat()

    def update_status(self, new_status: str, notes: Optional[str] = None):
        """Update application status and add timeline event"""
        old_status = self.status
        self.status = new_status.lower()
        self.updated_at = datetime.now().isoformat()

        # Add timeline event
        self.add_event(
            event_type=new_status,
            notes=notes or f"Status changed from {old_status} to {new_status}"
        )

    def get_display_status(self) -> str:
        """Get formatted status for display"""
        return self.status.replace('_', ' ').title()

    def get_days_since_applied(self) -> int:
        """Calculate days since application"""
        try:
            applied = datetime.strptime(self.applied_date, "%Y-%m-%d")
            delta = datetime.now() - applied
            return delta.days
        except:
            return 0

    def is_active(self) -> bool:
        """Check if application is still active"""
        return self.status in ["tracking", "applied", "screening", "interview", "offer"]

    def get_status_emoji(self) -> str:
        """Get emoji representation of status"""
        emoji_map = {
            "tracking": "📌",
            "applied": "📧",
            "screening": "📞",
            "interview": "💼",
            "offer": "🎉",
            "accepted": "✅",
            "rejected": "❌",
            "withdrawn": "🚫"
        }
        return emoji_map.get(self.status, "⚪")


def create_application(
    company: str,
    role: str,
    applied_date: Optional[str] = None,
    **kwargs
) -> Application:
    """
    Helper function to create an application with defaults.

    Args:
        company: Company name
        role: Job role/title
        applied_date: Date applied (defaults to today)
        **kwargs: Additional fields

    Returns:
        Application instance
    """
    if applied_date is None:
        applied_date = datetime.now().strftime("%Y-%m-%d")

    return Application(
        company=company,
        role=role,
        status=kwargs.pop('status', 'applied'),
        applied_date=applied_date,
        **kwargs
    )
