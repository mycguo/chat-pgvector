"""
Encryption utilities for user data storage.

Uses Fernet symmetric encryption from the cryptography library.
Each user gets a unique encryption key derived from a master key + user ID.
"""
import os
import base64
import hashlib
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cryptography.fernet import Fernet

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None  # For type hints when cryptography is not available

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    from storage.user_utils import get_user_id
    HAS_USER_UTILS = True
except ImportError:
    HAS_USER_UTILS = False


def get_master_key() -> Optional[bytes]:
    """
    Get master encryption key from Streamlit secrets or environment variable.
    
    Returns:
        Master key bytes, or None if encryption is not configured
    """
    master_key_str = None
    
    if HAS_STREAMLIT:
        try:
            master_key_str = st.secrets.get("ENCRYPTION_MASTER_KEY", None)
        except (AttributeError, KeyError):
            pass
    
    if not master_key_str:
        master_key_str = os.getenv("ENCRYPTION_MASTER_KEY", None)
    
    if master_key_str:
        # If it's a base64-encoded key, decode it
        try:
            return base64.urlsafe_b64decode(master_key_str.encode())
        except Exception:
            # If not base64, use it as-is (will be hashed)
            return master_key_str.encode()
    
    return None


def derive_user_key(user_id: str, master_key: Optional[bytes] = None) -> bytes:
    """
    Derive a user-specific encryption key from master key and user ID.
    
    Args:
        user_id: User identifier
        master_key: Optional master key (if None, will try to get from config)
    
    Returns:
        Fernet-compatible encryption key (32 bytes, base64-encoded)
    """
    if master_key is None:
        master_key = get_master_key()
    
    if master_key is None:
        # Generate a default key from user_id (less secure, but works)
        # In production, always set ENCRYPTION_MASTER_KEY
        key_material = hashlib.sha256(f"default_key_{user_id}".encode()).digest()
    else:
        # Use PBKDF2 to derive key from master key + user_id
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=user_id.encode(),
            iterations=100000,
        )
        key_material = kdf.derive(master_key)
    
    # Convert to Fernet-compatible key (base64-encoded)
    return base64.urlsafe_b64encode(key_material)


def get_user_fernet(user_id: str = None) -> Optional[Fernet]:
    """
    Get Fernet cipher instance for a user.
    
    Args:
        user_id: Optional user ID (if None, will try to get from Streamlit)
    
    Returns:
        Fernet instance, or None if encryption is not available
    """
    if not HAS_CRYPTOGRAPHY:
        return None
    
    if user_id is None and HAS_USER_UTILS:
        try:
            user_id = get_user_id()
        except (ValueError, AttributeError):
            user_id = "default_user"
    
    if user_id is None:
        user_id = "default_user"
    
    try:
        user_key = derive_user_key(user_id)
        return Fernet(user_key)
    except Exception as e:
        print(f"Error creating Fernet cipher: {e}")
        return None


def encrypt_data(data: bytes, user_id: str = None) -> bytes:
    """
    Encrypt data using user-specific key.
    
    Args:
        data: Data to encrypt
        user_id: Optional user ID
    
    Returns:
        Encrypted data, or original data if encryption fails
    """
    fernet = get_user_fernet(user_id)
    if fernet is None:
        return data
    
    try:
        return fernet.encrypt(data)
    except Exception as e:
        print(f"Encryption error: {e}")
        return data


def decrypt_data(encrypted_data: bytes, user_id: str = None) -> bytes:
    """
    Decrypt data using user-specific key.
    
    Args:
        encrypted_data: Encrypted data
        user_id: Optional user ID
    
    Returns:
        Decrypted data, or original data if decryption fails
    """
    fernet = get_user_fernet(user_id)
    if fernet is None:
        return encrypted_data
    
    try:
        return fernet.decrypt(encrypted_data)
    except Exception as e:
        print(f"Decryption error: {e}")
        return encrypted_data


def is_encryption_enabled() -> bool:
    """
    Check if encryption is enabled (master key is configured).
    
    Returns:
        True if encryption is available and configured
    """
    if not HAS_CRYPTOGRAPHY:
        return False
    
    master_key = get_master_key()
    return master_key is not None


def generate_master_key() -> str:
    """
    Generate a new master encryption key.
    
    Returns:
        Base64-encoded master key (safe to store in secrets)
    """
    if not HAS_CRYPTOGRAPHY:
        raise ImportError("cryptography library is not installed")
    
    key = Fernet.generate_key()
    return key.decode()  # Already base64-encoded

