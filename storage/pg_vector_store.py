"""
PostgreSQL-based vector store using pgvector extension.
Replaces SimpleVectorStore with database-backed storage for better scalability.
"""
import os
import json
import uuid
import pickle
import numpy as np
from typing import List, Optional, Dict, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings
try:
    from langchain_core.documents import Document
except ImportError:
    # Fallback for older langchain versions
    from langchain.docstore.document import Document
from datetime import datetime

try:
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

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

try:
    from storage.encryption import is_encryption_enabled
    HAS_ENCRYPTION = True
except ImportError:
    HAS_ENCRYPTION = False

from storage.pg_connection import get_connection, ensure_pgvector_extension


class PgVectorStore:
    """
    PostgreSQL-based vector store using pgvector extension.
    
    Maintains the same interface as SimpleVectorStore for easy migration.
    Stores vectors and metadata in PostgreSQL with user isolation.
    """

    def __init__(
        self,
        collection_name: str = "personal_assistant",
        embedding_model: str = "models/gemini-embedding-001",
        user_id: str = None
    ):
        """
        Initialize PostgreSQL vector store.
        
        Args:
            collection_name: Collection/namespace name (default: "personal_assistant")
            embedding_model: Embedding model name (default: "models/gemini-embedding-001")
            user_id: Optional user ID. If None, will try to get from Streamlit.
        """
        # Get user ID
        if user_id is None:
            if HAS_USER_UTILS:
                try:
                    user_id = get_user_id()
                except (ValueError, AttributeError):
                    user_id = "default_user"
            else:
                user_id = "default_user"
        
        self.user_id = user_id
        self.collection_name = collection_name
        self.embedding = GoogleGenerativeAIEmbeddings(model=embedding_model)
        self._encryption_enabled = HAS_ENCRYPTION and is_encryption_enabled() if HAS_ENCRYPTION else False
        
        # Dimensionality reduction settings
        self.max_dimensions = 2000  # pgvector index limit
        self.pca_model = None
        self.original_dimension = None
        self.reduced_dimension = None
        self.pca_model_path = os.path.join(
            os.path.dirname(__file__),
            f"pca_model_{collection_name}_{user_id}.pkl"
        )
        
        # Ensure pgvector extension exists (silently, only logs on first check)
        try:
            ensure_pgvector_extension()
        except Exception as e:
            print(f"Warning: Could not ensure pgvector extension: {e}")
            print("Make sure PostgreSQL has pgvector extension installed.")
        
        # Ensure table exists (run migration if needed)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Ensure the vector_documents table exists, create if not."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'vector_documents'
                    )
                """)
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    # Get embedding dimension from a test embedding
                    try:
                        test_embedding = self.embedding.embed_query("test")
                        original_dim = len(test_embedding)
                        self.original_dimension = original_dim
                        print(f"Detected embedding dimension: {original_dim}")
                        
                        # Reduce dimension if needed
                        if original_dim > self.max_dimensions:
                            print(f"Reducing dimension from {original_dim} to {self.max_dimensions} for pgvector indexing")
                            embedding_dim = self.max_dimensions
                            self.reduced_dimension = embedding_dim
                            # Initialize PCA model (will be trained on first batch)
                            self._initialize_pca_reduction()
                        else:
                            embedding_dim = original_dim
                            self.reduced_dimension = original_dim
                    except Exception as e:
                        print(f"Warning: Could not detect embedding dimension: {e}")
                        print("Using default dimension 768")
                        embedding_dim = 768
                        self.original_dimension = 768
                        self.reduced_dimension = 768
                    
                    # Create table with reduced dimension
                    self._create_table_with_dimension(cursor, embedding_dim)
                    conn.commit()
                    print(f"Created vector_documents table with dimension {embedding_dim}")
        except Exception as e:
            print(f"Warning: Could not ensure table exists: {e}")
            print("You may need to run the migration manually.")
    
    def _create_table_with_dimension(self, cursor, dimension: int):
        """Create table with specified vector dimension."""
        # Check if column exists and has correct dimension
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'vector_documents' 
                AND column_name = 'embedding'
            )
        """)
        column_exists = cursor.fetchone()[0]
        
        if not column_exists:
            # Create table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS vector_documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    collection_name VARCHAR(255) NOT NULL DEFAULT 'personal_assistant',
                    text TEXT NOT NULL,
                    embedding vector({dimension}) NOT NULL,
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_documents_user_collection 
                ON vector_documents(user_id, collection_name)
            """)
            
            # Create vector index based on dimension
            # Note: pgvector indexes (HNSW/IVFFlat) support up to 2000 dimensions
            if dimension > 2000:
                print(f"Warning: Vector dimension {dimension} exceeds pgvector index limit (2000)")
                print("  Table created without vector index. Queries will use sequential scan.")
                print("  This should not happen if dimensionality reduction is working.")
            elif dimension > 1000:
                # IVFFlat for medium-high dimensional vectors (1000-2000)
                lists = max(10, 100)  # Will adjust based on data size
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_vector_documents_embedding_ivfflat 
                    ON vector_documents USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = {lists})
                """)
                print(f"Created IVFFlat index for {dimension}-dimensional vectors")
            else:
                # HNSW for lower-dimensional vectors (<= 1000)
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_vector_documents_embedding_hnsw 
                    ON vector_documents USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """)
                print(f"Created HNSW index for {dimension}-dimensional vectors")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_documents_metadata_gin 
                ON vector_documents USING gin (metadata)
            """)
            
            # Create trigger function and trigger
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """)
            
            cursor.execute("""
                DROP TRIGGER IF EXISTS update_vector_documents_updated_at ON vector_documents
            """)
            
            cursor.execute("""
                CREATE TRIGGER update_vector_documents_updated_at 
                BEFORE UPDATE ON vector_documents
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
            """)
        else:
            # Check current dimension
            cursor.execute("""
                SELECT udt_name, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'vector_documents' 
                AND column_name = 'embedding'
            """)
            result = cursor.fetchone()
            if result:
                # Extract dimension from vector type (e.g., "vector(768)")
                current_dim = None
                cursor.execute("""
                    SELECT format_type(atttypid, atttypmod) 
                    FROM pg_attribute 
                    WHERE attrelid = 'vector_documents'::regclass 
                    AND attname = 'embedding'
                """)
                type_info = cursor.fetchone()
                if type_info:
                    import re
                    match = re.search(r'vector\((\d+)\)', type_info[0])
                    if match:
                        current_dim = int(match.group(1))
                
                if current_dim and current_dim != dimension:
                    print(f"Warning: Table has dimension {current_dim}, but embeddings are {dimension}")
                    print("You may need to recreate the table or migrate data")

    def _get_migration_sql(self) -> str:
        """Get migration SQL for creating tables."""
        migration_file = os.path.join(
            os.path.dirname(__file__),
            "migrations",
            "001_create_vector_tables.sql"
        )
        if os.path.exists(migration_file):
            with open(migration_file, 'r') as f:
                return f.read()
        else:
            # Fallback: inline SQL
            return """
            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE TABLE IF NOT EXISTS vector_documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                collection_name VARCHAR(255) NOT NULL DEFAULT 'personal_assistant',
                text TEXT NOT NULL,
                embedding vector(768) NOT NULL,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_vector_documents_user_collection 
                ON vector_documents(user_id, collection_name);
            CREATE INDEX IF NOT EXISTS idx_vector_documents_embedding_hnsw 
                ON vector_documents USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            CREATE INDEX IF NOT EXISTS idx_vector_documents_metadata_gin 
                ON vector_documents USING gin (metadata);
            """

    def add_texts(
        self, 
        texts: List[str], 
        metadatas: Optional[List[dict]] = None
    ) -> List[str]:
        """
        Add texts to the vector store.
        
        Args:
            texts: List of text strings to add
            metadatas: Optional list of metadata dictionaries
            
        Returns:
            List of document IDs
        """
        if not texts:
            return []

        # Ensure table exists (will detect dimension if needed)
        self._ensure_table_exists()

        # Generate embeddings
        embeddings = self.embedding.embed_documents(texts)
        
        # Apply dimensionality reduction if needed
        embeddings = self._reduce_dimensions(embeddings, fit_pca=True)

        # Prepare data for insertion
        ids = []
        rows = []
        
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            # Prepare metadata
            metadata = {
                "timestamp": datetime.now().isoformat()
            }
            
            # Add user-provided metadata
            if metadatas and i < len(metadatas):
                metadata.update(metadatas[i])
            
            # Store text in metadata for retrieval (also stored in text column)
            metadata["text"] = text
            
            # Convert embedding to string format for pgvector
            # Format: '[0.1,0.2,0.3,...]' or use psycopg2 adapter
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            
            rows.append((
                doc_id,
                self.user_id,
                self.collection_name,
                text,
                embedding_str,  # Will be cast to vector type in SQL
                json.dumps(metadata)
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
            print(f"Added {len(texts)} documents to PostgreSQL vector store")
        except Exception as e:
            print(f"Error adding texts to vector store: {e}")
            raise
        
        return ids

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of LangChain Document objects
            
        Returns:
            List of document IDs
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts, metadatas)

    def similarity_search(
        self, 
        query: str, 
        k: int = 4
    ) -> List[Document]:
        """
        Perform similarity search.
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of Document objects
        """
        # Generate query embedding
        query_embedding = self.embedding.embed_query(query)
        
        # Reduce dimension if needed
        query_embedding = self._reduce_query_embedding(query_embedding)
        
        query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Use cosine distance operator (<=>) for similarity search
                # Note: <=> returns cosine distance (0 = identical, 2 = opposite)
                # We convert to similarity: similarity = 1 - distance
                cursor.execute("""
                    SELECT 
                        id,
                        text,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM vector_documents
                    WHERE user_id = %s AND collection_name = %s
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT %s
                """, (query_embedding_str, self.user_id, self.collection_name, 
                      query_embedding_str, k))
                
                results = cursor.fetchall()
                
                documents = []
                for row in results:
                    doc_id, text, metadata_json, similarity = row
                    
                    # Parse metadata
                    if isinstance(metadata_json, str):
                        metadata = json.loads(metadata_json)
                    else:
                        metadata = metadata_json or {}
                    
                    # Remove internal fields from metadata
                    metadata.pop("text", None)
                    metadata.pop("timestamp", None)
                    
                    # Add similarity score to metadata
                    metadata["similarity"] = float(similarity)
                    
                    documents.append(Document(page_content=text, metadata=metadata))
                
                return documents
        except Exception as e:
            print(f"Error performing similarity search: {e}")
            return []

    def similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4
    ) -> List[tuple]:
        """
        Perform similarity search with scores.
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of tuples (Document, score)
        """
        # Generate query embedding
        query_embedding = self.embedding.embed_query(query)
        
        # Reduce dimension if needed
        query_embedding = self._reduce_query_embedding(query_embedding)
        
        query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        id,
                        text,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM vector_documents
                    WHERE user_id = %s AND collection_name = %s
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT %s
                """, (query_embedding_str, self.user_id, self.collection_name,
                      query_embedding_str, k))
                
                results = cursor.fetchall()
                
                documents_with_scores = []
                for row in results:
                    doc_id, text, metadata_json, similarity = row
                    
                    # Parse metadata
                    if isinstance(metadata_json, str):
                        metadata = json.loads(metadata_json)
                    else:
                        metadata = metadata_json or {}
                    
                    # Remove internal fields
                    metadata.pop("text", None)
                    metadata.pop("timestamp", None)
                    
                    doc = Document(page_content=text, metadata=metadata)
                    score = float(similarity)
                    documents_with_scores.append((doc, score))
                
                return documents_with_scores
        except Exception as e:
            print(f"Error performing similarity search with score: {e}")
            return []

    def delete(self, ids: Optional[List[str]] = None):
        """
        Delete documents by IDs.
        
        Args:
            ids: List of document IDs to delete
        """
        if not ids:
            return

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Delete documents matching IDs and user_id for security
                # Cast string IDs to UUID type
                cursor.execute("""
                    DELETE FROM vector_documents
                    WHERE id = ANY(%s::uuid[]) AND user_id = %s AND collection_name = %s
                """, (ids, self.user_id, self.collection_name))
                conn.commit()
                print(f"Deleted {cursor.rowcount} documents")
        except Exception as e:
            print(f"Error deleting documents: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as document_count,
                        MIN(created_at) as oldest_document,
                        MAX(created_at) as newest_document
                    FROM vector_documents
                    WHERE user_id = %s AND collection_name = %s
                """, (self.user_id, self.collection_name))
                
                result = cursor.fetchone()
                document_count, oldest, newest = result
                
                return {
                    "document_count": document_count,
                    "vector_count": document_count,  # Same as document count
                    "user_id": self.user_id,
                    "collection_name": self.collection_name,
                    "oldest_document": oldest.isoformat() if oldest else None,
                    "newest_document": newest.isoformat() if newest else None,
                    "status": "ready"
                }
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {
                "document_count": 0,
                "vector_count": 0,
                "user_id": self.user_id,
                "collection_name": self.collection_name,
                "status": "error"
            }

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_model: str = "models/gemini-embedding-001",
        metadatas: Optional[List[dict]] = None,
        collection_name: str = "personal_assistant",
        user_id: str = None
    ):
        """
        Create a PgVectorStore from texts.
        
        Args:
            texts: List of text strings
            embedding_model: Embedding model name
            metadatas: Optional metadata dictionaries
            collection_name: Collection name
            user_id: Optional user ID
            
        Returns:
            PgVectorStore instance
        """
        store = cls(
            collection_name=collection_name,
            embedding_model=embedding_model,
            user_id=user_id
        )
        store.add_texts(texts, metadatas)
        return store
    
    def _initialize_pca_reduction(self):
        """Initialize PCA model for dimensionality reduction."""
        if not HAS_SKLEARN:
            print("Warning: sklearn not available. Cannot use PCA reduction.")
            print("  Install with: pip install scikit-learn")
            return
        
        # Try to load existing PCA model
        if os.path.exists(self.pca_model_path):
            try:
                with open(self.pca_model_path, 'rb') as f:
                    self.pca_model = pickle.load(f)
                print(f"Loaded existing PCA model from {self.pca_model_path}")
                return
            except Exception as e:
                print(f"Could not load PCA model: {e}")
        
        # PCA model will be created and trained on first batch of embeddings
        self.pca_model = None
    
    def _reduce_dimensions(self, embeddings: List[List[float]], fit_pca: bool = False) -> List[List[float]]:
        """
        Reduce embedding dimensions if they exceed max_dimensions.
        
        Args:
            embeddings: List of embedding vectors
            fit_pca: If True, fit PCA model on this data (for first batch)
            
        Returns:
            List of reduced-dimension embeddings
        """
        if not embeddings:
            return embeddings
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings)
        original_dim = embeddings_array.shape[1]
        
        # No reduction needed
        if original_dim <= self.max_dimensions:
            return embeddings
        
        # Need reduction
        if not HAS_SKLEARN:
            print(f"Warning: Cannot reduce dimensions (sklearn not available)")
            print(f"  Truncating from {original_dim} to {self.max_dimensions} dimensions")
            # Simple truncation as fallback
            return [list(emb[:self.max_dimensions]) for emb in embeddings]
        
        # Use PCA for reduction
        if fit_pca and self.pca_model is None:
            n_samples = embeddings_array.shape[0]
            # PCA requires at least as many samples as components
            # Use min(n_samples, max_dimensions) components
            n_components = min(n_samples, self.max_dimensions)
            
            if n_samples < self.max_dimensions:
                # Not enough samples yet, use truncation and collect more samples
                print(f"Not enough samples ({n_samples}) for PCA reduction to {self.max_dimensions} dimensions")
                print(f"  Using truncation for now. PCA will be applied when more data is available.")
                # Truncate each embedding to max_dimensions
                return [list(emb[:self.max_dimensions]) for emb in embeddings]
            
            # Fit PCA model on this data
            print(f"Fitting PCA model to reduce from {original_dim} to {self.max_dimensions} dimensions...")
            self.pca_model = PCA(n_components=self.max_dimensions, random_state=42)
            reduced = self.pca_model.fit_transform(embeddings_array)
            
            # Save PCA model for future use
            try:
                os.makedirs(os.path.dirname(self.pca_model_path), exist_ok=True)
                with open(self.pca_model_path, 'wb') as f:
                    pickle.dump(self.pca_model, f)
                print(f"Saved PCA model to {self.pca_model_path}")
            except Exception as e:
                print(f"Warning: Could not save PCA model: {e}")
            
            return reduced.tolist()
        elif self.pca_model is not None:
            # Use existing PCA model
            reduced = self.pca_model.transform(embeddings_array)
            return reduced.tolist()
        else:
            # PCA model not initialized yet, use truncation temporarily
            print(f"Warning: PCA model not ready, truncating from {original_dim} to {self.max_dimensions}")
            return [list(emb[:self.max_dimensions]) for emb in embeddings]
    
    def _reduce_query_embedding(self, embedding: List[float]) -> List[float]:
        """Reduce query embedding dimension to match stored embeddings."""
        if not embedding:
            return embedding
        
        original_dim = len(embedding)
        
        # No reduction needed
        if original_dim <= self.max_dimensions:
            return embedding
        
        # Need reduction
        if self.pca_model is not None:
            # Use PCA model
            embedding_array = np.array(embedding).reshape(1, -1)
            reduced = self.pca_model.transform(embedding_array)
            return reduced[0].tolist()
        elif HAS_SKLEARN:
            # PCA model not available, use truncation
            print(f"Warning: PCA model not available, truncating query embedding")
            return embedding[:self.max_dimensions]
        else:
            # Simple truncation
            return embedding[:self.max_dimensions]

