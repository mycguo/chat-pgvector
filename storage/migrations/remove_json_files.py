#!/usr/bin/env python3
"""
Remove JSON files that have been migrated to pgvector.

KEEPS:
- profile.json (user profile data)
- interview_data/companies.json (interview research companies, different from job search)

REMOVES:
- applications.json
- companies.json (job search)
- contacts.json
- quick_notes.json
- questions.json
- concepts.json
- practice.json
- resumes.json
- versions.json (if not used)
"""

import os
import sys
from pathlib import Path

def remove_json_files(user_id: str = None, dry_run: bool = True):
    """Remove migrated JSON files for a user."""
    base_dir = Path(__file__).parent.parent.parent
    user_data_dir = base_dir / "user_data"
    
    if user_id:
        user_dirs = [user_data_dir / user_id]
    else:
        user_dirs = [d for d in user_data_dir.iterdir() if d.is_dir()]
    
    files_to_remove = [
        "job_search_data/applications.json",
        "job_search_data/companies.json",
        "job_search_data/contacts.json",
        "job_search_data/quick_notes.json",
        "interview_data/questions.json",
        "interview_data/concepts.json",
        "interview_data/practice.json",
        "resume_data/resumes.json",
        "resume_data/versions.json",
    ]
    
    files_kept = [
        "job_search_data/profile.json",
        "interview_data/companies.json",  # Interview research companies
    ]
    
    total_removed = 0
    total_size = 0
    
    for user_dir in user_dirs:
        if not user_dir.exists():
            continue
        
        user_id = user_dir.name
        print(f"\n{'='*60}")
        print(f"Processing user: {user_id}")
        print(f"{'='*60}")
        
        for file_rel_path in files_to_remove:
            file_path = user_dir / file_rel_path
            if file_path.exists():
                size = file_path.stat().st_size
                if dry_run:
                    print(f"  🔍 Would remove: {file_rel_path} ({size:,} bytes)")
                else:
                    try:
                        file_path.unlink()
                        print(f"  ✅ Removed: {file_rel_path} ({size:,} bytes)")
                        total_removed += 1
                        total_size += size
                    except Exception as e:
                        print(f"  ❌ Error removing {file_rel_path}: {e}")
            else:
                if dry_run:
                    print(f"  ℹ️  Not found: {file_rel_path}")
        
        # Verify kept files exist
        print(f"\n  Files kept:")
        for file_rel_path in files_kept:
            file_path = user_dir / file_rel_path
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"    ✅ {file_rel_path} ({size:,} bytes)")
            else:
                print(f"    ℹ️  {file_rel_path} (not found)")
    
    print(f"\n{'='*60}")
    if dry_run:
        print("DRY RUN - No files were actually removed")
        print("Run without --dry-run to actually remove files")
    else:
        print(f"Summary:")
        print(f"  Files removed: {total_removed}")
        print(f"  Total size freed: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Remove JSON files migrated to pgvector")
    parser.add_argument("--user-id", help="Remove files for specific user only")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run (don't actually remove)")
    parser.add_argument("--force", action="store_true", help="Actually remove files (overrides --dry-run)")
    
    args = parser.parse_args()
    
    dry_run = args.dry_run and not args.force
    
    if not dry_run and not args.force:
        try:
            response = input("⚠️  This will permanently delete JSON files. Are you sure? (yes/no): ")
            if response.lower() != "yes":
                print("Cancelled.")
                sys.exit(0)
        except EOFError:
            # Non-interactive mode, require --force flag
            print("⚠️  Non-interactive mode detected. Use --force flag to proceed.")
            sys.exit(1)
    
    remove_json_files(user_id=args.user_id, dry_run=dry_run)

