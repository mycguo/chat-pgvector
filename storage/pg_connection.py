"""
PostgreSQL connection management for pgvector operations.
Handles connection pooling and user-specific database access.
"""
import os
import logging
from typing import Optional
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# Set up logger
logger = logging.getLogger(__name__)


# Global connection pool
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def sanitize_connection_string(conn_string: str) -> str:
    """
    Sanitize connection string for logging by hiding password.
    
    Args:
        conn_string: Full connection string
        
    Returns:
        Sanitized connection string with password hidden
    """
    if not conn_string:
        return ""
    
    # Handle postgresql:// URLs
    if "://" in conn_string:
        try:
            # Split on @ to separate credentials from host
            if "@" in conn_string:
                parts = conn_string.split("@", 1)
                cred_part = parts[0]
                rest = parts[1]
                
                # Hide password in credentials part
                if ":" in cred_part:
                    protocol_user = cred_part.rsplit(":", 1)[0]
                    return f"{protocol_user}:***@{rest}"
                return f"{cred_part}:***@{rest}"
        except Exception:
            pass
    
    # Handle key=value format (psycopg2 connection string)
    if "password=" in conn_string.lower():
        import re
        # Replace password=value with password=***
        sanitized = re.sub(
            r'(?i)password\s*=\s*[^\s]+',
            'password=***',
            conn_string
        )
        return sanitized
    
    return conn_string


def get_connection_string() -> str:
    """
    Get PostgreSQL connection string from Streamlit secrets or environment variables.
    
    Returns:
        Connection string for psycopg2
        
    Configuration (in order of precedence):
        1. Streamlit secrets: st.secrets["NEON_DATABASE_URL"] (preferred for Streamlit apps)
        2. Environment variable: NEON_DATABASE_URL (for scripts/non-Streamlit)
        3. Legacy support: DATABASE_URL (for backward compatibility)
        4. Individual components from Streamlit secrets or environment variables:
           - POSTGRES_HOST (default: localhost - only for local dev)
           - POSTGRES_PORT (default: 5432)
           - POSTGRES_DB (default: chat_pgvector)
           - POSTGRES_USER (default: postgres)
           - POSTGRES_PASSWORD (required if NEON_DATABASE_URL not set)
    
    Note: This application uses Neon.tech (serverless PostgreSQL) as the primary database.
    Set NEON_DATABASE_URL in Streamlit secrets or environment variables with your Neon connection string.
    """
    # Try Streamlit secrets first (preferred for Streamlit apps)
    database_url = None
    source = None
    if HAS_STREAMLIT:
        try:
            # Try accessing secrets - st.secrets behaves like a dict
            if hasattr(st, 'secrets') and st.secrets:
                database_url = st.secrets.get("NEON_DATABASE_URL")
                if database_url:
                    source = "Streamlit secrets (NEON_DATABASE_URL)"
        except (AttributeError, KeyError, TypeError, FileNotFoundError):
            # Streamlit secrets not available or NEON_DATABASE_URL not in secrets
            pass
    
    # Fall back to environment variable (for scripts/non-Streamlit environments)
    if not database_url:
        database_url = os.getenv("NEON_DATABASE_URL")
        if database_url:
            source = "Environment variable (NEON_DATABASE_URL)"
    
    # Legacy support: check DATABASE_URL for backward compatibility
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            source = "Environment variable (DATABASE_URL - legacy)"
    
    if database_url:
        # Log connection source and sanitized URL (hide password)
        sanitized_url = sanitize_connection_string(database_url)
        logger.info(f"Using database connection from: {source}")
        logger.debug(f"Connection string: {sanitized_url}")
        return database_url
    
    # Build from individual components
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "chat_pgvector")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")
    
    # Log that we're using individual components
    logger.info(f"Using database connection from: Individual components (POSTGRES_HOST={host}, POSTGRES_PORT={port}, POSTGRES_DB={database}, POSTGRES_USER={user})")
    
    # For local PostgreSQL, password may not be required (peer authentication)
    # Only require password if explicitly set or if not using default localhost
    if not password and host == "localhost":
        # Try connection without password (peer auth)
        conn_string = f"host={host} port={port} dbname={database} user={user}"
        logger.debug(f"Connection string: {conn_string}")
        return conn_string
    elif not password:
        raise ValueError(
            "PostgreSQL password not found. Set POSTGRES_PASSWORD or NEON_DATABASE_URL environment variable."
        )
    
    conn_string = f"host={host} port={port} dbname={database} user={user} password={password}"
    sanitized = sanitize_connection_string(conn_string)
    logger.debug(f"Connection string: {sanitized}")
    return conn_string


def get_connection_pool() -> pool.ThreadedConnectionPool:
    """
    Get or create the global connection pool.
    
    Returns:
        ThreadedConnectionPool instance
    """
    global _connection_pool
    
    if _connection_pool is None:
        try:
            conn_string = get_connection_string()
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=conn_string
            )
        except Exception as e:
            raise ConnectionError(f"Failed to create PostgreSQL connection pool: {e}")
    
    return _connection_pool


@contextmanager
def get_connection():
    """
    Context manager for getting a database connection from the pool.
    
    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    pool = get_connection_pool()
    conn = None
    try:
        conn = pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            pool.putconn(conn)


def close_connection_pool():
    """Close the global connection pool."""
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None


def test_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


# Cache to track if extension check has been done
_extension_checked = False

def ensure_pgvector_extension():
    """
    Ensure pgvector extension is installed in the database.
    Raises exception if extension cannot be created.
    Uses caching to avoid repeated checks.
    """
    global _extension_checked
    
    # Skip if already checked (reduces log noise)
    if _extension_checked:
        return
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Check if extension exists
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            if not cursor.fetchone():
                # Create extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                conn.commit()
                print("pgvector extension created successfully")
            # Mark as checked (don't print if it already exists to reduce noise)
            _extension_checked = True
    except Exception as e:
        raise RuntimeError(f"Failed to ensure pgvector extension: {e}")

