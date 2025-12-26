"""
Question Bank Page

Browse, search, and manage all your interview questions in one place.
"""

import streamlit as st
import sys
from datetime import datetime
from typing import List
from difflib import SequenceMatcher

# Add parent directory to path
sys.path.insert(0, '.')

from storage.interview_db import InterviewDB
from storage.auth_utils import is_user_logged_in, logout, render_login_button
from models.interview_prep import InterviewQuestion


def fuzzy_match(query: str, text: str, threshold: float = 0.6) -> bool:
    """
    Fuzzy string matching using SequenceMatcher.

    Args:
        query: Search query
        text: Text to search in
        threshold: Similarity threshold (0.0 to 1.0)

    Returns:
        True if similarity is above threshold
    """
    if not query or not text:
        return False

    query_lower = query.lower()
    text_lower = text.lower()

    # Direct substring match (highest priority)
    if query_lower in text_lower:
        return True

    # Fuzzy match on words
    query_words = query_lower.split()
    text_words = text_lower.split()

    for q_word in query_words:
        for t_word in text_words:
            similarity = SequenceMatcher(None, q_word, t_word).ratio()
            if similarity >= threshold:
                return True

    return False


def show_question_list_item(question: InterviewQuestion, is_selected: bool = False):
    """Display a compact question list item with card design"""
    # Determine styling based on selection
    border_color = "#4285F4" if is_selected else "#e0e0e0"
    bg_color = "#f0f7ff" if is_selected else "#ffffff"

    # Difficulty badge colors
    difficulty_colors = {
        "easy": "#28a745",
        "medium": "#FFA500",
        "hard": "#dc3545"
    }
    difficulty_color = difficulty_colors.get(question.difficulty, "#666")

    # Type badge colors
    type_colors = {
        "behavioral": "#9c27b0",
        "technical": "#2196f3",
        "system_design": "#ff9800",
        "case_study": "#00bcd4"
    }
    type_color = type_colors.get(question.type, "#666")

    clicked = st.button(
        " ",
        key=f"select_{question.id}",
        use_container_width=True
    )

    # Display card content (this renders above the button due to Streamlit's layout)
    st.markdown(f"""
        <div style='
            background-color: {bg_color};
            padding: 14px;
            border-radius: 6px;
            margin: -50px 0 8px 0;
            border-left: 3px solid {border_color};
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            cursor: pointer;
            pointer-events: none;
        '>
            <p style='margin: 0 0 8px 0; font-weight: 500; font-size: 14px; color: #222; line-height: 1.4;'>{question.question}</p>
            <div style='display: flex; gap: 6px; align-items: center; flex-wrap: wrap;'>
                <span style='background-color: {type_color}22; color: {type_color}; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;'>{question.get_display_type()}</span>
                <span style='background-color: {difficulty_color}22; color: {difficulty_color}; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;'>{question.difficulty.title()}</span>
                <span style='color: #666; font-size: 12px; margin-left: 4px;'>{question.importance}/10</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    return clicked


def show_question_detail_panel(question: InterviewQuestion, db: InterviewDB):
    """Display question detail in right panel with STAR method format"""
    st.markdown(f"## {question.question}")

    # Question metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"**Type:** {question.get_display_type()}")
    with col2:
        st.caption(f"**Difficulty:** {question.difficulty.title()}")
    with col3:
        st.caption(f"**Importance:** {question.importance}/10")

    st.divider()

    # Display answer in STAR format if behavioral
    if question.type == "behavioral" and question.answer_star:
        st.markdown("### 📝 Answer (STAR Method)")

        if question.answer_star.get('situation'):
            st.markdown("**💼 Situation:**")
            st.write(question.answer_star['situation'])
            st.write("")

        if question.answer_star.get('task'):
            st.markdown("**🎯 Task:**")
            st.write(question.answer_star['task'])
            st.write("")

        if question.answer_star.get('action'):
            st.markdown("**⚡ Action:**")
            # Check if action is a list or string
            if isinstance(question.answer_star['action'], list):
                for action_item in question.answer_star['action']:
                    st.markdown(f"• {action_item}")
            else:
                st.write(question.answer_star['action'])
            st.write("")

        if question.answer_star.get('result'):
            st.markdown("**🎉 Result:**")
            # Check if result is a list or string
            if isinstance(question.answer_star['result'], list):
                for result_item in question.answer_star['result']:
                    st.markdown(f"• {result_item}")
            else:
                st.write(question.answer_star['result'])

    elif question.answer_full:
        st.markdown("### 📝 Answer")
        st.write(question.answer_full)

    # Notes section
    if question.notes:
        st.divider()
        st.markdown("### 📌 Notes")
        st.info(question.notes)

    # Practice info
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Practice Count", question.practice_count)
    with col2:
        if question.last_practiced:
            days_ago = (datetime.now() - datetime.fromisoformat(question.last_practiced)).days
            st.metric("Last Practiced", f"{days_ago} days ago")
        else:
            st.metric("Last Practiced", "Never")

    # Action buttons
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎓 Mark as Practiced", type="primary", use_container_width=True):
            question.mark_practiced()
            db.update_question(question)
            st.success("✅ Marked as practiced!")
            st.rerun()
    with col2:
        if st.button("✏️ Edit Question", use_container_width=True):
            st.session_state['edit_question_id'] = question.id
            st.rerun()


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
    # Hide sidebar navigation before login and style the login button with Google blue
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            /* Google blue branding for login button */
            .stButton > button[kind="primary"] {
                background-color: #4285F4 !important;
                border-color: #4285F4 !important;
            }
            .stButton > button[kind="primary"]:hover {
                background-color: #357ae8 !important;
                border-color: #357ae8 !important;
            }
            .stButton > button[kind="primary"]:active {
                background-color: #2a66c9 !important;
                border-color: #2a66c9 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("Please log in to access Questions")
    st.subheader("Please log in.")
    render_login_button(type="primary", use_container_width=True)


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

    # Search box at the top
    search_query = st.text_input(
        "🔍 Semantic Search",
        placeholder='Try: "find hard python data structure questions"',
        help="Fuzzy search across questions, answers, tags, and notes. Works with typos and partial matches!"
    )

    st.divider()

    # Initialize selected question in session state
    if 'selected_question_id' not in st.session_state and all_questions:
        st.session_state['selected_question_id'] = all_questions[0].id

    # Two-column layout: Questions list (left) and Detail (right)
    left_col, right_col = st.columns([1, 2])

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

    # Search filter with fuzzy matching
    if search_query:
        filtered_questions = [
            q for q in filtered_questions
            if fuzzy_match(search_query, q.question, threshold=0.6) or
               fuzzy_match(search_query, q.notes, threshold=0.6) or
               fuzzy_match(search_query, q.category, threshold=0.7) or
               any(fuzzy_match(search_query, tag, threshold=0.7) for tag in q.tags) or
               (q.answer_full and fuzzy_match(search_query, q.answer_full, threshold=0.5))
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

    # LEFT PANEL: Question List
    with left_col:
        st.markdown(f"### Interview Question Bank")
        st.caption(f"Showing {len(filtered_questions)} of {len(all_questions)} questions")
        st.markdown("---")

        if len(filtered_questions) == 0:
            st.info("🔍 No questions found. Try adjusting your filters!")
            if st.button("🔄 Clear Filters", key="clear_filters_panel", use_container_width=True):
                st.rerun()
        else:
            # Display question list
            for question in filtered_questions:
                is_selected = st.session_state.get('selected_question_id') == question.id
                if show_question_list_item(question, is_selected):
                    st.session_state['selected_question_id'] = question.id
                    st.rerun()

    # RIGHT PANEL: Question Detail
    with right_col:
        if st.session_state.get('selected_question_id'):
            selected_question = next(
                (q for q in all_questions if q.id == st.session_state['selected_question_id']),
                None
            )
            if selected_question:
                show_question_detail_panel(selected_question, db)
            else:
                st.info("Select a question from the list to view details")
        else:
            st.info("Select a question from the list to view details")

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
