#!/usr/bin/env python3
"""
Test PostgreSQL connection for the chat-pgvector application.
"""
import os
import sys
from storage.pg_connection import (
    test_connection,
    get_connection_string,
    sanitize_connection_string,
    ensure_pgvector_extension,
    get_connection
)

def main():
    print("=" * 70)
    print("PostgreSQL Connection Test")
    print("=" * 70)

    # Check for connection configuration
    print("\n1. Checking configuration...")

    # Check environment variables
    has_neon_url = bool(os.getenv("NEON_DATABASE_URL"))
    has_database_url = bool(os.getenv("DATABASE_URL"))
    has_postgres_password = bool(os.getenv("POSTGRES_PASSWORD"))

    print(f"   NEON_DATABASE_URL: {'✓ Set' if has_neon_url else '✗ Not set'}")
    print(f"   DATABASE_URL: {'✓ Set' if has_database_url else '✗ Not set'}")
    print(f"   POSTGRES_PASSWORD: {'✓ Set' if has_postgres_password else '✗ Not set'}")

    # Try to get connection string
    print("\n2. Getting connection string...")
    try:
        conn_string = get_connection_string()
        sanitized = sanitize_connection_string(conn_string)
        print(f"   ✓ Connection string obtained")
        print(f"   → {sanitized}")
    except Exception as e:
        print(f"   ✗ Failed to get connection string: {e}")
        return 1

    # Test basic connection
    print("\n3. Testing database connection...")
    try:
        if test_connection():
            print("   ✓ Connection successful!")
        else:
            print("   ✗ Connection failed (no exception but returned False)")
            return 1
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return 1

    # Test pgvector extension
    print("\n4. Checking pgvector extension...")
    try:
        ensure_pgvector_extension()
        print("   ✓ pgvector extension is available")
    except Exception as e:
        print(f"   ✗ pgvector extension check failed: {e}")
        print("   Note: Make sure pgvector is installed on your PostgreSQL server")
        return 1

    # Query some database info
    print("\n5. Querying database information...")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get PostgreSQL version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"   PostgreSQL version: {version.split(',')[0]}")

            # Get current database
            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()[0]
            print(f"   Current database: {db_name}")

            # Get current user
            cursor.execute("SELECT current_user")
            user = cursor.fetchone()[0]
            print(f"   Current user: {user}")

            # Check if vector_documents table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'vector_documents'
                )
            """)
            table_exists = cursor.fetchone()[0]
            print(f"   vector_documents table: {'✓ Exists' if table_exists else '✗ Does not exist'}")

            # If table exists, get row count
            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM vector_documents")
                count = cursor.fetchone()[0]
                print(f"   Document count: {count}")

    except Exception as e:
        print(f"   ✗ Failed to query database info: {e}")
        return 1

    print("\n" + "=" * 70)
    print("✓ All tests passed!")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
