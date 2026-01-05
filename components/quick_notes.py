"""
Quick Notes Component

Opens Quick Notes in a new browser tab for side-by-side viewing.
"""

import streamlit as st


def render_quick_notes():
    """Render quick notes button"""

    # Quick Notes section in sidebar
    with st.sidebar:

        # Button to navigate to Quick Notes page
        if st.button("📝 Quick Notes", use_container_width=True, type="secondary"):
            st.switch_page("pages/quick_notes.py")

        st.caption("Quick reference information")
