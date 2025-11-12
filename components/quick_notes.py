"""
Quick Notes Component

Opens Quick Notes in a new browser tab for side-by-side viewing.
"""

import streamlit as st


def render_quick_notes():
    """Render quick notes button that opens in a new tab"""

    # Quick Notes section in sidebar
    with st.sidebar:

        # Button to open in new tab using custom HTML
        st.markdown("""
            <a href="/quick_notes" target="_blank" style="text-decoration: none;">
                <button style="
                    width: 100%;
                    padding: 0.5rem 1rem;
                    background-color: #FF4B4B;
                    color: white;
                    border: none;
                    border-radius: 0.5rem;
                    font-size: 1rem;
                    cursor: pointer;
                    font-weight: 500;
                ">
                    📝 Quick Notes (New Tab)
                </button>
            </a>
        """, unsafe_allow_html=True)

        st.caption("Opens in a new tab")
