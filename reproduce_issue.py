import sys
import os
import time

# Add current directory to path
sys.path.insert(0, '.')

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

try:
    import sklearn
    print(f"✅ sklearn imported successfully. Version: {sklearn.__version__}")
    from sklearn.decomposition import PCA
    print("✅ PCA imported successfully")
except ImportError as e:
    print(f"❌ Failed to import sklearn: {e}")

try:
    import psycopg2
    print(f"✅ psycopg2 imported successfully. Version: {psycopg2.__version__}")
except ImportError as e:
    print(f"❌ Failed to import psycopg2: {e}")

# Test DB connection
try:
    from storage.pg_connection import get_connection
    print("Attempting to connect to database...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            print("✅ Database connection successful (SELECT 1)")
            
            # Check pgvector extension
            cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            if cur.fetchone():
                print("✅ pgvector extension exists")
            else:
                print("⚠️ pgvector extension NOT found")
                
            # Check table dimensions
            cur.execute("""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'vector_documents'::regclass 
                AND attname = 'embedding'
            """)
            res = cur.fetchone()
            if res:
                print(f"ℹ️ Current vector_documents embedding dimension: {res[0]}")
            else:
                print("ℹ️ vector_documents table or embedding column not found")

except Exception as e:
    print(f"❌ Database connection failed: {e}")

# Test Vector Store (Mocking embedding to avoid API calls if possible, or using real one)
try:
    print("\nTesting PgVectorStore initialization...")
    from storage.pg_vector_store import PgVectorStore
    
    # We need to mock the embedding class to avoid needing API keys for this simple test
    # or we can just try to instantiate it if env vars are set.
    # Let's try to instantiate it.
    
    store = PgVectorStore(collection_name="test_debug")
    print("✅ PgVectorStore initialized")
    
    # Check if sklearn is detected in the class
    from storage.pg_vector_store import HAS_SKLEARN
    print(f"PgVectorStore.HAS_SKLEARN = {HAS_SKLEARN}")

except Exception as e:
    print(f"❌ PgVectorStore initialization failed: {e}")
