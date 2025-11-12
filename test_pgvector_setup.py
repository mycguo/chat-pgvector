#!/usr/bin/env python3
"""
Test script to verify PostgreSQL + pgvector setup.
Run this after setting up PostgreSQL to verify everything works.
"""
import os
import sys

# Load Streamlit secrets if available
try:
    import streamlit as st
    # Try to access secrets (will work if running in Streamlit context or secrets.toml exists)
    try:
        if hasattr(st, 'secrets'):
            # Set environment variables from Streamlit secrets
            if 'GOOGLE_API_KEY' in st.secrets:
                os.environ['GOOGLE_API_KEY'] = st.secrets['GOOGLE_API_KEY']
            if 'GENAI_API_KEY' in st.secrets:
                os.environ['GENAI_API_KEY'] = st.secrets['GENAI_API_KEY']
            if 'GEMINI_API_KEY' in st.secrets:
                os.environ['GENAI_API_KEY'] = st.secrets['GEMINI_API_KEY']
    except:
        pass
except ImportError:
    pass

# Also try loading from secrets.toml directly
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python < 3.11
    except ImportError:
        tomllib = None

if tomllib:
    secrets_path = os.path.expanduser('~/.streamlit/secrets.toml')
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, 'rb') as f:
                secrets = tomllib.load(f)
                if 'GOOGLE_API_KEY' in secrets:
                    os.environ['GOOGLE_API_KEY'] = str(secrets['GOOGLE_API_KEY'])
                if 'GENAI_API_KEY' in secrets:
                    os.environ['GENAI_API_KEY'] = str(secrets['GENAI_API_KEY'])
                if 'GEMINI_API_KEY' in secrets:
                    os.environ['GENAI_API_KEY'] = str(secrets['GEMINI_API_KEY'])
        except Exception as e:
            print(f"Note: Could not load secrets.toml: {e}")

def test_imports():
    """Test that required packages are installed."""
    print("Testing imports...")
    try:
        import psycopg2
        print("✅ psycopg2 imported successfully")
    except ImportError as e:
        print(f"❌ psycopg2 not found: {e}")
        print("   Install with: pip install psycopg2-binary")
        return False
    return True

def test_connection():
    """Test database connection."""
    print("\nTesting database connection...")
    try:
        from storage.pg_connection import test_connection, get_connection_string
        
        # Show connection string (without password)
        conn_str = get_connection_string()
        # Mask password in output
        if "password=" in conn_str:
            masked = conn_str.split("password=")[0] + "password=***"
            print(f"   Connection string: {masked}")
        else:
            print(f"   Connection string: {conn_str}")
        
        if test_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            print("   Check your environment variables:")
            print("   - DATABASE_URL or")
            print("   - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
            return False
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def test_pgvector_extension():
    """Test pgvector extension."""
    print("\nTesting pgvector extension...")
    try:
        from storage.pg_connection import ensure_pgvector_extension, get_connection
        
        ensure_pgvector_extension()
        print("✅ pgvector extension is available")
        
        # Verify extension exists
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            result = cursor.fetchone()
            if result:
                print(f"   pgvector version: {result[0]}")
            else:
                print("   ⚠️  Extension not found (but no error)")
        return True
    except Exception as e:
        print(f"❌ pgvector extension error: {e}")
        print("   Make sure pgvector is installed in PostgreSQL")
        return False

def test_table_creation():
    """Test table creation."""
    print("\nTesting table creation...")
    try:
        from storage.pg_vector_store import PgVectorStore
        
        # Create a test store (will auto-create table)
        store = PgVectorStore(
            collection_name="test_collection",
            user_id="test_user"
        )
        print("✅ Table creation successful")
        
        # Check stats
        stats = store.get_collection_stats()
        print(f"   Collection stats: {stats}")
        return True
    except Exception as e:
        print(f"❌ Table creation error: {e}")
        return False

def test_vector_operations():
    """Test vector operations."""
    print("\nTesting vector operations...")
    try:
        from storage.pg_vector_store import PgVectorStore
        
        store = PgVectorStore(
            collection_name="test_collection",
            user_id="test_user"
        )
        
        # Add test documents
        print("   Adding test documents...")
        texts = [
            "This is a test document about Python programming.",
            "This is another document about machine learning.",
            "This document discusses database systems."
        ]
        ids = store.add_texts(texts, metadatas=[
            {"source": "test1"},
            {"source": "test2"},
            {"source": "test3"}
        ])
        print(f"   ✅ Added {len(ids)} documents")
        
        # Test search
        print("   Testing similarity search...")
        results = store.similarity_search("programming language", k=2)
        print(f"   ✅ Found {len(results)} results")
        for i, doc in enumerate(results, 1):
            print(f"      {i}. {doc.page_content[:50]}...")
        
        # Test search with scores
        print("   Testing similarity search with scores...")
        results_with_scores = store.similarity_search_with_score("machine learning", k=2)
        print(f"   ✅ Found {len(results_with_scores)} results with scores")
        for i, (doc, score) in enumerate(results_with_scores, 1):
            print(f"      {i}. Score: {score:.4f} - {doc.page_content[:50]}...")
        
        # Cleanup test data
        print("   Cleaning up test data...")
        store.delete(ids)
        print("   ✅ Cleanup complete")
        
        return True
    except Exception as e:
        print(f"❌ Vector operations error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("PostgreSQL + pgvector Setup Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Connection", test_connection()))
    results.append(("pgvector Extension", test_pgvector_extension()))
    results.append(("Table Creation", test_table_creation()))
    results.append(("Vector Operations", test_vector_operations()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 All tests passed! Your setup is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

