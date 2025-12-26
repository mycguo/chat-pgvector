"""
Shared styles for the application.
"""
import streamlit as st


def apply_google_button_style():
    """Apply Google blue color to all primary buttons."""
    st.markdown("""
        <style>
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
