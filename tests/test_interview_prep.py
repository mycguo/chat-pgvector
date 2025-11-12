"""
Quick test script for interview prep functionality
"""

import sys
sys.path.insert(0, '.')

from storage.interview_db import InterviewDB
from models.interview_prep import create_interview_question

def test_interview_db():
    """Test basic interview database operations"""
    print("Testing Interview DB...")

    # Initialize database
    db = InterviewDB()

    # Create a sample question
    question = create_interview_question(
        question="Tell me about a time you led a difficult project",
        type="behavioral",
        category="leadership",
        difficulty="medium",
        answer_full="In my previous role as a senior developer...",
        answer_star={
            'situation': 'Led a team of 5 developers on a critical migration project',
            'task': 'Migrate legacy system to microservices within 3 months',
            'action': 'Created detailed migration plan, set up daily standups, implemented CI/CD',
            'result': 'Completed migration 2 weeks early, reduced deployment time by 70%'
        },
        tags=['leadership', 'project-management', 'migration'],
        companies=['Google', 'Amazon'],
        confidence_level=4
    )

    # Add question to database
    q_id = db.add_question(question)
    print(f"✅ Created question with ID: {q_id}")

    # Retrieve question
    retrieved = db.get_question(q_id)
    assert retrieved is not None, "Failed to retrieve question"
    assert retrieved.question == question.question
    print(f"✅ Retrieved question: {retrieved.question[:50]}...")

    # List questions
    questions = db.list_questions()
    print(f"✅ Total questions in database: {len(questions)}")

    # Filter by type
    behavioral = db.list_questions(type="behavioral")
    print(f"✅ Behavioral questions: {len(behavioral)}")

    # Filter by company
    google_questions = db.list_questions(company="Google")
    print(f"✅ Google-related questions: {len(google_questions)}")

    # Get stats
    stats = db.get_stats()
    print(f"✅ Stats: {stats['total_questions']} questions, {stats['total_concepts']} concepts")

    # Mark as practiced
    db.mark_question_practiced(q_id)
    updated = db.get_question(q_id)
    assert updated.practice_count == 1, "Practice count not updated"
    print(f"✅ Marked question as practiced")

    print("\n✨ All tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_interview_db()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
