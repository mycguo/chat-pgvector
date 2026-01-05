"""
Authentication utilities for Streamlit.

Handles authentication safely across different Streamlit versions and deployment environments.
"""

import os
import secrets
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import requests

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

REQUIRED_OAUTH_KEYS = ("oauth_provider", "oauth_client_id", "oauth_client_secret")


def get_auth_config_status() -> Dict[str, Any]:
    """Return OAuth configuration status for the current environment."""
    if not HAS_STREAMLIT:
        return {
            "requires_oauth": False,
            "is_configured": True,
            "missing_keys": [],
            "provider": None,
        }

    requires_oauth = bool(os.getenv("STREAMLIT_SHARING_MODE"))
    secrets = getattr(st, "secrets", None)
    missing_keys: List[str] = []
    provider = None

    if secrets:
        provider = secrets.get("oauth_provider")
        for key in REQUIRED_OAUTH_KEYS:
            if not secrets.get(key):
                missing_keys.append(key)
    else:
        missing_keys = list(REQUIRED_OAUTH_KEYS)

    is_configured = not (requires_oauth and missing_keys)

    return {
        "requires_oauth": requires_oauth,
        "is_configured": is_configured,
        "missing_keys": missing_keys,
        "provider": provider,
    }


def render_auth_config_warning(status: Optional[Dict[str, Any]] = None) -> None:
    """Render a warning telling the user how to fix OAuth configuration."""
    if not HAS_STREAMLIT:
        return

    status = status or get_auth_config_status()
    if not status.get("requires_oauth") or status.get("is_configured"):
        return

    missing = status.get("missing_keys") or REQUIRED_OAUTH_KEYS
    missing_keys_list = "\n".join(f"- `{key}`" for key in missing)

    st.error("Google login isn't configured for this Streamlit Cloud deployment.")
    st.markdown(
        """
To fix this, add the following secrets in Streamlit Cloud (**App → Settings → Secrets**),
then redeploy the app:

{missing_keys}

See `docs/OAUTH_REDIRECT_URI_SETUP.md` for full Google Cloud setup instructions.
""".format(missing_keys=missing_keys_list)
    )


def is_user_logged_in() -> bool:
    """
    Safely check if user is logged in via Google or LinkedIn.

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
        # Check if user is logged in via LinkedIn
        if is_linkedin_user_logged_in():
            return True

        # Check if user is logged in via Streamlit auth (Google)
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
        status = get_auth_config_status()
        if not status.get("is_configured"):
            render_auth_config_warning(status)
            return

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
    Clears ALL session state and authentication data for both Google and LinkedIn.

    For LinkedIn: clears session and calls st.rerun()
    For Google: clears session and calls st.logout() which handles redirect
    """
    if HAS_STREAMLIT:
        try:
            # Check if logged in via LinkedIn BEFORE clearing session state
            is_linkedin = st.session_state.get('auth_provider') == 'linkedin' or st.session_state.get('linkedin_authenticated')

            # Clear LinkedIn session if logged in via LinkedIn
            linkedin_logout()

            # Clear all authentication-related session state
            auth_keys_to_clear = [
                'authenticated_in_session',
                'login_attempted',
                'user_id',
                'cached_user_id',
                # LinkedIn specific (redundant but safe)
                'linkedin_authenticated',
                'linkedin_user_info',
                'linkedin_access_token',
                'linkedin_oauth_state',
                'linkedin_login_initiated',
                'linkedin_callback_processed',
                'auth_provider',
            ]

            for key in auth_keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            # Handle logout based on provider
            if is_linkedin:
                # For LinkedIn, rerun to show login screen
                st.rerun()
            else:
                # For Google OAuth, call st.logout which handles redirect automatically
                if hasattr(st, 'logout'):
                    st.logout()
        except (AttributeError, Exception):
            # Fallback: clear session state
            linkedin_logout()

            # Clear all authentication-related session state
            auth_keys_to_clear = [
                'authenticated_in_session',
                'login_attempted',
                'user_id',
                'cached_user_id',
                'linkedin_authenticated',
                'linkedin_user_info',
                'linkedin_access_token',
                'linkedin_oauth_state',
                'linkedin_login_initiated',
                'linkedin_callback_processed',
                'auth_provider',
            ]

            for key in auth_keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]


def render_login_button(label: str = "Log in with Google", **button_kwargs: Any) -> bool:
    """Render the login button with OAuth configuration validation."""
    if not HAS_STREAMLIT:
        return False

    status = get_auth_config_status()
    disabled = not status.get("is_configured", True)
    if disabled:
        render_auth_config_warning(status)

    clicked = st.button(label, disabled=disabled, **button_kwargs)
    if clicked:
        login()
        return True
    return False


# ==================== LinkedIn OAuth Functions ====================

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USER_INFO_URL = "https://api.linkedin.com/v2/userinfo"


def get_linkedin_config() -> Dict[str, str]:
    """Get LinkedIn OAuth configuration from Streamlit secrets."""
    if not HAS_STREAMLIT:
        return {}

    secrets = getattr(st, "secrets", {})
    return {
        "client_id": secrets.get("LINKEDIN_CLIENT_ID", ""),
        "client_secret": secrets.get("LINKEDIN_CLIENT_SECRET", ""),
        "redirect_uri": secrets.get("LINKEDIN_REDIRECT_URI", "http://localhost:8501"),
    }


def is_linkedin_configured() -> bool:
    """Check if LinkedIn OAuth is properly configured."""
    config = get_linkedin_config()
    return bool(config.get("client_id") and config.get("client_secret"))


def get_linkedin_auth_url(state: str) -> str:
    """
    Generate LinkedIn OAuth authorization URL.

    Args:
        state: Random state string for CSRF protection

    Returns:
        LinkedIn authorization URL
    """
    config = get_linkedin_config()

    params = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "state": state,
        "scope": "openid profile email",
    }

    return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"


def exchange_linkedin_code_for_token(code: str) -> Optional[str]:
    """
    Exchange LinkedIn authorization code for access token.

    Args:
        code: Authorization code from LinkedIn callback

    Returns:
        Access token string or None if exchange fails
    """
    config = get_linkedin_config()

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config["redirect_uri"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
    }

    try:
        response = requests.post(LINKEDIN_TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.HTTPError as e:
        if HAS_STREAMLIT:
            error_detail = ""
            try:
                error_detail = response.json()
                st.error(f"LinkedIn token exchange failed: {error_detail.get('error_description', str(e))}")
            except:
                st.error(f"LinkedIn token exchange failed (HTTP {response.status_code}): {str(e)}")
        return None
    except Exception as e:
        if HAS_STREAMLIT:
            st.error(f"Failed to exchange LinkedIn code for token: {str(e)}")
        return None


def get_linkedin_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Fetch LinkedIn user profile information.

    Args:
        access_token: LinkedIn access token

    Returns:
        User info dictionary or None if fetch fails
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.get(LINKEDIN_USER_INFO_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        if HAS_STREAMLIT:
            st.error(f"Failed to fetch LinkedIn user info: {e}")
        return None


def is_linkedin_user_logged_in() -> bool:
    """Check if user is logged in via LinkedIn."""
    if not HAS_STREAMLIT:
        return False

    return (
        'linkedin_authenticated' in st.session_state and
        st.session_state.get('linkedin_authenticated') is True
    )


def linkedin_login() -> str:
    """
    Initiate LinkedIn OAuth login flow.

    Returns:
        LinkedIn authorization URL to redirect to
    """
    if not HAS_STREAMLIT:
        return ""

    if not is_linkedin_configured():
        st.error("LinkedIn OAuth is not configured. Please add LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, and LINKEDIN_REDIRECT_URI to secrets.")
        return ""

    # Generate and store state for CSRF protection
    # Prefix with "linkedin_" so we can identify LinkedIn callbacks without session state
    random_token = secrets.token_urlsafe(32)
    state = f"linkedin_{random_token}"
    st.session_state['linkedin_oauth_state'] = state
    st.session_state['linkedin_login_initiated'] = True

    # Get authorization URL
    auth_url = get_linkedin_auth_url(state)

    return auth_url


def handle_linkedin_callback(code: str, state: str) -> bool:
    """
    Handle LinkedIn OAuth callback.

    Args:
        code: Authorization code from LinkedIn
        state: State parameter for CSRF validation

    Returns:
        True if login successful, False otherwise
    """
    if not HAS_STREAMLIT:
        return False

    # Verify state to prevent CSRF attacks
    stored_state = st.session_state.get('linkedin_oauth_state')

    # If stored_state is None, session was lost during redirect
    # This is common with Streamlit - we'll skip state validation in this case
    # Note: In production, you may want to use a more persistent storage like cookies
    if stored_state and stored_state != state:
        st.error(f"Invalid state parameter. Stored: {stored_state[:10] if stored_state else 'None'}..., Got: {state[:10]}...")
        return False

    # If no stored state, we'll proceed but log a warning
    if not stored_state:
        st.warning("Session state was lost during OAuth redirect. Proceeding without CSRF validation.")

    # Exchange code for access token
    with st.spinner("Exchanging authorization code for access token..."):
        access_token = exchange_linkedin_code_for_token(code)

    if not access_token:
        st.error("Failed to get access token from LinkedIn")
        return False

    # Get user info
    with st.spinner("Fetching your LinkedIn profile..."):
        user_info = get_linkedin_user_info(access_token)

    if not user_info:
        st.error("Failed to get user information from LinkedIn")
        return False

    # Store user info in session state
    st.session_state['linkedin_authenticated'] = True
    st.session_state['linkedin_user_info'] = user_info
    st.session_state['linkedin_access_token'] = access_token
    st.session_state['authenticated_in_session'] = True
    st.session_state['auth_provider'] = 'linkedin'

    # Clear OAuth state
    if 'linkedin_oauth_state' in st.session_state:
        del st.session_state['linkedin_oauth_state']
    if 'linkedin_login_initiated' in st.session_state:
        del st.session_state['linkedin_login_initiated']

    # Debug: Show user info
    st.success(f"✅ Successfully authenticated as {user_info.get('name', user_info.get('email', 'LinkedIn User'))}")

    return True


def linkedin_logout() -> None:
    """Log out LinkedIn user and clear session state."""
    if not HAS_STREAMLIT:
        return

    # Clear all LinkedIn-related session state
    keys_to_clear = [
        'linkedin_authenticated',
        'linkedin_user_info',
        'linkedin_access_token',
        'linkedin_oauth_state',
        'linkedin_login_initiated',
        'linkedin_callback_processed',
        'auth_provider',
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def render_linkedin_login_button(label: str = "Log in with LinkedIn", **button_kwargs: Any) -> bool:
    """Render LinkedIn login button using st.link_button for proper redirect."""
    if not HAS_STREAMLIT:
        return False

    if not is_linkedin_configured():
        st.warning("LinkedIn login is not configured.")
        return False

    # Generate the LinkedIn auth URL
    auth_url = linkedin_login()

    if auth_url:
        # Use st.link_button for external redirect
        st.link_button(label, auth_url, **button_kwargs)
        return True

    return False
