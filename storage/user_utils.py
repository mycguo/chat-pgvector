"""
Utility functions for user management and user-specific storage paths.
"""
import hashlib
import re

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


def sanitize_user_id(user_identifier: str) -> str:
    """
    Sanitize the identifier for use in file paths and collection names.
    Replace invalid characters with underscores.
    """
    if not user_identifier:
        return "default_user"
        
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', user_identifier)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


def get_user_id() -> str:
    """
    Get a unique user identifier from Streamlit user object or LinkedIn session.

    Returns:
        A sanitized user ID suitable for use in file paths and collection names.
        Uses email if available, otherwise falls back to name or generates a hash.
        Supports both Google OAuth (via Streamlit) and LinkedIn OAuth.
    """
    if not HAS_STREAMLIT:
        # For non-Streamlit contexts (e.g., tests), return a default
        return "default_user"

    # CRITICAL: Check session state first for consistency
    # Once we determine a user_id, we cache it in session to ensure consistency
    # throughout the session (prevents mismatches between add/retrieve operations)
    if hasattr(st, 'session_state') and 'cached_user_id' in st.session_state:
        return st.session_state['cached_user_id']

    # Check if user is logged in via LinkedIn
    user_identifier = None
    if hasattr(st, 'session_state') and st.session_state.get('linkedin_authenticated'):
        linkedin_user_info = st.session_state.get('linkedin_user_info', {})
        # Keep LinkedIn data separate from Google by namespacing the identifier
        if linkedin_user_info.get('email'):
            user_identifier = f"linkedin_{linkedin_user_info['email']}"
        elif linkedin_user_info.get('sub'):  # OpenID Connect subject identifier
            user_identifier = f"linkedin_{linkedin_user_info['sub']}"
        elif linkedin_user_info.get('name'):
            user_identifier = f"linkedin_{linkedin_user_info['name']}"

    # If not LinkedIn, try Google OAuth via Streamlit
    if not user_identifier:
        # Safely check if user is logged in
        try:
            if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in'):
                if not st.user.is_logged_in:
                    raise ValueError("User is not logged in")
        except (AttributeError, KeyError):
            # If is_logged_in doesn't exist, continue (for Community Cloud compatibility)
            pass

        # Try to get user identifier safely
        try:
            if hasattr(st, 'user'):
                if hasattr(st.user, 'email') and st.user.email:
                    user_identifier = f"google_{st.user.email}"
                elif hasattr(st.user, 'name') and st.user.name:
                    user_identifier = f"google_{st.user.name}"
                elif hasattr(st.user, 'id') and st.user.id:
                    user_identifier = f"google_{str(st.user.id)}"
                else:
                    # Fallback: generate hash from user object
                    try:
                        user_str = str(st.user.__dict__)
                        user_identifier = f"google_{hashlib.md5(user_str.encode()).hexdigest()}"
                    except:
                        pass
        except (AttributeError, KeyError):
            pass

    # If we couldn't get a user identifier, use session-based or default
    if not user_identifier:
        # Try to use session state as fallback
        if hasattr(st, 'session_state') and 'user_id' in st.session_state:
            user_identifier = st.session_state['user_id']
        else:
            # Final fallback: use a default user ID
            user_identifier = "default_user"

    # Sanitize and return
    return sanitize_user_id(user_identifier)

    # Cache in session state for consistency
    if hasattr(st, 'session_state'):
        st.session_state['cached_user_id'] = sanitized

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
