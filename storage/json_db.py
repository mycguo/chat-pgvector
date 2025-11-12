"""
Database for job search data.

Uses PostgreSQL + pgvector as the single source of truth.
Maintains backward compatibility with existing API.
"""

import json
import os
from typing import List, Optional, Dict, Callable
from datetime import datetime
from models.application import Application
from storage.user_utils import get_user_data_dir
from storage.encryption import encrypt_data, decrypt_data, is_encryption_enabled
from storage.pg_vector_store import PgVectorStore


class JobSearchDB:
    """Database for job search data using PostgreSQL + pgvector"""

    def __init__(self, data_dir: str = None, user_id: str = None):
        """
        Initialize database.

        Args:
            data_dir: Directory to store JSON files (deprecated, kept for compatibility)
            user_id: Optional user ID (if None, will try to get from Streamlit)
        """
        if data_dir is None:
            data_dir = get_user_data_dir("job_search_data", user_id)
        
        self.data_dir = data_dir
        self.user_id = user_id
        self._encryption_enabled = is_encryption_enabled()
        
        # Initialize pgvector stores for each collection
        self.applications_store = PgVectorStore(collection_name="applications", user_id=user_id)
        self.companies_store = PgVectorStore(collection_name="companies", user_id=user_id)
        self.contacts_store = PgVectorStore(collection_name="contacts", user_id=user_id)
        self.quick_notes_store = PgVectorStore(collection_name="quick_notes", user_id=user_id)
        
        # Keep JSON file paths for backward compatibility (profile only)
        os.makedirs(data_dir, exist_ok=True)
        self.profile_file = os.path.join(data_dir, "profile.json")

        # Initialize files if they don't exist
        self._init_file(self.profile_file, {})

    def _init_file(self, filepath: str, default_content):
        """Create file with default content if it doesn't exist"""
        if not os.path.exists(filepath):
            self._write_json(filepath, default_content)

    def _read_json(self, filepath: str):
        """Read JSON file (with optional decryption)"""
        try:
            if self._encryption_enabled:
                # Read encrypted file as binary
                with open(filepath, 'rb') as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        decrypted_data = decrypt_data(encrypted_data, self.user_id)
                        return json.loads(decrypted_data.decode('utf-8'))
                    else:
                        return [] if filepath != self.profile_file else {}
            else:
                # Read plain JSON file
                with open(filepath, 'r') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading {filepath}: {e}")
            return [] if filepath != self.profile_file else {}
        except Exception as e:
            # If decryption fails, try reading as plain JSON (for migration)
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                # Don't print the error again if it's the same decryption error
                if "decrypt" not in str(e).lower() and "fernet" not in str(e).lower():
                    print(f"Error reading {filepath}: {e}")
                return [] if filepath != self.profile_file else {}

    def _write_json(self, filepath: str, data):
        """Write JSON file (with optional encryption)"""
        try:
            json_data = json.dumps(data, indent=2, ensure_ascii=False)
            
            if self._encryption_enabled:
                # Write encrypted file as binary
                encrypted_data = encrypt_data(json_data.encode('utf-8'), self.user_id)
                with open(filepath, 'wb') as f:
                    f.write(encrypted_data)
            else:
                # Write plain JSON file
                with open(filepath, 'w') as f:
                    f.write(json_data)
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            raise

    # ==================== APPLICATION CRUD ====================

    def add_application(self, app: Application) -> str:
        """
        Add new application.

        Args:
            app: Application instance

        Returns:
            Application ID
        """
        # Check for duplicate using pgvector
        existing_apps = self.applications_store.list_records(
            record_type='application',
            filters={'company': app.company, 'role': app.role}
        )
        
        for existing in existing_apps:
            if existing.get('status') not in ['rejected', 'withdrawn', 'accepted']:
                raise ValueError(f"Active application already exists for {app.company} - {app.role}")

        # Add to vector store (which stores full structured data)
        try:
            from storage.vector_sync import sync_application_to_vector_store
            sync_application_to_vector_store(app, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add application to vector store: {e}")
            raise

        print(f"✅ Added application: {app.company} - {app.role} (ID: {app.id})")
        return app.id

    def get_application(self, app_id: str) -> Optional[Application]:
        """
        Get application by ID.

        Args:
            app_id: Application ID

        Returns:
            Application instance or None
        """
        app_dict = self.applications_store.get_by_record_id('application', app_id)
        if app_dict:
            return Application.from_dict(app_dict)
        return None

    def list_applications(
        self,
        status: Optional[str] = None,
        company: Optional[str] = None,
        sort_by: str = "applied_date",
        reverse: bool = True
    ) -> List[Application]:
        """
        List applications with optional filtering.

        Args:
            status: Filter by status (e.g., 'applied', 'interview')
            company: Filter by company name (exact match)
            sort_by: Field to sort by (default: applied_date)
            reverse: Sort in reverse order (default: True - newest first)

        Returns:
            List of Application instances
        """
        # Build filters
        filters = {}
        if status:
            filters['status'] = status.lower()
        if company:
            filters['company'] = company  # Exact match for now
        
        # Query from pgvector
        app_dicts = self.applications_store.list_records(
            record_type='application',
            filters=filters if filters else None,
            sort_by=sort_by,
            reverse=reverse,
            limit=1000  # Reasonable limit
        )
        
        results = []
        for app_dict in app_dicts:
            app = Application.from_dict(app_dict)
            
            # Apply partial match for company if needed
            if company and company.lower() not in app.company.lower():
                continue
            
            results.append(app)
        
        # If company filter was partial match, sort again
        if company and not filters.get('company'):
            if sort_by == "applied_date":
                results.sort(key=lambda x: x.applied_date, reverse=reverse)
            elif sort_by == "company":
                results.sort(key=lambda x: x.company.lower(), reverse=reverse)
            elif sort_by == "updated_at":
                results.sort(key=lambda x: x.updated_at, reverse=reverse)

        return results

    def update_application(self, app_id: str, updates: Dict) -> bool:
        """
        Update application fields.

        Args:
            app_id: Application ID
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        # Get existing application
        app_dict = self.applications_store.get_by_record_id('application', app_id)
        if not app_dict:
            print(f"❌ Application not found: {app_id}")
            return False
        
        # Update fields
        app = Application.from_dict(app_dict)
        for key, value in updates.items():
            if hasattr(app, key):
                setattr(app, key, value)

        app.updated_at = datetime.now().isoformat()

        # Update in vector store
        try:
            from storage.vector_sync import sync_application_to_vector_store
            sync_application_to_vector_store(app, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update application in vector store: {e}")
            return False

        print(f"✅ Updated application: {app.company} - {app.role}")
        return True

    def update_status(self, app_id: str, new_status: str, notes: Optional[str] = None) -> bool:
        """
        Update application status and add timeline event.

        Args:
            app_id: Application ID
            new_status: New status
            notes: Optional notes

        Returns:
            True if successful
        """
        # Get existing application
        app_dict = self.applications_store.get_by_record_id('application', app_id)
        if not app_dict:
            print(f"❌ Application not found: {app_id}")
            return False
        
        app = Application.from_dict(app_dict)
        old_status = app.status
        app.update_status(new_status, notes)

        # Update in vector store
        try:
            from storage.vector_sync import sync_application_to_vector_store
            sync_application_to_vector_store(app, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update application status in vector store: {e}")
            return False

        print(f"✅ Status updated: {app.company} - {old_status} → {new_status}")
        return True

    def delete_application(self, app_id: str) -> bool:
        """
        Delete application.

        Args:
            app_id: Application ID

        Returns:
            True if successful
        """
        # Check if exists
        app_dict = self.applications_store.get_by_record_id('application', app_id)
        if not app_dict:
            print(f"❌ Application not found: {app_id}")
            return False
        
        # Delete from vector store
        try:
            from storage.vector_sync import delete_from_vector_store
            success = delete_from_vector_store('application', app_id, self.user_id)
            if success:
                print(f"✅ Deleted application: {app_id}")
                return True
            else:
                print(f"❌ Failed to delete application: {app_id}")
                return False
        except Exception as e:
            print(f"Warning: Could not delete application from vector store: {e}")
            return False

    def add_application_note(self, app_id: str, note: str) -> bool:
        """
        Add note to application.

        Args:
            app_id: Application ID
            note: Note text

        Returns:
            True if successful
        """
        app = self.get_application(app_id)
        if not app:
            return False

        current_notes = app.notes or ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_note = f"[{timestamp}] {note}"

        if current_notes:
            app.notes = f"{current_notes}\n{new_note}"
        else:
            app.notes = new_note

        return self.update_application(app_id, {"notes": app.notes})

    def add_timeline_event(self, app_id: str, event_type: str, event_date: str, notes: Optional[str] = None) -> bool:
        """
        Add a timeline event to an application.

        Args:
            app_id: Application ID
            event_type: Type of event (e.g., 'interview', 'screening', 'offer')
            event_date: Date of the event (format: YYYY-MM-DD)
            notes: Optional notes about the event

        Returns:
            True if successful
        """
        applications = self._read_json(self.applications_file)

        for i, app_dict in enumerate(applications):
            if app_dict['id'] == app_id:
                app = Application.from_dict(app_dict)
                
                # Add the event using the Application's add_event method
                # But we need to create the event with the specified date
                from models.application import ApplicationEvent
                event = ApplicationEvent(
                    date=event_date,
                    event_type=event_type,
                    notes=notes
                )
                app.timeline.append(event)
                app.updated_at = datetime.now().isoformat()

                applications[i] = app.to_dict()
                self._write_json(self.applications_file, applications)

                print(f"✅ Added timeline event: {event_type} on {event_date}")
                return True

        print(f"❌ Application not found: {app_id}")
        return False

    def update_timeline_event(self, app_id: str, event_index: int, event_type: str = None, event_date: str = None, notes: str = None) -> bool:
        """
        Update a timeline event in an application.

        Args:
            app_id: Application ID
            event_index: Index of the event in the timeline
            event_type: New event type (optional)
            event_date: New event date (optional, format: YYYY-MM-DD)
            notes: New notes (optional)

        Returns:
            True if successful
        """
        applications = self._read_json(self.applications_file)

        for i, app_dict in enumerate(applications):
            if app_dict['id'] == app_id:
                app = Application.from_dict(app_dict)
                
                # Check if event_index is valid
                if event_index < 0 or event_index >= len(app.timeline):
                    print(f"❌ Invalid event index: {event_index}")
                    return False
                
                # Update the event
                event = app.timeline[event_index]
                if event_type is not None:
                    event.event_type = event_type
                if event_date is not None:
                    event.date = event_date
                if notes is not None:
                    event.notes = notes
                
                app.updated_at = datetime.now().isoformat()

                applications[i] = app.to_dict()
                self._write_json(self.applications_file, applications)

                print(f"✅ Updated timeline event at index {event_index}")
                return True

        print(f"❌ Application not found: {app_id}")
        return False

    def delete_timeline_event(self, app_id: str, event_index: int) -> bool:
        """
        Delete a timeline event from an application.

        Args:
            app_id: Application ID
            event_index: Index of the event in the timeline

        Returns:
            True if successful
        """
        applications = self._read_json(self.applications_file)

        for i, app_dict in enumerate(applications):
            if app_dict['id'] == app_id:
                app = Application.from_dict(app_dict)
                
                # Check if event_index is valid
                if event_index < 0 or event_index >= len(app.timeline):
                    print(f"❌ Invalid event index: {event_index}")
                    return False
                
                # Don't allow deleting the first event (initial application)
                if event_index == 0:
                    print(f"❌ Cannot delete the initial application event")
                    return False
                
                # Delete the event
                del app.timeline[event_index]
                app.updated_at = datetime.now().isoformat()

                applications[i] = app.to_dict()
                self._write_json(self.applications_file, applications)

                print(f"✅ Deleted timeline event at index {event_index}")
                return True

        print(f"❌ Application not found: {app_id}")
        return False

    # ==================== STATISTICS ====================

    def get_stats(self) -> Dict:
        """
        Get application statistics.

        Returns:
            Dictionary with various stats
        """
        applications = self.list_applications()

        total = len(applications)
        if total == 0:
            return {
                "total": 0,
                "active": 0,
                "by_status": {},
                "response_rate": 0,
                "avg_days_to_response": 0
            }

        # Count by status
        by_status = {}
        active = 0
        responded = 0
        days_to_response = []

        for app in applications:
            status = app.status
            by_status[status] = by_status.get(status, 0) + 1

            if app.is_active():
                active += 1

            if status != "applied":
                responded += 1

                # Calculate days to first response
                if len(app.timeline) > 1:
                    try:
                        applied = datetime.strptime(app.applied_date, "%Y-%m-%d")
                        first_response = datetime.strptime(app.timeline[1].date, "%Y-%m-%d")
                        days = (first_response - applied).days
                        days_to_response.append(days)
                    except:
                        pass

        response_rate = (responded / total * 100) if total > 0 else 0
        avg_days = sum(days_to_response) / len(days_to_response) if days_to_response else 0

        return {
            "total": total,
            "active": active,
            "by_status": by_status,
            "response_rate": round(response_rate, 1),
            "avg_days_to_response": round(avg_days, 1),
            "top_companies": self._get_top_companies(applications)
        }

    def _get_top_companies(self, applications: List[Application], limit: int = 5) -> List[Dict]:
        """Get companies with most applications"""
        company_counts = {}
        for app in applications:
            company_counts[app.company] = company_counts.get(app.company, 0) + 1

        sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"company": c, "count": n} for c, n in sorted_companies[:limit]]

    # ==================== SEARCH ====================

    def search_applications(self, query: str) -> List[Application]:
        """
        Search applications by company, role, or notes.

        Args:
            query: Search query

        Returns:
            List of matching applications
        """
        applications = self.list_applications()
        query_lower = query.lower()

        results = []
        for app in applications:
            if (query_lower in app.company.lower() or
                query_lower in app.role.lower() or
                (app.notes and query_lower in app.notes.lower()) or
                (app.location and query_lower in app.location.lower())):
                results.append(app)

        return results

    # ==================== QUICK NOTES CRUD ====================

    def add_quick_note(self, label: str, content: str, note_type: str = "text") -> str:
        """
        Add a new quick note.

        Args:
            label: Label/title for the note
            content: Content of the note (URL, text, etc.)
            note_type: Type of note (text, url, code, etc.)

        Returns:
            Note ID
        """
        # Generate ID
        note_id = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        note = {
            'id': note_id,
            'label': label,
            'content': content,
            'type': note_type,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Add to vector store
        try:
            from storage.vector_sync import sync_quick_note_to_vector_store
            sync_quick_note_to_vector_store(note, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add quick note to vector store: {e}")
            raise

        return note_id

    def get_quick_notes(self) -> List[Dict]:
        """
        Get all quick notes.

        Returns:
            List of quick notes
        """
        return self.quick_notes_store.list_records(
            record_type='quick_note',
            limit=1000
        )

    def get_quick_note(self, note_id: str) -> Optional[Dict]:
        """
        Get a specific quick note.

        Args:
            note_id: Note ID

        Returns:
            Note dict or None
        """
        return self.quick_notes_store.get_by_record_id('quick_note', note_id)

    def update_quick_note(self, note_id: str, label: str = None, content: str = None, note_type: str = None) -> bool:
        """
        Update a quick note.

        Args:
            note_id: Note ID
            label: New label (optional)
            content: New content (optional)
            note_type: New type (optional)

        Returns:
            True if updated, False if not found
        """
        # Get existing note
        note = self.quick_notes_store.get_by_record_id('quick_note', note_id)
        if not note:
            return False
        
        # Update fields
        if label is not None:
            note['label'] = label
        if content is not None:
            note['content'] = content
        if note_type is not None:
            note['type'] = note_type
        note['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update in vector store
        try:
            from storage.vector_sync import sync_quick_note_to_vector_store
            sync_quick_note_to_vector_store(note, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update quick note in vector store: {e}")
            return False

        return True

    def delete_quick_note(self, note_id: str) -> bool:
        """
        Delete a quick note.

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        # Check if exists
        existing = self.quick_notes_store.get_by_record_id('quick_note', note_id)
        if not existing:
            return False
        
        # Delete from vector store
        try:
            from storage.vector_sync import delete_from_vector_store
            success = delete_from_vector_store('quick_note', note_id, self.user_id)
            return success
        except Exception as e:
            print(f"Warning: Could not delete quick note from vector store: {e}")
            return False

    # ==================== COMPANIES ====================

    def add_company(self, company_data: Dict) -> str:
        """
        Add a new company.

        Args:
            company_data: Company dictionary (from Company.to_dict())

        Returns:
            Company ID
        """
        # Add to vector store (which stores full structured data)
        try:
            from storage.vector_sync import sync_company_to_vector_store
            sync_company_to_vector_store(company_data, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add company to vector store: {e}")
            raise
        
        return company_data['id']

    def get_companies(self) -> List[Dict]:
        """
        Get all companies.

        Returns:
            List of company dictionaries
        """
        return self.companies_store.list_records(
            record_type='company',
            limit=1000
        )

    def get_company(self, company_id: str) -> Optional[Dict]:
        """
        Get a specific company by ID.

        Args:
            company_id: Company ID

        Returns:
            Company dict or None
        """
        return self.companies_store.get_by_record_id('company', company_id)

    def get_company_by_name(self, name: str) -> Optional[Dict]:
        """
        Get a company by name (case-insensitive).

        Args:
            name: Company name

        Returns:
            Company dict or None
        """
        companies = self.companies_store.list_records(
            record_type='company',
            filters={'name': name},
            limit=100
        )
        
        # Case-insensitive match
        name_lower = name.lower()
        for company in companies:
            if company.get('name', '').lower() == name_lower:
                return company
        return None

    def update_company(self, company_data: Dict) -> bool:
        """
        Update a company.

        Args:
            company_data: Updated company dictionary

        Returns:
            True if updated, False if not found
        """
        # Check if exists
        existing = self.companies_store.get_by_record_id('company', company_data['id'])
        if not existing:
            return False
        
        company_data['updated_at'] = datetime.now().isoformat()
        
        # Update in vector store
        try:
            from storage.vector_sync import sync_company_to_vector_store
            sync_company_to_vector_store(company_data, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update company in vector store: {e}")
            return False
        
        return True

    def delete_company(self, company_id: str) -> bool:
        """
        Delete a company.

        Args:
            company_id: Company ID

        Returns:
            True if deleted, False if not found
        """
        # Check if exists
        existing = self.companies_store.get_by_record_id('company', company_id)
        if not existing:
            return False
        
        # Delete from vector store
        try:
            from storage.vector_sync import delete_from_vector_store
            success = delete_from_vector_store('company', company_id, self.user_id)
            return success
        except Exception as e:
            print(f"Warning: Could not delete company from vector store: {e}")
            return False

    def search_companies(self, query: str) -> List[Dict]:
        """
        Search companies by name, industry, or notes.

        Args:
            query: Search query

        Returns:
            List of matching companies
        """
        companies = self._read_json(self.companies_file)
        query_lower = query.lower()

        results = []
        for company in companies:
            if (query_lower in company['name'].lower() or
                query_lower in company.get('industry', '').lower() or
                query_lower in company.get('notes', '').lower() or
                query_lower in company.get('description', '').lower()):
                results.append(company)

        return results
