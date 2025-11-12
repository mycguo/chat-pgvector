"""
Company Data Models

Models for tracking companies - both applied and target companies.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
import uuid


@dataclass
class Company:
    """
    Company information for tracking applications and targets.

    Tracks company details, status, and related applications.
    """
    name: str
    id: str = field(default_factory=lambda: f"comp_{uuid.uuid4().hex[:8]}")
    status: str = "target"  # target, applied, interviewing, offer, rejected, accepted
    website: str = ""
    industry: str = ""
    size: str = ""  # startup, small, medium, large, enterprise
    location: str = ""
    description: str = ""
    culture_notes: str = ""
    tech_stack: List[str] = field(default_factory=list)
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    contacts: List[str] = field(default_factory=list)  # Names or LinkedIn URLs
    application_ids: List[str] = field(default_factory=list)  # Link to applications
    notes: str = ""
    priority: int = 5  # 1-10 scale
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'Company':
        """Create from dictionary"""
        # Set defaults for new fields
        if 'priority' not in data:
            data['priority'] = 5
        if 'status' not in data:
            data['status'] = 'target'
        return Company(**data)

    def get_status_emoji(self) -> str:
        """Get emoji for company status"""
        status_map = {
            'target': '🎯',
            'applied': '📝',
            'interviewing': '💼',
            'offer': '🎉',
            'rejected': '❌',
            'accepted': '✅'
        }
        return status_map.get(self.status, '📋')

    def get_priority_emoji(self) -> str:
        """Get emoji for priority level"""
        if self.priority >= 8:
            return '🔥'
        elif self.priority >= 5:
            return '⭐'
        else:
            return '💡'

    def get_size_emoji(self) -> str:
        """Get emoji for company size"""
        size_map = {
            'startup': '🚀',
            'small': '🏢',
            'medium': '🏛️',
            'large': '🏰',
            'enterprise': '🌐'
        }
        return size_map.get(self.size.lower(), '🏢')

    def link_application(self, app_id: str):
        """Link to an application"""
        if app_id not in self.application_ids:
            self.application_ids.append(app_id)
            self.updated_at = datetime.now().isoformat()

    def update_status(self, status: str):
        """Update company status"""
        self.status = status
        self.updated_at = datetime.now().isoformat()

    def update_priority(self, priority: int):
        """Update priority level (1-10)"""
        self.priority = max(1, min(10, priority))
        self.updated_at = datetime.now().isoformat()


def create_company(
    name: str,
    status: str = "target",
    website: str = "",
    industry: str = "",
    size: str = "",
    location: str = "",
    description: str = "",
    priority: int = 5
) -> Company:
    """
    Create a new company entry.

    Args:
        name: Company name
        status: target, applied, interviewing, offer, rejected, accepted
        website: Company website URL
        industry: Industry/sector
        size: startup, small, medium, large, enterprise
        location: Company location
        description: Company description
        priority: Priority level 1-10

    Returns:
        Company instance
    """
    return Company(
        name=name,
        status=status,
        website=website,
        industry=industry,
        size=size,
        location=location,
        description=description,
        priority=priority
    )
