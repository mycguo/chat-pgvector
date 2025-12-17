"""
Utility functions for user management and user-specific storage paths.
"""
import hashlib
import re
import sys

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

def _log(message):
    """Log message to console for debugging user ID issues."""
    print(f"[USER_UTILS] {message}", file=sys.stderr, flush=True)


def get_user_id() -> str:
    """
    Get a unique user identifier from Streamlit user object.

    Returns:
        A sanitized user ID suitable for use in file paths and collection names.
        Uses email if available, otherwise falls back to name or generates a hash.
    """
    _log("get_user_id() called")

    if not HAS_STREAMLIT:
        # For non-Streamlit contexts (e.g., tests), return a default
        _log("No Streamlit available, returning 'default_user'")
        return "default_user"

    # Safely check if user is logged in
    try:
        has_user_attr = hasattr(st, 'user')
        user_is_none = st.user is None if has_user_attr else True
        _log(f"User check: hasattr(st, 'user')={has_user_attr}, st.user is None={user_is_none}")

        if has_user_attr and not user_is_none and hasattr(st.user, 'is_logged_in'):
            is_logged_in = st.user.is_logged_in
            _log(f"st.user.is_logged_in={is_logged_in}")
            if not is_logged_in:
                _log("User is not logged in, raising ValueError")
                raise ValueError("User is not logged in")
    except (AttributeError, KeyError) as e:
        # If is_logged_in doesn't exist, continue (for Community Cloud compatibility)
        _log(f"Exception checking login status: {type(e).__name__}: {e} (continuing)")
        pass

    # Try to get user identifier safely
    user_identifier = None
    try:
        has_user_attr = hasattr(st, 'user')
        user_is_none = st.user is None if has_user_attr else True
        _log(f"Getting user identifier: hasattr={has_user_attr}, is_none={user_is_none}")

        if has_user_attr and st.user is not None:
            _log(f"st.user type: {type(st.user)}")
            _log(f"st.user attributes: {dir(st.user) if hasattr(st.user, '__dir__') else 'N/A'}")

            if hasattr(st.user, 'email') and st.user.email:
                user_identifier = st.user.email
                _log(f"Got user identifier from email: {user_identifier}")
            elif hasattr(st.user, 'name') and st.user.name:
                user_identifier = st.user.name
                _log(f"Got user identifier from name: {user_identifier}")
            elif hasattr(st.user, 'id') and st.user.id:
                user_identifier = str(st.user.id)
                _log(f"Got user identifier from id: {user_identifier}")
            else:
                # Fallback: generate hash from user object
                _log("Trying to generate hash from user object")
                try:
                    if hasattr(st.user, '__dict__') and st.user.__dict__ is not None:
                        user_str = str(st.user.__dict__)
                        user_identifier = hashlib.md5(user_str.encode()).hexdigest()
                        _log(f"Generated hash identifier: {user_identifier}")
                except Exception as e:
                    _log(f"Failed to generate hash: {type(e).__name__}: {e}")
                    pass
        else:
            _log("st.user is None or doesn't exist")
    except (AttributeError, KeyError, TypeError) as e:
        _log(f"ERROR getting user identifier: {type(e).__name__}: {e}")
        import traceback
        _log(f"Traceback:\n{traceback.format_exc()}")
        pass

    # If we couldn't get a user identifier, use session-based or default
    if not user_identifier:
        _log("No user identifier found, trying session_state fallback")
        # Try to use session state as fallback
        has_session_state = hasattr(st, 'session_state')
        _log(f"hasattr(st, 'session_state')={has_session_state}")

        if has_session_state and 'user_id' in st.session_state:
            user_identifier = st.session_state['user_id']
            _log(f"Got user identifier from session_state: {user_identifier}")
        else:
            # Final fallback: use a default user ID
            user_identifier = "default_user"
            _log(f"Using fallback: {user_identifier}")

    # Sanitize the identifier for use in file paths and collection names
    _log(f"Sanitizing user identifier: {user_identifier}")
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', user_identifier)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')

    _log(f"Returning sanitized user_id: {sanitized}")
    return sanitized


def get_user_data_dir(base_dir: str, user_id: str = None) -> str:
    """
    Get user-specific data directory path.
    
    Args:
        base_dir: Base directory name (e.g., "job_search_data")
        user_id: Optional user ID. If None, will try to get from Streamlit.
    
    Returns:
        Path to user-specific data directory
    """
    if user_id is None:
        try:
            user_id = get_user_id()
        except (ValueError, AttributeError):
            # Fallback for non-logged-in contexts
            user_id = "default_user"
    
    return f"./user_data/{user_id}/{base_dir}"


def get_user_vector_store_path(collection_name: str = "personal_assistant", user_id: str = None) -> str:
    """
    Get user-specific vector store path.
    
    Args:
        collection_name: Base collection name
        user_id: Optional user ID. If None, will try to get from Streamlit.
    
    Returns:
        Path to user-specific vector store
    """
    if user_id is None:
        try:
            user_id = get_user_id()
        except (ValueError, AttributeError):
            # Fallback for non-logged-in contexts
            user_id = "default_user"
    
    return f"./user_data/{user_id}/vector_store_{collection_name}"


def get_user_collection_name(base_name: str = "personal_assistant", user_id: str = None) -> str:
    """
    Get user-specific collection name for Milvus.
    
    Args:
        base_name: Base collection name
        user_id: Optional user ID. If None, will try to get from Streamlit.
    
    Returns:
        User-specific collection name
    """
    if user_id is None:
        try:
            user_id = get_user_id()
        except (ValueError, AttributeError):
            # Fallback for non-logged-in contexts
            user_id = "default_user"
    
    # Milvus collection names can contain alphanumeric and underscores
    sanitized_user_id = re.sub(r'[^a-zA-Z0-9_]', '_', user_id)
    sanitized_user_id = re.sub(r'_+', '_', sanitized_user_id).strip('_')
    
    return f"{base_name}_{sanitized_user_id}"

