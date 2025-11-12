"""
Test suite for Job Search Database and Application models.
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime
from models.application import Application, ApplicationEvent, ContactLink, create_application
from storage.json_db import JobSearchDB


class TestApplicationModel:
    """Test Application data model"""

    def test_create_basic_application(self):
        """Test creating a basic application"""
        app = Application(
            company="Google",
            role="ML Engineer",
            status="applied",
            applied_date="2025-11-01"
        )

        assert app.company == "Google"
        assert app.role == "ML Engineer"
        assert app.status == "applied"
        assert app.id.startswith("app_")
        assert len(app.timeline) == 1  # Initial event

    def test_application_status_validation(self):
        """Test that invalid status raises error"""
        with pytest.raises(ValueError):
            Application(
                company="Google",
                role="ML Engineer",
                status="invalid_status",
                applied_date="2025-11-01"
            )

    def test_application_update_status(self):
        """Test updating application status"""
        app = Application(
            company="Google",
            role="ML Engineer",
            status="applied",
            applied_date="2025-11-01"
        )

        app.update_status("screening", "Phone screen scheduled")

        assert app.status == "screening"
        assert len(app.timeline) == 2
        assert app.timeline[-1].event_type == "screening"

    def test_application_to_dict(self):
        """Test converting application to dictionary"""
        app = Application(
            company="Google",
            role="ML Engineer",
            status="applied",
            applied_date="2025-11-01",
            location="San Francisco",
            salary_range="$180k-$250k"
        )

        data = app.to_dict()

        assert data['company'] == "Google"
        assert data['role'] == "ML Engineer"
        assert data['location'] == "San Francisco"
        assert isinstance(data['timeline'], list)

    def test_application_from_dict(self):
        """Test creating application from dictionary"""
        data = {
            'id': 'app_test123',
            'company': 'Meta',
            'role': 'Senior Engineer',
            'status': 'interview',
            'applied_date': '2025-11-05',
            'location': 'Remote',
            'timeline': [
                {'date': '2025-11-05', 'event_type': 'applied', 'notes': None}
            ]
        }

        app = Application.from_dict(data)

        assert app.company == "Meta"
        assert app.role == "Senior Engineer"
        assert app.id == "app_test123"
        assert len(app.timeline) == 1

    def test_application_contact_links_serialization(self):
        """Ensure recruiter/hiring manager links persist through serialization"""
        recruiter = ContactLink(name="Jane Recruiter", url="https://linkedin.com/in/jane")
        hiring_manager = ContactLink(name="Alex Lead", url="https://linkedin.com/in/alex")

        app = Application(
            company="Reflection AI",
            role="Forward Deployed Engineer",
            status="applied",
            applied_date="2025-11-06",
            recruiter_contact=recruiter,
            hiring_manager_contact=hiring_manager
        )

        data = app.to_dict()
        assert data['recruiter_contact']['name'] == "Jane Recruiter"
        assert data['hiring_manager_contact']['url'] == "https://linkedin.com/in/alex"

        restored = Application.from_dict(data)
        assert restored.recruiter_contact.name == "Jane Recruiter"
        assert restored.hiring_manager_contact.url.endswith("/alex")

    def test_create_application_helper(self):
        """Test create_application helper function"""
        app = create_application(
            company="Anthropic",
            role="AI Engineer",
            location="San Francisco",
            salary_range="$200k-$280k"
        )

        assert app.company == "Anthropic"
        assert app.status == "applied"
        assert app.applied_date == datetime.now().strftime("%Y-%m-%d")

    def test_application_is_active(self):
        """Test is_active method"""
        app1 = create_application("Google", "Engineer", status="interview")
        app2 = create_application("Meta", "Engineer", status="rejected")

        assert app1.is_active() is True
        assert app2.is_active() is False

    def test_application_status_emoji(self):
        """Test status emoji representation"""
        app = create_application("Google", "Engineer")

        assert app.get_status_emoji() == "📧"

        app.update_status("interview")
        assert app.get_status_emoji() == "💼"

        app.update_status("offer")
        assert app.get_status_emoji() == "🎉"


class TestJobSearchDB:
    """Test JobSearchDB storage layer"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_dir = tempfile.mkdtemp()
        db = JobSearchDB(data_dir=temp_dir)
        yield db
        shutil.rmtree(temp_dir)

    def test_db_initialization(self, temp_db):
        """Test database initialization"""
        assert os.path.exists(temp_db.applications_file)
        assert os.path.exists(temp_db.contacts_file)
        assert os.path.exists(temp_db.profile_file)

    def test_add_application(self, temp_db):
        """Test adding an application"""
        app = create_application(
            company="Google",
            role="ML Engineer",
            location="San Francisco"
        )

        app_id = temp_db.add_application(app)

        assert app_id == app.id
        assert app_id.startswith("app_")

    def test_get_application(self, temp_db):
        """Test retrieving an application"""
        app = create_application("Google", "ML Engineer")
        app_id = temp_db.add_application(app)

        retrieved = temp_db.get_application(app_id)

        assert retrieved is not None
        assert retrieved.company == "Google"
        assert retrieved.role == "ML Engineer"
        assert retrieved.id == app_id

    def test_list_applications(self, temp_db):
        """Test listing applications"""
        # Add multiple applications
        apps = [
            create_application("Google", "ML Engineer", status="applied"),
            create_application("Meta", "Senior Engineer", status="screening"),
            create_application("OpenAI", "AI Engineer", status="interview"),
        ]

        for app in apps:
            temp_db.add_application(app)

        all_apps = temp_db.list_applications()
        assert len(all_apps) == 3

        # Test filtering by status
        interview_apps = temp_db.list_applications(status="interview")
        assert len(interview_apps) == 1
        assert interview_apps[0].company == "OpenAI"

    def test_update_application_status(self, temp_db):
        """Test updating application status"""
        app = create_application("Google", "ML Engineer")
        app_id = temp_db.add_application(app)

        success = temp_db.update_status(app_id, "screening", "Phone screen scheduled")

        assert success is True

        updated = temp_db.get_application(app_id)
        assert updated.status == "screening"
        assert len(updated.timeline) == 2

    def test_duplicate_application_prevention(self, temp_db):
        """Test that duplicate active applications are prevented"""
        app1 = create_application("Google", "ML Engineer", status="applied")
        temp_db.add_application(app1)

        app2 = create_application("Google", "ML Engineer", status="screening")

        with pytest.raises(ValueError, match="Active application already exists"):
            temp_db.add_application(app2)

    def test_delete_application(self, temp_db):
        """Test deleting an application"""
        app = create_application("Google", "ML Engineer")
        app_id = temp_db.add_application(app)

        success = temp_db.delete_application(app_id)
        assert success is True

        retrieved = temp_db.get_application(app_id)
        assert retrieved is None

    def test_add_application_note(self, temp_db):
        """Test adding notes to application"""
        app = create_application("Google", "ML Engineer")
        app_id = temp_db.add_application(app)

        success = temp_db.add_application_note(app_id, "Met with recruiter Jane")
        assert success is True

        updated = temp_db.get_application(app_id)
        assert "Met with recruiter Jane" in updated.notes

    def test_search_applications(self, temp_db):
        """Test searching applications"""
        apps = [
            create_application("Google", "ML Engineer", location="San Francisco"),
            create_application("Meta", "AI Researcher", location="Remote"),
            create_application("OpenAI", "Senior Engineer", location="San Francisco"),
        ]

        for app in apps:
            temp_db.add_application(app)

        # Search by company
        results = temp_db.search_applications("Google")
        assert len(results) == 1
        assert results[0].company == "Google"

        # Search by location
        results = temp_db.search_applications("San Francisco")
        assert len(results) == 2

        # Search by role keyword
        results = temp_db.search_applications("ML")
        assert len(results) == 1

    def test_get_stats(self, temp_db):
        """Test getting application statistics"""
        apps = [
            create_application("Google", "ML Engineer", status="applied"),
            create_application("Meta", "Senior Engineer", status="screening"),
            create_application("OpenAI", "AI Engineer", status="interview"),
            create_application("Anthropic", "Engineer", status="offer"),
            create_application("Stripe", "Backend Engineer", status="rejected"),
        ]

        for app in apps:
            temp_db.add_application(app)

        stats = temp_db.get_stats()

        assert stats['total'] == 5
        assert stats['active'] == 4  # All except rejected
        assert stats['by_status']['applied'] == 1
        assert stats['by_status']['screening'] == 1
        assert stats['by_status']['interview'] == 1
        assert stats['by_status']['offer'] == 1
        assert stats['by_status']['rejected'] == 1
        assert stats['response_rate'] > 0

    def test_list_applications_sorting(self, temp_db):
        """Test sorting applications"""
        apps = [
            create_application("Google", "Engineer", applied_date="2025-11-01"),
            create_application("Meta", "Engineer", applied_date="2025-11-05"),
            create_application("OpenAI", "Engineer", applied_date="2025-11-03"),
        ]

        for app in apps:
            temp_db.add_application(app)

        # Sort by date (newest first - default)
        sorted_apps = temp_db.list_applications(sort_by="applied_date", reverse=True)
        assert sorted_apps[0].company == "Meta"  # Nov 5
        assert sorted_apps[1].company == "OpenAI"  # Nov 3
        assert sorted_apps[2].company == "Google"  # Nov 1

        # Sort by company alphabetically
        sorted_apps = temp_db.list_applications(sort_by="company", reverse=False)
        assert sorted_apps[0].company == "Google"
        assert sorted_apps[1].company == "Meta"
        assert sorted_apps[2].company == "OpenAI"


def test_end_to_end_workflow():
    """Test complete application workflow"""
    # Create temp database
    temp_dir = tempfile.mkdtemp()
    db = JobSearchDB(data_dir=temp_dir)

    try:
        # 1. Apply to job
        app = create_application(
            company="Google",
            role="ML Engineer",
            location="San Francisco",
            salary_range="$180k-$250k",
            job_url="https://careers.google.com/ml-engineer"
        )
        app_id = db.add_application(app)
        print(f"✓ Applied to {app.company}")

        # 2. Get phone screen
        db.update_status(app_id, "screening", "Phone screen with recruiter")
        print(f"✓ Status updated to screening")

        # 3. Technical interview
        db.update_status(app_id, "interview", "Onsite interview scheduled")
        db.add_application_note(app_id, "Prepare: System design and ML questions")
        print(f"✓ Interview scheduled")

        # 4. Receive offer
        db.update_status(app_id, "offer", "Received offer!")
        db.add_application_note(app_id, "Offer: $220k base + equity")
        print(f"✓ Offer received")

        # 5. Check final state
        final_app = db.get_application(app_id)
        assert final_app.status == "offer"
        assert len(final_app.timeline) == 4
        assert "Offer: $220k" in final_app.notes

        print(f"\n✓ Complete workflow test passed!")
        print(f"  Company: {final_app.company}")
        print(f"  Status: {final_app.get_status_emoji()} {final_app.get_display_status()}")
        print(f"  Timeline events: {len(final_app.timeline)}")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Run quick test
    test_end_to_end_workflow()

    # Run full test suite
    pytest.main([__file__, "-v", "-s"])
