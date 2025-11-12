"""
PostgreSQL connection management for pgvector operations.
Handles connection pooling and user-specific database access.
"""
import os
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


# Global connection pool
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def get_connection_string() -> str:
    """
    Get PostgreSQL connection string from environment variables.
    
    Returns:
        Connection string for psycopg2
        
    Environment Variables:
        DATABASE_URL: Full connection string (preferred)
        Or individual components:
        - POSTGRES_HOST (default: localhost)
        - POSTGRES_PORT (default: 5432)
        - POSTGRES_DB (default: chat_pgvector)
        - POSTGRES_USER (default: postgres)
        - POSTGRES_PASSWORD (required if DATABASE_URL not set)
    """
    # Prefer DATABASE_URL if set
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # Build from individual components
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "chat_pgvector")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")
    
    # For local PostgreSQL, password may not be required (peer authentication)
    # Only require password if explicitly set or if not using default localhost
    if not password and host == "localhost":
        # Try connection without password (peer auth)
        return f"host={host} port={port} dbname={database} user={user}"
    elif not password:
        raise ValueError(
            "PostgreSQL password not found. Set POSTGRES_PASSWORD or DATABASE_URL environment variable."
        )
    
    return f"host={host} port={port} dbname={database} user={user} password={password}"


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


def ensure_pgvector_extension():
    """
    Ensure pgvector extension is installed in the database.
    Raises exception if extension cannot be created.
    """
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
            else:
                print("pgvector extension already exists")
    except Exception as e:
        raise RuntimeError(f"Failed to ensure pgvector extension: {e}")

