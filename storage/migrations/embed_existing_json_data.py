"""
Migration script to embed existing JSON data into the vector store.

This script reads all existing JSON data (applications, resumes, interview questions, etc.)
and embeds them into the vector store for semantic search.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.json_db import JobSearchDB
from storage.interview_db import InterviewDB
from storage.resume_db import ResumeDB
from storage.vector_sync import (
    sync_application_to_vector_store,
    sync_interview_question_to_vector_store,
    sync_resume_to_vector_store,
    sync_company_to_vector_store,
)
from storage.user_utils import get_user_data_dir


def embed_all_json_data(user_id: str = None, dry_run: bool = False, return_stats: bool = False):
    """
    Embed all existing JSON data into the vector store.
    
    Args:
        user_id: Optional user ID (if None, will try to detect)
        dry_run: If True, only print what would be embedded without actually doing it
        return_stats: If True, return stats dictionary instead of printing summary
    
    Returns:
        Dictionary with stats if return_stats=True, None otherwise
    """
    if user_id is None:
        try:
            from storage.user_utils import get_user_id
            user_id = get_user_id()
        except:
            user_id = "default_user"
    
    print(f"Embedding JSON data for user: {user_id}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("-" * 60)
    
    stats = {
        'applications': 0,
        'questions': 0,
        'resumes': 0,
        'companies': 0,
        'errors': 0,
    }
    
    # 1. Applications
    print("\n📝 Processing Applications...")
    try:
        db = JobSearchDB(user_id=user_id)
        applications = db.list_applications()
        
        for app in applications:
            if not dry_run:
                try:
                    sync_application_to_vector_store(app, user_id)
                    stats['applications'] += 1
                except Exception as e:
                    print(f"  ❌ Error embedding application {app.id}: {e}")
                    stats['errors'] += 1
            else:
                print(f"  Would embed: {app.company} - {app.role} ({app.id})")
                stats['applications'] += 1
        
        print(f"  ✅ Processed {stats['applications']} applications")
    except Exception as e:
        print(f"  ❌ Error processing applications: {e}")
        stats['errors'] += 1
    
    # 2. Interview Questions
    print("\n❓ Processing Interview Questions...")
    try:
        db = InterviewDB(user_id=user_id)
        questions = db.list_questions()
        
        for question in questions:
            if not dry_run:
                try:
                    sync_interview_question_to_vector_store(question, user_id)
                    stats['questions'] += 1
                except Exception as e:
                    print(f"  ❌ Error embedding question {question.id}: {e}")
                    stats['errors'] += 1
            else:
                print(f"  Would embed: {question.question[:50]}... ({question.id})")
                stats['questions'] += 1
        
        print(f"  ✅ Processed {stats['questions']} questions")
    except Exception as e:
        print(f"  ❌ Error processing questions: {e}")
        stats['errors'] += 1
    
    # 3. Resumes
    print("\n📄 Processing Resumes...")
    try:
        db = ResumeDB(user_id=user_id)
        resumes = db.list_resumes()
        
        for resume in resumes:
            if not dry_run:
                try:
                    sync_resume_to_vector_store(resume, user_id)
                    stats['resumes'] += 1
                except Exception as e:
                    print(f"  ❌ Error embedding resume {resume.id}: {e}")
                    stats['errors'] += 1
            else:
                print(f"  Would embed: {resume.name} ({resume.id})")
                stats['resumes'] += 1
        
        print(f"  ✅ Processed {stats['resumes']} resumes")
    except Exception as e:
        print(f"  ❌ Error processing resumes: {e}")
        stats['errors'] += 1
    
    # 4. Companies
    print("\n🏢 Processing Companies...")
    try:
        db = JobSearchDB(user_id=user_id)
        companies = db.get_companies()
        
        for company in companies:
            if not dry_run:
                try:
                    sync_company_to_vector_store(company, user_id)
                    stats['companies'] += 1
                except Exception as e:
                    print(f"  ❌ Error embedding company {company.get('id')}: {e}")
                    stats['errors'] += 1
            else:
                print(f"  Would embed: {company.get('name', 'Unknown')} ({company.get('id')})")
                stats['companies'] += 1
        
        print(f"  ✅ Processed {stats['companies']} companies")
    except Exception as e:
        print(f"  ❌ Error processing companies: {e}")
        stats['errors'] += 1
    
    # Summary
    if not return_stats:
        print("\n" + "=" * 60)
        print("📊 Summary:")
        print(f"  Applications: {stats['applications']}")
        print(f"  Questions: {stats['questions']}")
        print(f"  Resumes: {stats['resumes']}")
        print(f"  Companies: {stats['companies']}")
        print(f"  Errors: {stats['errors']}")
        print("=" * 60)
        
        if dry_run:
            print("\n⚠️  This was a DRY RUN. No data was actually embedded.")
            print("   Run without --dry-run to actually embed the data.")
        else:
            print("\n✅ Embedding complete!")
    
    if return_stats:
        return stats


def embed_all_users(dry_run: bool = False):
    """
    Embed JSON data for all users found in user_data directory.
    
    Args:
        dry_run: If True, only print what would be embedded
    """
    import os
    user_data_dir = Path(__file__).parent.parent.parent / "user_data"
    
    if not user_data_dir.exists():
        print(f"❌ User data directory not found: {user_data_dir}")
        return
    
    # Find all user directories
    user_dirs = [d.name for d in user_data_dir.iterdir() 
                 if d.is_dir() and not d.name.startswith('.')]
    
    if not user_dirs:
        print("❌ No user directories found")
        return
    
    print(f"Found {len(user_dirs)} user(s): {', '.join(user_dirs)}")
    print("=" * 60)
    
    total_stats = {
        'applications': 0,
        'questions': 0,
        'resumes': 0,
        'companies': 0,
        'errors': 0,
    }
    
    for user_id in user_dirs:
        print(f"\n👤 Processing user: {user_id}")
        print("-" * 60)
        stats = embed_all_json_data(user_id=user_id, dry_run=dry_run, return_stats=True)
        
        # Accumulate stats
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 TOTAL SUMMARY (All Users):")
    print(f"  Applications: {total_stats['applications']}")
    print(f"  Questions: {total_stats['questions']}")
    print(f"  Resumes: {total_stats['resumes']}")
    print(f"  Companies: {total_stats['companies']}")
    print(f"  Errors: {total_stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Embed existing JSON data into vector store")
    parser.add_argument("--user-id", help="User ID (if not provided, will try to detect or process all users)")
    parser.add_argument("--all-users", action="store_true", help="Process all users found in user_data directory")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (don't actually embed)")
    
    args = parser.parse_args()
    
    if args.all_users:
        embed_all_users(dry_run=args.dry_run)
    else:
        embed_all_json_data(user_id=args.user_id, dry_run=args.dry_run)

