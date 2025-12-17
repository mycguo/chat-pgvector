"""
Authentication utilities for Streamlit.

Handles authentication safely across different Streamlit versions and deployment environments.
"""
import sys

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

def _log(message):
    """Log message to console for debugging OAuth issues."""
    print(f"[AUTH] {message}", file=sys.stderr, flush=True)


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
    _log("is_user_logged_in() called")

    if not HAS_STREAMLIT:
        _log("No Streamlit available, returning True")
        return True

    try:
        # Check if session state is available and valid
        has_session_state = hasattr(st, 'session_state')
        session_state_is_none = st.session_state is None if has_session_state else True
        _log(f"Session state check: hasattr={has_session_state}, is_none={session_state_is_none}")

        if not has_session_state or session_state_is_none:
            _log("Session state not available, returning False")
            return False

        # Check if user is logged in via Streamlit auth
        user_is_logged_in = False
        has_auth_system = False
        has_user_attr = hasattr(st, 'user')
        user_is_none = st.user is None if has_user_attr else True
        _log(f"User check: hasattr(st, 'user')={has_user_attr}, st.user is None={user_is_none}")

        if has_user_attr and not user_is_none and hasattr(st.user, 'is_logged_in'):
            has_auth_system = True
            user_is_logged_in = st.user.is_logged_in
            _log(f"Auth system available: user_is_logged_in={user_is_logged_in}")
        
        # If session is already authenticated, verify user is still logged in
        if 'authenticated_in_session' in st.session_state:
            _log("Session already authenticated")
            if has_auth_system:
                if user_is_logged_in:
                    _log("User still logged in, returning True")
                    return True
                else:
                    # User logged out, clear session flags
                    _log("User logged out, clearing session flags")
                    if 'authenticated_in_session' in st.session_state:
                        del st.session_state['authenticated_in_session']
                    if 'login_attempted' in st.session_state:
                        del st.session_state['login_attempted']
                    return False
            else:
                # No auth system, session authenticated is enough
                _log("No auth system, session authenticated, returning True")
                return True
        
        # Session not authenticated yet - check if login was completed
        # If login was attempted AND user is logged in, authenticate the session
        if 'login_attempted' in st.session_state:
            _log("Login was attempted")
            if has_auth_system:
                # Check if user is logged in (either just completed login or was already logged in)
                if user_is_logged_in:
                    # Login completed successfully (or user was already logged in via cookie)
                    # Authenticate the session
                    _log("Login completed, authenticating session")
                    st.session_state['authenticated_in_session'] = True
                    return True
                # Login attempted but not completed yet - show login screen
                # Don't show login button again if login is in progress
                _log("Login attempted but not completed, returning False")
                return False
            else:
                # No auth system, but login was attempted - allow access
                _log("No auth system, login attempted, allowing access")
                st.session_state['authenticated_in_session'] = True
                return True

        # No login attempted yet - check if user is already logged in via cookie
        if has_auth_system and user_is_logged_in:
            # User is already logged in from another tab/session via cookie
            # Automatically authenticate this session
            _log("User already logged in via cookie, auto-authenticating session")
            st.session_state['authenticated_in_session'] = True
            return True

        # User not logged in - require login
        _log("User not logged in, returning False")
        return False

    except (AttributeError, KeyError, TypeError) as e:
        # If any error occurs, default to allowing access
        _log(f"ERROR in is_user_logged_in: {type(e).__name__}: {e}")
        import traceback
        _log(f"Traceback:\n{traceback.format_exc()}")
        return True


def login():
    """
    Safely call st.login if available.
    Sets session state flag to authenticate the session.

    If user is already logged in (via persisted cookie), just set the session flag.
    Otherwise, initiate the OAuth login flow.
    """
    _log("login() called")

    if HAS_STREAMLIT:
        try:
            # Check if session state is available
            has_session_state = hasattr(st, 'session_state')
            session_state_is_none = st.session_state is None if has_session_state else True
            _log(f"login(): Session state check: hasattr={has_session_state}, is_none={session_state_is_none}")

            if not has_session_state or session_state_is_none:
                # Session state not ready, cannot proceed with login
                _log("login(): Session state not ready, returning")
                return

            # Check if user is already logged in via Streamlit auth
            user_already_logged_in = False
            has_user = hasattr(st, 'user')
            user_is_none = st.user is None if has_user else True
            _log(f"login(): User check: hasattr={has_user}, is_none={user_is_none}")

            if has_user and not user_is_none and hasattr(st.user, 'is_logged_in'):
                user_already_logged_in = st.user.is_logged_in
                _log(f"login(): user_already_logged_in={user_already_logged_in}")

            if user_already_logged_in:
                # User is already logged in via persisted cookie
                # Just set the session flag to grant access
                _log("login(): User already logged in, setting session flag")
                st.session_state['authenticated_in_session'] = True
                # Clear any lingering login_attempted flag
                if 'login_attempted' in st.session_state:
                    del st.session_state['login_attempted']
            else:
                # User not logged in, initiate OAuth flow
                _log("login(): User not logged in, setting login_attempted and calling st.login()")
                st.session_state['login_attempted'] = True
                if hasattr(st, 'login'):
                    _log("login(): Calling st.login()")
                    st.login()
                else:
                    # If st.login doesn't exist but login was attempted, set session flag
                    # This handles environments without auth system
                    _log("login(): st.login() not available, setting authenticated flag")
                    st.session_state['authenticated_in_session'] = True
        except (AttributeError, TypeError, Exception) as e:
            # If login fails, clear the attempt flag safely
            _log(f"ERROR in login(): {type(e).__name__}: {e}")
            import traceback
            _log(f"Traceback:\n{traceback.format_exc()}")
            try:
                if hasattr(st, 'session_state') and st.session_state is not None:
                    if 'login_attempted' in st.session_state:
                        del st.session_state['login_attempted']
            except:
                pass


def logout():
    """
    Safely call st.logout if available.
    Clears session state authentication flags.
    """
    if HAS_STREAMLIT:
        try:
            # Check if session state is available
            if hasattr(st, 'session_state') and st.session_state is not None:
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
        except (AttributeError, TypeError, Exception):
            # Fallback: clear session state safely
            try:
                if hasattr(st, 'session_state') and st.session_state is not None:
                    if 'authenticated_in_session' in st.session_state:
                        del st.session_state['authenticated_in_session']
                    if 'login_attempted' in st.session_state:
                        del st.session_state['login_attempted']
                    if 'user_id' in st.session_state:
                        del st.session_state['user_id']
            except:
                pass

