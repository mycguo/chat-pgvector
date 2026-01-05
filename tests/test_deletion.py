
import os
import sys
import time

# Add current directory to path
sys.path.insert(0, '.')

# Load .env manually
try:
    with open('.env') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except FileNotFoundError:
    pass

# Load from secrets.toml if not in env
if "GOOGLE_API_KEY" not in os.environ:
    try:
        import toml
        with open('.streamlit/secrets.toml') as f:
            secrets = toml.load(f)
            if "GOOGLE_API_KEY" in secrets:
                os.environ["GOOGLE_API_KEY"] = secrets["GOOGLE_API_KEY"]
    except (FileNotFoundError, ImportError):
        pass

if "GOOGLE_API_KEY" not in os.environ:
    print("GOOGLE_API_KEY not found")
    exit(1)

try:
    from storage.pg_vector_store import PgVectorStore
    
    store = PgVectorStore(collection_name="test_deletion")
    
    # 1. Add a test document
    print("Adding test document...")
    filename = "test_doc_to_delete.txt"
    text = "This is a test document that should be deleted."
    metadata = {"source": filename, "filename": filename}
    
    store.add_texts([text], metadatas=[metadata])
    
    # 2. List sources
    print("Listing sources...")
    sources = store.list_sources()
    print(f"Sources: {sources}")
    
    found = False
    for s in sources:
        if s['source'] == filename:
            found = True
            break
    
    if not found:
        print("FAILURE: Test document not found in list")
        exit(1)
        
    # 3. Delete source
    print(f"Deleting source: {filename}...")
    count = store.delete_by_source(filename)
    print(f"Deleted {count} chunks")
    
    # 4. Verify deletion
    sources_after = store.list_sources()
    print(f"Sources after deletion: {sources_after}")
    
    found_after = False
    for s in sources_after:
        if s['source'] == filename:
            found_after = True
            break
            
    if found_after:
        print("FAILURE: Test document still exists after deletion")
        exit(1)
    else:
        print("SUCCESS: Document deleted successfully")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
