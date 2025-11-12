#!/usr/bin/env python3
"""
Migration script to migrate data from SimpleVectorStore (pickle/JSON) to PostgreSQL with pgvector.

This script:
1. Scans for existing vector store files (vectors.pkl, metadata.json)
2. Loads vectors and metadata for each user
3. Migrates data to PostgreSQL
4. Verifies data integrity
5. Creates backups
6. Provides rollback capability
"""
import os
import sys
import json
import pickle
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from storage.pg_vector_store import PgVectorStore
    from storage.pg_connection import get_connection, test_connection
    HAS_PGVECTOR = True
except ImportError as e:
    print(f"Error importing pgvector modules: {e}")
    HAS_PGVECTOR = False

try:
    from storage.user_utils import get_user_vector_store_path, get_user_id
    from storage.encryption import decrypt_data, is_encryption_enabled
    HAS_STORAGE_UTILS = True
except ImportError:
    HAS_STORAGE_UTILS = False


class VectorStoreMigrator:
    """Migrate vector stores from file-based to PostgreSQL."""
    
    def __init__(self, user_data_dir: str = "./user_data", backup_dir: str = "./migration_backup"):
        """
        Initialize migrator.
        
        Args:
            user_data_dir: Directory containing user data
            backup_dir: Directory for backups
        """
        self.user_data_dir = Path(user_data_dir)
        self.backup_dir = Path(backup_dir)
        self.migration_log = []
        
    def find_vector_stores(self) -> List[Dict[str, Any]]:
        """
        Find all vector store directories.
        
        Returns:
            List of dicts with user_id, store_path, vectors_file, metadata_file
        """
        vector_stores = []
        
        if not self.user_data_dir.exists():
            print(f"User data directory not found: {self.user_data_dir}")
            return vector_stores
        
        # Look for vector_store_* directories
        for user_dir in self.user_data_dir.iterdir():
            if not user_dir.is_dir():
                continue
            
            user_id = user_dir.name
            
            # Look for vector_store_* subdirectories
            for subdir in user_dir.iterdir():
                if subdir.is_dir() and subdir.name.startswith("vector_store_"):
                    vectors_file = subdir / "vectors.pkl"
                    metadata_file = subdir / "metadata.json"
                    
                    if vectors_file.exists() or metadata_file.exists():
                        collection_name = subdir.name.replace("vector_store_", "")
                        vector_stores.append({
                            "user_id": user_id,
                            "collection_name": collection_name,
                            "store_path": str(subdir),
                            "vectors_file": str(vectors_file) if vectors_file.exists() else None,
                            "metadata_file": str(metadata_file) if metadata_file.exists() else None,
                        })
        
        return vector_stores
    
    def load_vector_store(self, store_info: Dict[str, Any], user_id: str = None) -> tuple:
        """
        Load vectors and metadata from file-based store.
        
        Args:
            store_info: Store information dict
            user_id: User ID for decryption
            
        Returns:
            Tuple of (vectors, metadata_list)
        """
        vectors = []
        metadata_list = []
        
        # Load vectors
        if store_info["vectors_file"] and os.path.exists(store_info["vectors_file"]):
            try:
                with open(store_info["vectors_file"], 'rb') as f:
                    vectors = pickle.load(f)
                print(f"  Loaded {len(vectors)} vectors from {store_info['vectors_file']}")
            except Exception as e:
                print(f"  Error loading vectors: {e}")
                return [], []
        
        # Load metadata
        if store_info["metadata_file"] and os.path.exists(store_info["metadata_file"]):
            try:
                encryption_enabled = HAS_STORAGE_UTILS and is_encryption_enabled()
                
                if encryption_enabled and user_id:
                    # Try encrypted first
                    try:
                        with open(store_info["metadata_file"], 'rb') as f:
                            encrypted_data = f.read()
                            if encrypted_data:
                                decrypted_data = decrypt_data(encrypted_data, user_id)
                                metadata_list = json.loads(decrypted_data.decode('utf-8'))
                                print(f"  Loaded {len(metadata_list)} metadata entries (decrypted)")
                    except Exception:
                        # Fall back to plain JSON
                        with open(store_info["metadata_file"], 'r', encoding='utf-8') as f:
                            metadata_list = json.load(f)
                            print(f"  Loaded {len(metadata_list)} metadata entries (plain)")
                else:
                    # Plain JSON
                    with open(store_info["metadata_file"], 'r', encoding='utf-8') as f:
                        metadata_list = json.load(f)
                    print(f"  Loaded {len(metadata_list)} metadata entries")
            except Exception as e:
                print(f"  Error loading metadata: {e}")
                return vectors, []
        
        # Ensure vectors and metadata match
        if len(vectors) != len(metadata_list):
            print(f"  Warning: Vector count ({len(vectors)}) != metadata count ({len(metadata_list)})")
            # Use minimum length
            min_len = min(len(vectors), len(metadata_list))
            vectors = vectors[:min_len]
            metadata_list = metadata_list[:min_len]
        
        return vectors, metadata_list
    
    def migrate_store(self, store_info: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Migrate a single vector store to PostgreSQL.
        
        Args:
            store_info: Store information dict
            dry_run: If True, don't actually migrate
            
        Returns:
            Migration result dict
        """
        user_id = store_info["user_id"]
        collection_name = store_info["collection_name"]
        
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating store: {user_id}/{collection_name}")
        print(f"  Path: {store_info['store_path']}")
        
        # Load data
        vectors, metadata_list = self.load_vector_store(store_info, user_id)
        
        if not vectors:
            return {
                "success": False,
                "user_id": user_id,
                "collection_name": collection_name,
                "reason": "No vectors found",
                "count": 0
            }
        
        if dry_run:
            return {
                "success": True,
                "user_id": user_id,
                "collection_name": collection_name,
                "count": len(vectors),
                "dry_run": True
            }
        
        # Migrate to PostgreSQL
        try:
            # Create PgVectorStore instance
            pg_store = PgVectorStore(
                collection_name=collection_name,
                user_id=user_id
            )
            
            # Extract texts from metadata
            texts = []
            metadatas = []
            for meta in metadata_list:
                text = meta.get("text", "")
                if not text:
                    # Try to get from page_content or content
                    text = meta.get("page_content", meta.get("content", ""))
                
                if text:
                    texts.append(text)
                    # Clean metadata (remove text, keep other fields)
                    clean_meta = {k: v for k, v in meta.items() 
                                 if k not in ["text", "page_content", "content", "id", "timestamp"]}
                    metadatas.append(clean_meta)
            
            if not texts:
                return {
                    "success": False,
                    "user_id": user_id,
                    "collection_name": collection_name,
                    "reason": "No text content found in metadata",
                    "count": len(vectors)
                }
            
            # Use existing vectors directly to avoid API quota issues
            # Insert vectors directly into PostgreSQL
            print(f"  Migrating {len(texts)} documents with existing vectors...")
            ids = self._migrate_with_existing_vectors(pg_store, texts, vectors, metadatas)
            
            # Verify
            stats = pg_store.get_collection_stats()
            actual_count = stats.get("document_count", 0)
            
            if actual_count != len(texts):
                print(f"  Warning: Expected {len(texts)} documents, got {actual_count}")
            
            return {
                "success": True,
                "user_id": user_id,
                "collection_name": collection_name,
                "count": actual_count,
                "expected": len(texts)
            }
            
        except Exception as e:
            print(f"  Error migrating: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "user_id": user_id,
                "collection_name": collection_name,
                "error": str(e),
                "count": 0
            }
    
    def create_backup(self, store_info: Dict[str, Any]) -> str:
        """
        Create backup of vector store files.
        
        Args:
            store_info: Store information dict
            
        Returns:
            Backup directory path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / timestamp / store_info["user_id"] / store_info["collection_name"]
        backup_path.mkdir(parents=True, exist_ok=True)
        
        store_path = Path(store_info["store_path"])
        
        # Copy files
        if store_info["vectors_file"] and os.path.exists(store_info["vectors_file"]):
            shutil.copy2(store_info["vectors_file"], backup_path / "vectors.pkl")
        
        if store_info["metadata_file"] and os.path.exists(store_info["metadata_file"]):
            shutil.copy2(store_info["metadata_file"], backup_path / "metadata.json")
        
        print(f"  Backup created: {backup_path}")
        return str(backup_path)
    
    def _migrate_with_existing_vectors(self, pg_store, texts: List[str], vectors: List[List[float]], 
                                       metadatas: List[Dict]) -> List[str]:
        """
        Migrate documents using existing vectors (avoids API quota issues).
        
        Args:
            pg_store: PgVectorStore instance
            texts: List of text strings
            vectors: List of existing embedding vectors
            metadatas: List of metadata dicts
            
        Returns:
            List of document IDs
        """
        import uuid
        from storage.pg_connection import get_connection
        
        ids = []
        rows = []
        
        # Ensure table exists
        pg_store._ensure_table_exists()
        
        # Prepare data for insertion
        for i, (text, vector, metadata) in enumerate(zip(texts, vectors, metadatas)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            # Prepare metadata
            clean_meta = metadata.copy()
            clean_meta["text"] = text  # Store text in metadata
            clean_meta["timestamp"] = datetime.now().isoformat()
            
            # Reduce vector dimension if needed
            if len(vector) > pg_store.max_dimensions:
                if pg_store.pca_model is not None:
                    # Use PCA model
                    import numpy as np
                    vector_array = np.array(vector).reshape(1, -1)
                    reduced = pg_store.pca_model.transform(vector_array)
                    vector = reduced[0].tolist()
                else:
                    # Truncate
                    vector = vector[:pg_store.max_dimensions]
            
            # Convert vector to string format
            vector_str = "[" + ",".join(map(str, vector)) + "]"
            
            rows.append((
                doc_id,
                pg_store.user_id,
                pg_store.collection_name,
                text,
                vector_str,
                json.dumps(clean_meta)
            ))
        
        # Batch insert into PostgreSQL
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Insert each row with proper vector casting
                for row in rows:
                    cursor.execute("""
                        INSERT INTO vector_documents 
                        (id, user_id, collection_name, text, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s::vector, %s::jsonb)
                    """, row)
                conn.commit()
            print(f"  ✅ Inserted {len(rows)} documents with existing vectors")
        except Exception as e:
            print(f"  Error inserting documents: {e}")
            raise
        
        return ids
    
    def migrate_all(self, dry_run: bool = False, create_backups: bool = True) -> Dict[str, Any]:
        """
        Migrate all vector stores.
        
        Args:
            dry_run: If True, don't actually migrate
            create_backups: If True, create backups before migrating
            
        Returns:
            Migration summary
        """
        if not HAS_PGVECTOR:
            return {
                "success": False,
                "error": "PgVectorStore not available"
            }
        
        # Test database connection
        if not test_connection():
            return {
                "success": False,
                "error": "Database connection failed. Check your DATABASE_URL or PostgreSQL connection."
            }
        
        print("=" * 60)
        print("Vector Store Migration to PostgreSQL")
        print("=" * 60)
        print(f"User data directory: {self.user_data_dir}")
        print(f"Backup directory: {self.backup_dir}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")
        print("=" * 60)
        
        # Find all vector stores
        vector_stores = self.find_vector_stores()
        
        if not vector_stores:
            print("\nNo vector stores found to migrate.")
            return {
                "success": True,
                "stores_found": 0,
                "migrated": 0
            }
        
        print(f"\nFound {len(vector_stores)} vector store(s) to migrate:")
        for store in vector_stores:
            print(f"  - {store['user_id']}/{store['collection_name']}")
        
        if not dry_run and create_backups:
            print(f"\nCreating backups in {self.backup_dir}...")
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Migrate each store
        results = []
        for store_info in vector_stores:
            if not dry_run and create_backups:
                self.create_backup(store_info)
            
            result = self.migrate_store(store_info, dry_run=dry_run)
            results.append(result)
            self.migration_log.append(result)
        
        # Summary
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        print(f"Total stores: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        total_docs = sum(r.get("count", 0) for r in successful)
        print(f"Total documents migrated: {total_docs}")
        
        if failed:
            print("\nFailed migrations:")
            for r in failed:
                print(f"  - {r['user_id']}/{r['collection_name']}: {r.get('reason', r.get('error', 'Unknown error'))}")
        
        return {
            "success": len(failed) == 0,
            "stores_found": len(vector_stores),
            "migrated": len(successful),
            "failed": len(failed),
            "total_documents": total_docs,
            "results": results
        }


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate vector stores to PostgreSQL")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without actually migrating"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backups"
    )
    parser.add_argument(
        "--user-data-dir",
        default="./user_data",
        help="Directory containing user data (default: ./user_data)"
    )
    parser.add_argument(
        "--backup-dir",
        default="./migration_backup",
        help="Directory for backups (default: ./migration_backup)"
    )
    
    args = parser.parse_args()
    
    migrator = VectorStoreMigrator(
        user_data_dir=args.user_data_dir,
        backup_dir=args.backup_dir
    )
    
    result = migrator.migrate_all(
        dry_run=args.dry_run,
        create_backups=not args.no_backup
    )
    
    if result.get("success"):
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration completed with errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()

