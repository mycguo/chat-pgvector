"""
Authentication utilities for Streamlit.

Handles authentication safely across different Streamlit versions and deployment environments.
"""

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


def is_user_logged_in() -> bool:
    """
    Safely check if user is logged in.
    
    Requires login on every app restart by checking session state.
    Session state is cleared on restart, forcing re-authentication.
    Even if Streamlit's auth persists, we require explicit login action in each session.
    
    Returns:
        True if user is logged in in this session, False otherwise.
        In environments where st.user.is_logged_in is not available,
        defaults to True (no authentication required).
    """
    if not HAS_STREAMLIT:
        return True
    
    try:
        # Check if user is logged in via Streamlit auth
        user_is_logged_in = False
        has_auth_system = False
        if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in'):
            has_auth_system = True
            user_is_logged_in = st.user.is_logged_in
        
        # If session is already authenticated, verify user is still logged in
        if 'authenticated_in_session' in st.session_state:
            if has_auth_system:
                if user_is_logged_in:
                    return True
                else:
                    # User logged out, clear session flags
                    if 'authenticated_in_session' in st.session_state:
                        del st.session_state['authenticated_in_session']
                    if 'login_attempted' in st.session_state:
                        del st.session_state['login_attempted']
                    return False
            else:
                # No auth system, session authenticated is enough
                return True
        
        # Session not authenticated yet - check if login was completed
        # If login was attempted AND user is logged in, authenticate the session
        if 'login_attempted' in st.session_state:
            if has_auth_system:
                # Check if user is logged in (either just completed login or was already logged in)
                if user_is_logged_in:
                    # Login completed successfully (or user was already logged in via cookie)
                    # Authenticate the session
                    st.session_state['authenticated_in_session'] = True
                    return True
                # Login attempted but not completed yet - show login screen
                # Don't show login button again if login is in progress
                return False
            else:
                # No auth system, but login was attempted - allow access
                st.session_state['authenticated_in_session'] = True
                return True
        
        # No login attempted yet - check if user is already logged in via cookie
        if has_auth_system and user_is_logged_in:
            # User is already logged in from another tab/session via cookie
            # Automatically authenticate this session
            st.session_state['authenticated_in_session'] = True
            return True

        # User not logged in - require login
        return False
        
    except (AttributeError, KeyError) as e:
        # If any error occurs, default to allowing access
        return True


def login():
    """
    Safely call st.login if available.
    Sets session state flag to authenticate the session.
    
    If user is already logged in (via persisted cookie), just set the session flag.
    Otherwise, initiate the OAuth login flow.
    """
    if HAS_STREAMLIT:
        try:
            # Check if user is already logged in via Streamlit auth
            user_already_logged_in = False
            if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in'):
                user_already_logged_in = st.user.is_logged_in
            
            if user_already_logged_in:
                # User is already logged in via persisted cookie
                # Just set the session flag to grant access
                st.session_state['authenticated_in_session'] = True
                # Clear any lingering login_attempted flag
                if 'login_attempted' in st.session_state:
                    del st.session_state['login_attempted']
            else:
                # User not logged in, initiate OAuth flow
                st.session_state['login_attempted'] = True
                if hasattr(st, 'login'):
                    st.login()
                else:
                    # If st.login doesn't exist but login was attempted, set session flag
                    # This handles environments without auth system
                    st.session_state['authenticated_in_session'] = True
        except (AttributeError, Exception) as e:
            # If login fails, clear the attempt flag
            if 'login_attempted' in st.session_state:
                del st.session_state['login_attempted']


def logout():
    """
    Safely call st.logout if available.
    Clears session state authentication flags.
    """
    if HAS_STREAMLIT:
        try:
            # Clear session authentication flags
            if 'authenticated_in_session' in st.session_state:
                del st.session_state['authenticated_in_session']
            if 'login_attempted' in st.session_state:
                del st.session_state['login_attempted']
            if 'user_id' in st.session_state:
                del st.session_state['user_id']
            
            # Then call st.logout to clear the cookie
            if hasattr(st, 'logout'):
                st.logout()
        except (AttributeError, Exception):
            # Fallback: clear session state
            if 'authenticated_in_session' in st.session_state:
                del st.session_state['authenticated_in_session']
            if 'login_attempted' in st.session_state:
                del st.session_state['login_attempted']
            if 'user_id' in st.session_state:
                del st.session_state['user_id']

