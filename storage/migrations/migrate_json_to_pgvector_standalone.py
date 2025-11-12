#!/usr/bin/env python3
"""
Standalone migration script to migrate JSON data to pgvector.
Reads directly from JSON files without importing database classes.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import only what we need for reading JSON (with encryption support)
from storage.encryption import decrypt_data, is_encryption_enabled


def read_json_file(filepath: str, user_id: str = None) -> List[Dict]:
    """Read JSON file with optional decryption."""
    encryption_enabled = is_encryption_enabled()
    
    try:
        if encryption_enabled:
            # Read encrypted file as binary
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
                if encrypted_data:
                    decrypted_data = decrypt_data(encrypted_data, user_id)
                    return json.loads(decrypted_data.decode('utf-8'))
                else:
                    return []
        else:
            # Read plain JSON file
            with open(filepath, 'r') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  ⚠️  Error reading {filepath}: {e}")
        return []
    except Exception as e:
        # If decryption fails, try reading as plain JSON (for migration)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            print(f"  ⚠️  Error reading {filepath}: {e}")
            return []


def migrate_user_data(user_id: str, dry_run: bool = False):
    """Migrate all JSON data for a user to pgvector."""
    print(f"\n{'='*60}")
    print(f"Migrating data for user: {user_id}")
    print(f"{'='*60}\n")
    
    stats = {
        'applications': 0,
        'companies': 0,
        'contacts': 0,
        'quick_notes': 0,
        'questions': 0,
        'concepts': 0,
        'practice_sessions': 0,
        'resumes': 0,
        'resume_versions': 0,
    }
    
    base_dir = Path(__file__).parent.parent.parent
    user_data_dir = base_dir / "user_data" / user_id
    
    # Import sync functions (they handle their own imports)
    try:
        from storage.vector_sync import (
            sync_application_to_vector_store,
            sync_company_to_vector_store,
            sync_contact_to_vector_store,
            sync_quick_note_to_vector_store,
            sync_interview_question_to_vector_store,
            sync_concept_to_vector_store,
            sync_practice_session_to_vector_store,
            sync_resume_to_vector_store,
            sync_resume_version_to_vector_store,
        )
        from models.application import Application
        from models.interview_prep import InterviewQuestion, TechnicalConcept, PracticeSession
        from models.resume import Resume, ResumeVersion
    except ImportError as e:
        print(f"❌ Error importing modules: {e}")
        print("   Make sure you're in the virtual environment with all dependencies installed")
        return stats
    
    # Migrate JobSearchDB data
    job_search_dir = user_data_dir / "job_search_data"
    
    # Applications
    print("Migrating applications...")
    applications_file = job_search_dir / "applications.json"
    if applications_file.exists():
        try:
            app_dicts = read_json_file(str(applications_file), user_id)
            if app_dicts and len(app_dicts) > 0:
                print(f"  📄 Found {len(app_dicts)} applications in JSON file")
                for app_dict in app_dicts:
                    try:
                        app = Application.from_dict(app_dict)
                        if not dry_run:
                            sync_application_to_vector_store(app, user_id)
                        stats['applications'] += 1
                    except Exception as e:
                        print(f"  ⚠️  Error processing application {app_dict.get('id', 'unknown')}: {e}")
            else:
                print(f"  ℹ️  No applications found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read applications: {e}")
    else:
        print(f"  ℹ️  Applications file not found: {applications_file}")
    print(f"  ✅ Migrated {stats['applications']} applications")
    
    # Companies
    print("Migrating companies...")
    companies_file = job_search_dir / "companies.json"
    if companies_file.exists():
        try:
            company_dicts = read_json_file(str(companies_file), user_id)
            if company_dicts and len(company_dicts) > 0:
                print(f"  📄 Found {len(company_dicts)} companies in JSON file")
                for company in company_dicts:
                    if not dry_run:
                        sync_company_to_vector_store(company, user_id)
                    stats['companies'] += 1
            else:
                print(f"  ℹ️  No companies found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read companies: {e}")
    else:
        print(f"  ℹ️  Companies file not found: {companies_file}")
    print(f"  ✅ Migrated {stats['companies']} companies")
    
    # Contacts
    print("Migrating contacts...")
    contacts_file = job_search_dir / "contacts.json"
    if contacts_file.exists():
        try:
            contacts = read_json_file(str(contacts_file), user_id)
            if contacts and len(contacts) > 0:
                print(f"  📄 Found {len(contacts)} contacts in JSON file")
                for contact in contacts:
                    if not dry_run:
                        sync_contact_to_vector_store(contact, user_id)
                    stats['contacts'] += 1
            else:
                print(f"  ℹ️  No contacts found in file")
        except Exception as e:
            print(f"  ⚠️  Could not read contacts: {e}")
    else:
        print(f"  ℹ️  Contacts file not found: {contacts_file}")
    print(f"  ✅ Migrated {stats['contacts']} contacts")
    
    # Quick Notes
    print("Migrating quick notes...")
    quick_notes_file = job_search_dir / "quick_notes.json"
    if quick_notes_file.exists():
        try:
            notes = read_json_file(str(quick_notes_file), user_id)
            if notes and len(notes) > 0:
                print(f"  📄 Found {len(notes)} quick notes in JSON file")
                for note in notes:
                    if not dry_run:
                        sync_quick_note_to_vector_store(note, user_id)
                    stats['quick_notes'] += 1
            else:
                print(f"  ℹ️  No quick notes found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read quick notes: {e}")
    else:
        print(f"  ℹ️  Quick notes file not found: {quick_notes_file}")
    print(f"  ✅ Migrated {stats['quick_notes']} quick notes")
    
    # Migrate InterviewDB data
    interview_dir = user_data_dir / "interview_data"
    
    # Questions
    print("Migrating interview questions...")
    questions_file = interview_dir / "questions.json"
    if questions_file.exists():
        try:
            question_dicts = read_json_file(str(questions_file), user_id)
            if question_dicts and len(question_dicts) > 0:
                print(f"  📄 Found {len(question_dicts)} questions in JSON file")
                for q_dict in question_dicts:
                    try:
                        question = InterviewQuestion.from_dict(q_dict)
                        if not dry_run:
                            sync_interview_question_to_vector_store(question, user_id)
                        stats['questions'] += 1
                    except Exception as e:
                        print(f"  ⚠️  Error processing question {q_dict.get('id', 'unknown')}: {e}")
            else:
                print(f"  ℹ️  No questions found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read questions: {e}")
    else:
        print(f"  ℹ️  Questions file not found: {questions_file}")
    print(f"  ✅ Migrated {stats['questions']} questions")
    
    # Concepts
    print("Migrating technical concepts...")
    concepts_file = interview_dir / "concepts.json"
    if concepts_file.exists():
        try:
            concept_dicts = read_json_file(str(concepts_file), user_id)
            if concept_dicts and len(concept_dicts) > 0:
                print(f"  📄 Found {len(concept_dicts)} concepts in JSON file")
                for c_dict in concept_dicts:
                    try:
                        concept = TechnicalConcept.from_dict(c_dict)
                        if not dry_run:
                            sync_concept_to_vector_store(concept, user_id)
                        stats['concepts'] += 1
                    except Exception as e:
                        print(f"  ⚠️  Error processing concept {c_dict.get('id', 'unknown')}: {e}")
            else:
                print(f"  ℹ️  No concepts found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read concepts: {e}")
    else:
        print(f"  ℹ️  Concepts file not found: {concepts_file}")
    print(f"  ✅ Migrated {stats['concepts']} concepts")
    
    # Practice Sessions
    print("Migrating practice sessions...")
    practice_file = interview_dir / "practice.json"
    if practice_file.exists():
        try:
            session_dicts = read_json_file(str(practice_file), user_id)
            if session_dicts and len(session_dicts) > 0:
                print(f"  📄 Found {len(session_dicts)} practice sessions in JSON file")
                for s_dict in session_dicts:
                    try:
                        session = PracticeSession.from_dict(s_dict)
                        if not dry_run:
                            sync_practice_session_to_vector_store(session, user_id)
                        stats['practice_sessions'] += 1
                    except Exception as e:
                        print(f"  ⚠️  Error processing session {s_dict.get('id', 'unknown')}: {e}")
            else:
                print(f"  ℹ️  No practice sessions found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read practice sessions: {e}")
    else:
        print(f"  ℹ️  Practice sessions file not found: {practice_file}")
    print(f"  ✅ Migrated {stats['practice_sessions']} practice sessions")
    
    # Migrate ResumeDB data
    resume_dir = user_data_dir / "resume_data"
    
    # Resumes
    print("Migrating resumes...")
    resumes_file = resume_dir / "resumes.json"
    if resumes_file.exists():
        try:
            resume_dicts = read_json_file(str(resumes_file), user_id)
            if resume_dicts and len(resume_dicts) > 0:
                print(f"  📄 Found {len(resume_dicts)} resumes in JSON file")
                for r_dict in resume_dicts:
                    try:
                        resume = Resume.from_dict(r_dict)
                        if not dry_run:
                            sync_resume_to_vector_store(resume, user_id)
                        stats['resumes'] += 1
                    except Exception as e:
                        print(f"  ⚠️  Error processing resume {r_dict.get('id', 'unknown')}: {e}")
            else:
                print(f"  ℹ️  No resumes found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read resumes: {e}")
    else:
        print(f"  ℹ️  Resumes file not found: {resumes_file}")
    print(f"  ✅ Migrated {stats['resumes']} resumes")
    
    # Resume Versions
    print("Migrating resume versions...")
    versions_file = resume_dir / "versions.json"
    if versions_file.exists():
        try:
            version_dicts = read_json_file(str(versions_file), user_id)
            if version_dicts and len(version_dicts) > 0:
                print(f"  📄 Found {len(version_dicts)} resume versions in JSON file")
                for v_dict in version_dicts:
                    try:
                        version = ResumeVersion.from_dict(v_dict)
                        if not dry_run:
                            sync_resume_version_to_vector_store(version, user_id)
                        stats['resume_versions'] += 1
                    except Exception as e:
                        print(f"  ⚠️  Error processing version {v_dict.get('id', 'unknown')}: {e}")
            else:
                print(f"  ℹ️  No resume versions found in JSON file")
        except Exception as e:
            print(f"  ⚠️  Could not read resume versions: {e}")
    else:
        print(f"  ℹ️  Resume versions file not found: {versions_file}")
    print(f"  ✅ Migrated {stats['resume_versions']} resume versions")
    
    # Print summary
    print(f"\n{'='*60}")
    print("Migration Summary:")
    print(f"{'='*60}")
    total = sum(stats.values())
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    print(f"\n  Total records: {total}")
    print(f"{'='*60}\n")
    
    return stats


def migrate_all_users(dry_run: bool = False):
    """Migrate data for all users found in user_data directory."""
    base_dir = Path(__file__).parent.parent.parent
    user_data_dir = base_dir / "user_data"
    
    if not user_data_dir.exists():
        print(f"User data directory not found: {user_data_dir}")
        return
    
    user_dirs = [d for d in user_data_dir.iterdir() if d.is_dir()]
    
    if not user_dirs:
        print("No user directories found")
        return
    
    print(f"Found {len(user_dirs)} user directories")
    
    all_stats = {}
    for user_dir in user_dirs:
        user_id = user_dir.name
        stats = migrate_user_data(user_id, dry_run=dry_run)
        all_stats[user_id] = stats
    
    # Print overall summary
    print(f"\n{'='*60}")
    print("Overall Migration Summary:")
    print(f"{'='*60}")
    total_all = sum(sum(s.values()) for s in all_stats.values())
    print(f"Total records migrated: {total_all}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate all JSON data to pgvector")
    parser.add_argument("--user-id", help="Migrate data for specific user only")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't actually migrate)")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be migrated\n")
    
    if args.user_id:
        migrate_user_data(args.user_id, dry_run=args.dry_run)
    else:
        migrate_all_users(dry_run=args.dry_run)

