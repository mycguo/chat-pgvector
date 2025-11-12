"""
Resume Database

Uses PostgreSQL + pgvector as the single source of truth.
Maintains backward compatibility with existing API.
"""

import os
import json
import shutil
from typing import List, Optional, Dict
from datetime import datetime

from models.resume import Resume, ResumeVersion
from storage.user_utils import get_user_data_dir
from storage.encryption import encrypt_data, decrypt_data, is_encryption_enabled
from storage.pg_vector_store import PgVectorStore


class ResumeDB:
    """Database for resume management"""

    def __init__(self, data_dir: str = None, user_id: str = None):
        """
        Initialize resume database.

        Args:
            data_dir: Directory for storing JSON files and resume files (if None, uses user-specific directory)
            user_id: Optional user ID (if None, will try to get from Streamlit)
        """
        if data_dir is None:
            data_dir = get_user_data_dir("resume_data", user_id)
        
        self.data_dir = data_dir
        self.user_id = user_id
        self._encryption_enabled = is_encryption_enabled()
        
        # Initialize pgvector store for resumes
        self.resumes_store = PgVectorStore(collection_name="resumes", user_id=user_id)
        
        # Resume files directory (PDF files are still stored on disk)
        self.files_dir = os.path.join(data_dir, "files")

        # Create directory for resume files
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)

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

    # ========== Resume Operations ==========

    def add_resume(self, resume: Resume, file_bytes: Optional[bytes] = None) -> str:
        """
        Add resume to database.

        Args:
            resume: Resume instance
            file_bytes: Optional file bytes to store

        Returns:
            Resume ID
        """
        # Store file if provided
        if file_bytes and resume.original_filename:
            file_path = self._store_file(resume.id, resume.original_filename, file_bytes)
            resume.file_path = file_path

        # Add to vector store (which stores full structured data)
        try:
            from storage.vector_sync import sync_resume_to_vector_store
            sync_resume_to_vector_store(resume, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add resume to vector store: {e}")
            raise
        
        return resume.id

    def get_resume(self, resume_id: str) -> Optional[Resume]:
        """Get resume by ID"""
        r_dict = self.resumes_store.get_by_record_id('resume', resume_id)
        if r_dict:
            return Resume.from_dict(r_dict)
        return None

    def list_resumes(
        self,
        is_master: Optional[bool] = None,
        is_active: Optional[bool] = None,
        tailored_for_company: Optional[str] = None
    ) -> List[Resume]:
        """
        List resumes with optional filters.

        Args:
            is_master: Filter by master status
            is_active: Filter by active status
            tailored_for_company: Filter by company

        Returns:
            List of Resume instances
        """
        # Build filters
        filters = {}
        if is_master is not None:
            filters['is_master'] = str(is_master).lower()  # Convert bool to string for JSONB
        if is_active is not None:
            filters['is_active'] = str(is_active).lower()
        if tailored_for_company:
            filters['tailored_for_company'] = tailored_for_company
        
        # Query from pgvector
        r_dicts = self.resumes_store.list_records(
            record_type='resume',
            filters=filters if filters else None,
            limit=1000
        )
        
        result = []
        for r_dict in r_dicts:
            r = Resume.from_dict(r_dict)
            
            # Apply boolean filters (since JSONB stores them as strings)
            if is_master is not None and r.is_master != is_master:
                continue
            if is_active is not None and r.is_active != is_active:
                continue
            
            result.append(r)

        return result

    def update_resume(self, resume: Resume):
        """Update resume"""
        # Check if exists
        existing = self.resumes_store.get_by_record_id('resume', resume.id)
        if not existing:
            return False
        
        resume.updated_at = datetime.now().isoformat()
        
        # Update in vector store
        try:
            from storage.vector_sync import sync_resume_to_vector_store
            sync_resume_to_vector_store(resume, self.user_id)
        except Exception as e:
            print(f"Warning: Could not update resume in vector store: {e}")
            return False
        
        return True

    def delete_resume(self, resume_id: str) -> bool:
        """Delete resume and associated files"""
        # Get resume to check for file
        resume = self.get_resume(resume_id)
        if not resume:
            return False

        if resume.file_path:
            # Delete associated file
            try:
                if os.path.exists(resume.file_path):
                    os.remove(resume.file_path)
            except Exception as e:
                print(f"Error deleting file: {e}")

        # Delete from vector store
        try:
            from storage.vector_sync import delete_from_vector_store
            success = delete_from_vector_store('resume', resume_id, self.user_id)
            return success
        except Exception as e:
            print(f"Warning: Could not delete resume from vector store: {e}")
            return False

    def set_active_resume(self, resume_id: str):
        """Set a resume as active (deactivate others)"""
        resumes = self.list_resumes()

        for r in resumes:
            if r.id == resume_id:
                r.is_active = True
                self.update_resume(r)
            elif r.is_active:
                r.is_active = False
                self.update_resume(r)

    def get_master_resumes(self) -> List[Resume]:
        """Get all master resumes"""
        return self.list_resumes(is_master=True)

    def get_tailored_resumes(self, parent_id: Optional[str] = None) -> List[Resume]:
        """Get all tailored resumes, optionally filtered by parent"""
        resumes = self.list_resumes(is_master=False)
        if parent_id:
            resumes = [r for r in resumes if r.parent_id == parent_id]
        return resumes

    # ========== Version Operations ==========

    def add_version(self, version: ResumeVersion) -> str:
        """Add resume version"""
        # Add to vector store
        try:
            from storage.vector_sync import sync_resume_version_to_vector_store
            sync_resume_version_to_vector_store(version, self.user_id)
        except Exception as e:
            print(f"Warning: Could not add resume version to vector store: {e}")
            raise
        return version.id

    def get_versions(self, resume_id: str) -> List[ResumeVersion]:
        """Get all versions for a resume"""
        # Query from pgvector
        v_dicts = self.resumes_store.list_records(
            record_type='resume_version',
            filters={'resume_id': resume_id},
            sort_by='created_at',
            reverse=True,
            limit=1000
        )
        
        return [ResumeVersion.from_dict(v_dict) for v_dict in v_dicts]

    # ========== File Operations ==========

    def _store_file(self, resume_id: str, filename: str, file_bytes: bytes) -> str:
        """
        Store resume file.

        Args:
            resume_id: Resume ID
            filename: Original filename
            file_bytes: File content

        Returns:
            Path to stored file
        """
        # Create filename with resume ID
        ext = os.path.splitext(filename)[1]
        new_filename = f"{resume_id}{ext}"
        file_path = os.path.join(self.files_dir, new_filename)

        # Write file
        with open(file_path, 'wb') as f:
            f.write(file_bytes)

        return file_path

    def get_file_bytes(self, resume_id: str) -> Optional[bytes]:
        """Get file bytes for a resume"""
        resume = self.get_resume(resume_id)
        if not resume or not resume.file_path:
            return None

        try:
            with open(resume.file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    # ========== Statistics ==========

    def get_stats(self) -> Dict:
        """Get resume statistics"""
        # Get data from pgvector
        resumes = self.list_resumes()

        master_resumes = [r for r in resumes if r.is_master]
        tailored_resumes = [r for r in resumes if not r.is_master]
        active_resumes = [r for r in resumes if r.is_active]

        # Calculate average success rate
        total_success = sum(r.success_rate for r in resumes)
        avg_success = (total_success / len(resumes)) if len(resumes) > 0 else 0

        # Most used resume
        most_used = None
        max_apps = 0
        for r in resumes:
            if r.applications_count > max_apps:
                max_apps = r.applications_count
                most_used = r.name

        return {
            'total_resumes': len(resumes),
            'master_resumes': len(master_resumes),
            'tailored_resumes': len(tailored_resumes),
            'active_resumes': len(active_resumes),
            'average_success_rate': avg_success,
            'most_used_resume': most_used,
            'total_applications': sum(r.applications_count for r in resumes)
        }
