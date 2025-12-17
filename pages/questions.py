"""
Question Bank Page

Browse, search, and manage all your interview questions in one place.
"""

import streamlit as st
import sys
from datetime import datetime
from typing import List

# Add parent directory to path
sys.path.insert(0, '.')

from storage.interview_db import InterviewDB
from storage.auth_utils import is_user_logged_in, logout, render_login_button
from models.interview_prep import InterviewQuestion


def show_question_card(question: InterviewQuestion, db: InterviewDB):
    """Display a question as a card"""
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 1, 1])

        with col1:
            st.markdown(f"**{question.question}**")

            # Badges
            badges = []
            badges.append(question.get_display_type())
            badges.append(f"{question.get_difficulty_emoji()} {question.difficulty.title()}")
            badges.append(f"📁 {question.category.title()}")

            st.caption(" • ".join(badges))

            # Tags
            if question.tags:
                tag_text = " ".join([f"`{tag}`" for tag in question.tags[:3]])
                st.caption(f"🏷️ {tag_text}")

        with col2:
            st.write(f"**Importance:** {question.get_importance_emoji()} {question.importance}/10")
            if question.practice_count > 0:
                st.caption(f"✅ Practiced {question.practice_count}x")
            else:
                st.caption("⚠️ Not practiced yet")

        with col3:
            if question.last_practiced:
                days_ago = (datetime.now() - datetime.fromisoformat(question.last_practiced)).days
                if days_ago == 0:
                    st.caption("🕐 Today")
                elif days_ago == 1:
                    st.caption("🕐 Yesterday")
                else:
                    st.caption(f"🕐 {days_ago}d ago")
            else:
                st.caption("🕐 Never")

        with col4:
            if st.button("🎓 Practice", key=f"practice_{question.id}", width="stretch"):
                # Mark as practiced
                question.mark_practiced()
                db.update_question(question)
                st.success("✅ Marked as practiced!")
                st.rerun()

        with col5:
            if st.button("View", key=f"view_{question.id}", width="stretch"):
                st.session_state['view_question_id'] = question.id
                st.rerun()

        st.divider()


def get_unique_values(questions: List[InterviewQuestion], field: str) -> List[str]:
    """Extract unique values for a field from questions"""
    values = set()
    for q in questions:
        if field == 'companies':
            values.update(q.companies)
        elif field == 'tags':
            values.update(q.tags)
        elif field == 'category':
            values.add(q.category)
        elif field == 'type':
            values.add(q.type)
    return sorted(list(values))


def login_screen():
    st.header("Please log in to access Questions")
    st.subheader("Please log in.")
    render_login_button()


def main():
    st.set_page_config(page_title="Question Bank", page_icon="📝", layout="wide")

    if not is_user_logged_in():
        login_screen()
        return

    st.title("📝 Question Bank")
    st.markdown("Browse and manage all your interview questions")

    # Initialize database
    db = InterviewDB()

    # Check if viewing a specific question (reuse detail view from interview_prep)
    if st.session_state.get('view_question_id'):
        # Import and use the detail view from interview_prep
        from pages.interview_prep import show_question_detail
        show_question_detail(db, st.session_state['view_question_id'])
        return

    # Get all questions
    all_questions = db.list_questions()

    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filters")

        # Type filter
        types = ["All"] + get_unique_values(all_questions, 'type')
        filter_type = st.selectbox(
            "Type",
            types,
            help="Filter by question type"
        )

        # Category filter
        categories = ["All"] + get_unique_values(all_questions, 'category')
        filter_category = st.selectbox(
            "Category",
            categories,
            help="Filter by category"
        )

        # Importance filter
        filter_importance = st.selectbox(
            "Importance",
            ["All", "10", "9", "8", "7", "6", "5", "4", "3", "2", "1"],
            help="Filter by importance level"
        )

        # Confidence filter
        filter_confidence = st.selectbox(
            "Confidence Level",
            ["All", "Low (1-2)", "Medium (3)", "High (4-5)"],
            help="Filter by your confidence level"
        )

        # Practice status filter
        filter_practice = st.selectbox(
            "Practice Status",
            ["All", "Practiced", "Not Practiced", "Needs Review (>7 days)"],
            help="Filter by practice status"
        )

        st.divider()

        # Sort options
        st.header("📊 Sort By")

        sort_by = st.selectbox(
            "Sort",
            [
                "Created (Newest)",
                "Created (Oldest)",
                "Last Practiced (Recent)",
                "Last Practiced (Oldest)",
                "Practice Count (High to Low)",
                "Practice Count (Low to High)",
                "Confidence (High to Low)",
                "Confidence (Low to High)",
                "Question (A-Z)",
                "Question (Z-A)"
            ]
        )

        st.divider()

        # Quick stats
        st.header("📈 Stats")
        stats = db.get_stats()

        st.metric("Total Questions", stats['total_questions'])
        st.metric("Practiced", f"{stats['practice_percentage']:.0f}%")

        if st.button("🔄 Clear Filters", key="clear_filters_sidebar", width="stretch"):
            st.rerun()

    # Main content area
    col1, col2 = st.columns([3, 1])

    with col1:
        # Search box
        search_query = st.text_input(
            "🔍 Search questions",
            placeholder="Search by question text, tags, or notes...",
            help="Search in question text, tags, and notes"
        )

    with col2:
        # View options
        view_mode = st.radio(
            "View",
            ["Cards", "Compact"],
            horizontal=True,
            label_visibility="collapsed"
        )

    st.divider()

    # Apply filters
    filtered_questions = all_questions.copy()

    # Type filter
    if filter_type != "All":
        filtered_questions = [q for q in filtered_questions if q.type == filter_type]

    # Category filter
    if filter_category != "All":
        filtered_questions = [q for q in filtered_questions if q.category == filter_category]

    # Importance filter
    if filter_importance != "All":
        filtered_questions = [q for q in filtered_questions if q.importance == int(filter_importance)]

    # Confidence filter
    if filter_confidence == "Low (1-2)":
        filtered_questions = [q for q in filtered_questions if q.confidence_level <= 2]
    elif filter_confidence == "Medium (3)":
        filtered_questions = [q for q in filtered_questions if q.confidence_level == 3]
    elif filter_confidence == "High (4-5)":
        filtered_questions = [q for q in filtered_questions if q.confidence_level >= 4]

    # Practice status filter
    if filter_practice == "Practiced":
        filtered_questions = [q for q in filtered_questions if q.practice_count > 0]
    elif filter_practice == "Not Practiced":
        filtered_questions = [q for q in filtered_questions if q.practice_count == 0]
    elif filter_practice == "Needs Review (>7 days)":
        filtered_questions = [
            q for q in filtered_questions
            if q.last_practiced and
            (datetime.now() - datetime.fromisoformat(q.last_practiced)).days > 7
        ]

    # Search filter
    if search_query:
        search_lower = search_query.lower()
        filtered_questions = [
            q for q in filtered_questions
            if search_lower in q.question.lower() or
               search_lower in q.notes.lower() or
               any(search_lower in tag.lower() for tag in q.tags) or
               search_lower in q.category.lower()
        ]

    # Apply sorting
    if sort_by == "Created (Newest)":
        filtered_questions.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_by == "Created (Oldest)":
        filtered_questions.sort(key=lambda x: x.created_at, reverse=False)
    elif sort_by == "Last Practiced (Recent)":
        filtered_questions.sort(
            key=lambda x: x.last_practiced if x.last_practiced else "1970-01-01",
            reverse=True
        )
    elif sort_by == "Last Practiced (Oldest)":
        filtered_questions.sort(
            key=lambda x: x.last_practiced if x.last_practiced else "9999-12-31",
            reverse=False
        )
    elif sort_by == "Practice Count (High to Low)":
        filtered_questions.sort(key=lambda x: x.practice_count, reverse=True)
    elif sort_by == "Practice Count (Low to High)":
        filtered_questions.sort(key=lambda x: x.practice_count, reverse=False)
    elif sort_by == "Confidence (High to Low)":
        filtered_questions.sort(key=lambda x: x.confidence_level, reverse=True)
    elif sort_by == "Confidence (Low to High)":
        filtered_questions.sort(key=lambda x: x.confidence_level, reverse=False)
    elif sort_by == "Question (A-Z)":
        filtered_questions.sort(key=lambda x: x.question.lower())
    elif sort_by == "Question (Z-A)":
        filtered_questions.sort(key=lambda x: x.question.lower(), reverse=True)

    # Display results
    st.write(f"**Showing {len(filtered_questions)} of {len(all_questions)} questions**")

    if len(filtered_questions) == 0:
        st.info("🔍 No questions found. Try adjusting your filters or add new questions!")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Question", key="add_question_empty", type="primary", width="stretch"):
                st.switch_page("pages/interview_prep.py")
        with col2:
            if st.button("🔄 Clear Filters", key="clear_filters_empty", width="stretch"):
                st.rerun()
    else:
        # Display questions based on view mode
        if view_mode == "Cards":
            for question in filtered_questions:
                show_question_card(question, db)
        else:
            # Compact view
            for question in filtered_questions:
                col1, col2, col3, col4 = st.columns([5, 2, 2, 1])

                with col1:
                    st.markdown(f"**{question.question[:80]}{'...' if len(question.question) > 80 else ''}**")
                    badges = f"{question.get_display_type()} • {question.get_difficulty_emoji()} • {question.category.title()}"
                    st.caption(badges)

                with col2:
                    st.caption(f"Importance: {question.get_importance_emoji()} {question.importance}/10")

                with col3:
                    st.caption(f"Practiced: {question.practice_count}x")

                with col4:
                    if st.button("View", key=f"compact_view_{question.id}"):
                        st.session_state['view_question_id'] = question.id
                        st.rerun()

                st.divider()

    # Bottom actions
    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🏠 Home", key="nav_home", width="stretch"):
            st.switch_page("app.py")

    with col2:
        if st.button("🎯 Interview Prep", key="nav_interview_prep", width="stretch"):
            st.switch_page("pages/interview_prep.py")

    with col3:
        if st.button("📝 Applications", key="nav_applications", width="stretch"):
            st.switch_page("pages/applications.py")

    with col4:
        if st.button("➕ Add Question", key="add_question_bottom", width="stretch", type="primary"):
            st.switch_page("pages/interview_prep.py")

    # Logout button
    st.divider()
    st.button("Log out", key="logout_button", on_click=logout)


if __name__ == "__main__":
    main()
