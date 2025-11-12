#!/usr/bin/env python3
"""
Test script to verify JSON files can be read correctly.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.json_db import JobSearchDB
from storage.interview_db import InterviewDB
from storage.resume_db import ResumeDB

def test_json_reads(user_id: str):
    """Test reading JSON files directly."""
    print(f"\n{'='*60}")
    print(f"Testing JSON file reads for user: {user_id}")
    print(f"{'='*60}\n")
    
    # Test JobSearchDB
    job_db = JobSearchDB(user_id=user_id)
    applications_file = os.path.join(job_db.data_dir, "applications.json")
    if os.path.exists(applications_file):
        try:
            apps = job_db._read_json(applications_file)
            print(f"✅ Applications: Found {len(apps)} records in JSON file")
            if len(apps) > 0:
                print(f"   Sample: {apps[0].get('company', 'N/A')} - {apps[0].get('role', 'N/A')}")
        except Exception as e:
            print(f"❌ Applications: Error reading - {e}")
    else:
        print(f"ℹ️  Applications file not found: {applications_file}")
    
    companies_file = os.path.join(job_db.data_dir, "companies.json")
    if os.path.exists(companies_file):
        try:
            companies = job_db._read_json(companies_file)
            print(f"✅ Companies: Found {len(companies)} records in JSON file")
        except Exception as e:
            print(f"❌ Companies: Error reading - {e}")
    
    # Test InterviewDB
    interview_db = InterviewDB(user_id=user_id)
    questions_file = os.path.join(interview_db.data_dir, "questions.json")
    if os.path.exists(questions_file):
        try:
            questions = interview_db._read_json(questions_file)
            print(f"✅ Questions: Found {len(questions)} records in JSON file")
            if len(questions) > 0:
                print(f"   Sample: {questions[0].get('question', 'N/A')[:50]}...")
        except Exception as e:
            print(f"❌ Questions: Error reading - {e}")
    
    # Test ResumeDB
    resume_db = ResumeDB(user_id=user_id)
    resumes_file = os.path.join(resume_db.data_dir, "resumes.json")
    if os.path.exists(resumes_file):
        try:
            resumes = resume_db._read_json(resumes_file)
            print(f"✅ Resumes: Found {len(resumes)} records in JSON file")
        except Exception as e:
            print(f"❌ Resumes: Error reading - {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default="mycguo_gmail_com")
    args = parser.parse_args()
    test_json_reads(args.user_id)

