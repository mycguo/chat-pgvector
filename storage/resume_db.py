"""
Resume Database

JSON-based storage for resumes and versions with file management.
"""

import os
import json
import shutil
from typing import List, Optional, Dict
from datetime import datetime

from models.resume import Resume, ResumeVersion
from storage.user_utils import get_user_data_dir
from storage.encryption import encrypt_data, decrypt_data, is_encryption_enabled


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
        self.resumes_file = os.path.join(data_dir, "resumes.json")
        self.versions_file = os.path.join(data_dir, "versions.json")
        self.files_dir = os.path.join(data_dir, "files")

        # Create directory and initialize files
        self._initialize()

    def _initialize(self):
        """Create data directory and initialize JSON files"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)

        for file_path in [self.resumes_file, self.versions_file]:
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
        resumes = self._read_json(self.resumes_file)

        # Store file if provided
        if file_bytes and resume.original_filename:
            file_path = self._store_file(resume.id, resume.original_filename, file_bytes)
            resume.file_path = file_path

        resumes.append(resume.to_dict())
        self._write_json(self.resumes_file, resumes)
        return resume.id

    def get_resume(self, resume_id: str) -> Optional[Resume]:
        """Get resume by ID"""
        resumes = self._read_json(self.resumes_file)
        for r in resumes:
            if r['id'] == resume_id:
                return Resume.from_dict(r)
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
        resumes = self._read_json(self.resumes_file)
        result = []

        for r_data in resumes:
            r = Resume.from_dict(r_data)

            # Apply filters
            if is_master is not None and r.is_master != is_master:
                continue
            if is_active is not None and r.is_active != is_active:
                continue
            if tailored_for_company and r.tailored_for_company != tailored_for_company:
                continue

            result.append(r)

        return result

    def update_resume(self, resume: Resume):
        """Update resume"""
        resumes = self._read_json(self.resumes_file)

        for i, r in enumerate(resumes):
            if r['id'] == resume.id:
                resume.updated_at = datetime.now().isoformat()
                resumes[i] = resume.to_dict()
                self._write_json(self.resumes_file, resumes)
                return True

        return False

    def delete_resume(self, resume_id: str) -> bool:
        """Delete resume and associated files"""
        resumes = self._read_json(self.resumes_file)
        resume = self.get_resume(resume_id)

        if resume and resume.file_path:
            # Delete associated file
            try:
                if os.path.exists(resume.file_path):
                    os.remove(resume.file_path)
            except Exception as e:
                print(f"Error deleting file: {e}")

        # Remove from database
        filtered = [r for r in resumes if r['id'] != resume_id]

        if len(filtered) < len(resumes):
            self._write_json(self.resumes_file, filtered)
            return True
        return False

    def set_active_resume(self, resume_id: str):
        """Set a resume as active (deactivate others)"""
        resumes = self._read_json(self.resumes_file)

        for r in resumes:
            r['is_active'] = (r['id'] == resume_id)

        self._write_json(self.resumes_file, resumes)

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
        versions = self._read_json(self.versions_file)
        versions.append(version.to_dict())
        self._write_json(self.versions_file, versions)
        return version.id

    def get_versions(self, resume_id: str) -> List[ResumeVersion]:
        """Get all versions for a resume"""
        versions = self._read_json(self.versions_file)
        result = []

        for v_data in versions:
            v = ResumeVersion.from_dict(v_data)
            if v.resume_id == resume_id:
                result.append(v)

        # Sort by created_at (most recent first)
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result

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
        resumes = self._read_json(self.resumes_file)

        master_resumes = [r for r in resumes if r.get('is_master', False)]
        tailored_resumes = [r for r in resumes if not r.get('is_master', False)]
        active_resumes = [r for r in resumes if r.get('is_active', True)]

        # Calculate average success rate
        total_success = sum(r.get('success_rate', 0) for r in resumes)
        avg_success = (total_success / len(resumes)) if len(resumes) > 0 else 0

        # Most used resume
        most_used = None
        max_apps = 0
        for r in resumes:
            if r.get('applications_count', 0) > max_apps:
                max_apps = r.get('applications_count', 0)
                most_used = r.get('name', 'Unknown')

        return {
            'total_resumes': len(resumes),
            'master_resumes': len(master_resumes),
            'tailored_resumes': len(tailored_resumes),
            'active_resumes': len(active_resumes),
            'average_success_rate': avg_success,
            'most_used_resume': most_used,
            'total_applications': sum(r.get('applications_count', 0) for r in resumes)
        }
