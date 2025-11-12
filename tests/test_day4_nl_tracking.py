"""
Tests for Day 4: Natural Language Job Tracking

Tests the enhanced remember feature for job search:
- Application intent detection
- Application detail parsing
- Interview intent detection
- Interview detail parsing
- Integration with JobSearchDB
"""

import sys
import os
from datetime import datetime
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, '.')

from app import (
    detect_application_intent,
    parse_application_details,
    detect_interview_intent,
    parse_interview_details,
    create_application_from_text,
    add_interview_to_application
)
from storage.json_db import JobSearchDB
from models.application import create_application


def test_application_intent_detection():
    """Test detection of job application intents"""
    print("\n=== Testing Application Intent Detection ===")

    # Positive cases
    test_cases = [
        "Applied to Google for ML Engineer",
        "I applied to Meta for Senior SWE today",
        "Just submitted application to Amazon for Data Scientist",
        "Applied at Apple for iOS Developer",
        "applying to Netflix for Backend Engineer",
    ]

    for test in test_cases:
        is_app, _ = detect_application_intent(test)
        print(f"✓ '{test}' -> detected: {is_app}")
        assert is_app, f"Failed to detect application in: {test}"

    # Negative cases
    negative_cases = [
        "What companies should I apply to?",
        "Remember that I like Python",
        "Interview with Google tomorrow",
    ]

    for test in negative_cases:
        is_app, _ = detect_application_intent(test)
        print(f"✓ '{test}' -> detected: {is_app} (should be False)")
        assert not is_app, f"False positive for: {test}"

    print("✅ All application intent detection tests passed!\n")


def test_interview_intent_detection():
    """Test detection of interview intents"""
    print("\n=== Testing Interview Intent Detection ===")

    # Positive cases
    test_cases = [
        "Interview with Google tomorrow at 2pm",
        "Phone screen with Meta on Nov 10",
        "Technical interview scheduled for Friday",
        "interviewing at Amazon next week",
        "Scheduled interview with recruiter",
    ]

    for test in test_cases:
        is_interview, _ = detect_interview_intent(test)
        print(f"✓ '{test}' -> detected: {is_interview}")
        assert is_interview, f"Failed to detect interview in: {test}"

    # Negative cases
    negative_cases = [
        "Applied to Google today",
        "What should I prepare for interviews?",
        "Remember to practice leetcode",
    ]

    for test in negative_cases:
        is_interview, _ = detect_interview_intent(test)
        print(f"✓ '{test}' -> detected: {is_interview} (should be False)")
        assert not is_interview, f"False positive for: {test}"

    print("✅ All interview intent detection tests passed!\n")


def test_application_parsing():
    """Test parsing of application details from natural language"""
    print("\n=== Testing Application Detail Parsing ===")

    test_cases = [
        {
            "input": "Applied to Google for ML Engineer",
            "expected": {
                "company": "Google",
                "role": "ML Engineer"
            }
        },
        {
            "input": "I applied to Meta for Senior Software Engineer at Menlo Park for $200k",
            "expected": {
                "company": "Meta",
                "role": "Senior Software Engineer"
            }
        },
        {
            "input": "Just submitted application to Amazon for Data Scientist in Seattle",
            "expected": {
                "company": "Amazon",
                "role": "Data Scientist"
            }
        }
    ]

    for test_case in test_cases:
        print(f"\nParsing: '{test_case['input']}'")
        details = parse_application_details(test_case['input'])

        if details:
            print(f"  Company: {details.get('company')}")
            print(f"  Role: {details.get('role')}")
            print(f"  Date: {details.get('date')}")

            # Check required fields
            assert details.get('company'), "Missing company"
            assert details.get('role'), "Missing role"
            assert details.get('date'), "Missing date"

            # Check expected values (case-insensitive)
            if 'company' in test_case['expected']:
                expected_company = test_case['expected']['company'].lower()
                actual_company = details['company'].lower()
                assert expected_company in actual_company or actual_company in expected_company, \
                    f"Company mismatch: expected '{expected_company}', got '{actual_company}'"

            if 'role' in test_case['expected']:
                expected_role = test_case['expected']['role'].lower()
                actual_role = details['role'].lower()
                # Check if key words from expected role are in actual role
                for word in expected_role.split():
                    if len(word) > 2:  # Skip short words like "for", "at"
                        assert word in actual_role, \
                            f"Role mismatch: '{word}' not found in '{actual_role}'"

            print("  ✓ Parsing successful")
        else:
            print("  ❌ Parsing failed")
            assert False, f"Failed to parse: {test_case['input']}"

    print("\n✅ All application parsing tests passed!\n")


def test_interview_parsing():
    """Test parsing of interview details from natural language"""
    print("\n=== Testing Interview Detail Parsing ===")

    test_cases = [
        {
            "input": "Interview with Google tomorrow at 2pm",
            "expected": {
                "company": "Google"
            }
        },
        {
            "input": "Phone screen with Meta on November 10th at 3:30 PM",
            "expected": {
                "company": "Meta"
            }
        },
        {
            "input": "Technical interview at Amazon with Jane next Friday",
            "expected": {
                "company": "Amazon"
            }
        }
    ]

    for test_case in test_cases:
        print(f"\nParsing: '{test_case['input']}'")
        details = parse_interview_details(test_case['input'])

        if details:
            print(f"  Company: {details.get('company')}")
            print(f"  Date: {details.get('date')}")
            print(f"  Time: {details.get('time')}")
            print(f"  Type: {details.get('interview_type')}")

            # Check required fields
            assert details.get('company'), "Missing company"
            assert details.get('date'), "Missing date"

            # Check expected values (case-insensitive)
            if 'company' in test_case['expected']:
                expected_company = test_case['expected']['company'].lower()
                actual_company = details['company'].lower()
                assert expected_company in actual_company or actual_company in expected_company, \
                    f"Company mismatch: expected '{expected_company}', got '{actual_company}'"

            print("  ✓ Parsing successful")
        else:
            print("  ❌ Parsing failed")
            assert False, f"Failed to parse: {test_case['input']}"

    print("\n✅ All interview parsing tests passed!\n")


def test_application_creation_from_text():
    """Test end-to-end application creation from natural language"""
    print("\n=== Testing Application Creation from Text ===")

    # Test creating application from text
    test_input = "Applied to TestCompany123 for Test Engineer Role"
    print(f"\nInput: '{test_input}'")

    # Parse details
    details = parse_application_details(test_input)
    assert details, "Failed to parse application details"
    print(f"Parsed: {details['company']} - {details['role']}")

    # Create application
    success, message = create_application_from_text(details)
    print(f"Result: {message}")
    assert success or "already exists" in message.lower(), f"Unexpected error: {message}"

    # Verify application was created by checking the database
    test_db = JobSearchDB()
    apps = test_db.list_applications()

    # Find our test application
    found = False
    for app in apps:
        if "testcompany123" in app.company.lower():
            found = True
            print(f"✅ Application found in database: {app.company} - {app.role}")

            # Clean up test application
            test_db.delete_application(app.id)
            print(f"✅ Test application cleaned up")
            break

    assert found, "Application not found in database after creation"

    print("\n✅ Application creation test passed!\n")


def test_interview_addition():
    """Test adding interviews to existing applications"""
    print("\n=== Testing Interview Addition ===")

    # Initialize test database
    test_db = JobSearchDB()

    # Create a test application first
    app = create_application(
        company="TestCompanyInterview456",
        role="Test Role for Interview",
        status="screening",
        applied_date=datetime.now().strftime("%Y-%m-%d")
    )
    app_id = test_db.add_application(app)
    print(f"✓ Created test application: {app.company} - {app.role}")

    try:
        # Test adding interview to existing application
        interview_text = "Technical interview with TestCompanyInterview456 tomorrow at 2pm"
        print(f"\nAdding interview: '{interview_text}'")

        details = parse_interview_details(interview_text)
        assert details, "Failed to parse interview details"

        success, message = add_interview_to_application(details)
        print(f"Result: {message}")
        assert success, f"Failed to add interview: {message}"

        # Verify interview was added
        updated_app = test_db.get_application(app_id)
        assert updated_app, "Application not found after interview addition"

        # Check status was updated
        assert updated_app.status == "interview", f"Status not updated, got: {updated_app.status}"

        # Check notes were added
        assert len(updated_app.notes) > 0, "No notes added"
        assert "interview scheduled" in updated_app.notes.lower(), "Interview note not added"

        print("✅ Interview added successfully!")

    finally:
        # Cleanup - delete test application
        test_db.delete_application(app_id)
        print(f"✅ Test application cleaned up")

    print("\n✅ All interview addition tests passed!\n")


def run_all_tests():
    """Run all Day 4 tests"""
    print("=" * 60)
    print("DAY 4: Natural Language Job Tracking - Test Suite")
    print("=" * 60)

    try:
        # Intent detection tests (no API calls)
        test_application_intent_detection()
        test_interview_intent_detection()

        print("\n" + "=" * 60)
        print("Note: The following tests require Google API key")
        print("They will use the LLM to parse natural language")
        print("=" * 60)

        # Parsing tests (requires API key)
        try:
            test_application_parsing()
            test_interview_parsing()

            # End-to-end tests (requires API key)
            test_application_creation_from_text()
            test_interview_addition()

            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 60)

        except Exception as e:
            if "authentication" in str(e).lower() or "api" in str(e).lower():
                print("\n⚠️ Some tests skipped: Google API key not configured")
                print("Set GOOGLE_API_KEY environment variable to run all tests")
                print("\nBasic tests (intent detection) passed! ✅")
            else:
                raise

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
