"""
Test suite to validate Google Gemini models integration.

This test validates:
1. Gemini 2.5 Flash LLM initialization and basic functionality
2. gemini-embedding-001 embeddings generation
3. Vector store integration with new embeddings
4. End-to-end RAG pipeline functionality
"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, Mock
from typing import List


# Skip tests if Google API key is not available
skip_without_api_key = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="Google API key not available"
)


class TestGeminiLLM:
    """Test Gemini 2.5 Flash LLM"""

    @skip_without_api_key
    def test_gemini_flash_initialization(self):
        """Test that Gemini 2.5 Flash model initializes correctly"""
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Initialize the model
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0
        )

        assert model is not None
        assert model.model == "gemini-2.5-flash"
        assert model.temperature == 0.0

    @skip_without_api_key
    def test_gemini_flash_basic_generation(self):
        """Test that Gemini 2.5 Flash can generate text"""
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0
        )

        # Test basic text generation
        response = model.invoke("Say 'test successful' and nothing else")

        assert response is not None
        assert len(response.content) > 0
        print(f"LLM Response: {response.content}")


class TestGeminiEmbeddings:
    """Test gemini-embedding-001 embeddings"""

    @skip_without_api_key
    def test_gemini_embeddings_initialization(self):
        """Test that gemini-embedding-001 initializes correctly"""
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        )

        assert embeddings is not None
        assert embeddings.model == "models/gemini-embedding-001"

    @skip_without_api_key
    def test_gemini_embeddings_single_text(self):
        """Test embedding a single text"""
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        )

        # Generate embedding for a single query
        query = "What is artificial intelligence?"
        embedding = embeddings.embed_query(query)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == 3072  # gemini-embedding-001 uses 3072 dimensions
        assert all(isinstance(x, float) for x in embedding)
        print(f"Embedding dimension: {len(embedding)}")

    @skip_without_api_key
    def test_gemini_embeddings_multiple_documents(self):
        """Test embedding multiple documents"""
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        )

        # Generate embeddings for multiple documents
        documents = [
            "Artificial intelligence is transforming the world.",
            "Machine learning is a subset of AI.",
            "Deep learning uses neural networks."
        ]

        doc_embeddings = embeddings.embed_documents(documents)

        assert doc_embeddings is not None
        assert len(doc_embeddings) == 3
        assert all(len(emb) == 3072 for emb in doc_embeddings)
        print(f"Generated {len(doc_embeddings)} embeddings")


class TestSimpleVectorStore:
    """Test SimpleVectorStore with Google embeddings"""

    @skip_without_api_key
    def test_simple_vector_store_initialization(self):
        """Test SimpleVectorStore initializes with Google embeddings"""
        from simple_vector_store import SimpleVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SimpleVectorStore(
                store_path=tmpdir,
                embedding_model="models/gemini-embedding-001"
            )

            assert store is not None
            assert store.store_path == tmpdir
            assert store.embedding is not None

    @skip_without_api_key
    def test_simple_vector_store_add_texts(self):
        """Test adding texts to SimpleVectorStore"""
        from simple_vector_store import SimpleVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SimpleVectorStore(
                store_path=tmpdir,
                embedding_model="models/gemini-embedding-001"
            )

            # Add some test documents
            texts = [
                "Charles is a software engineer specializing in AI and machine learning.",
                "He has experience with Python, LangChain, and RAG systems.",
                "Charles enjoys building intelligent applications."
            ]

            ids = store.add_texts(texts)

            assert len(ids) == 3
            assert len(store.vectors) == 3
            assert len(store.metadata) == 3
            print(f"Added {len(ids)} documents to vector store")

    @skip_without_api_key
    def test_simple_vector_store_similarity_search(self):
        """Test similarity search with SimpleVectorStore"""
        from simple_vector_store import SimpleVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SimpleVectorStore(
                store_path=tmpdir,
                embedding_model="models/gemini-embedding-001"
            )

            # Add test documents
            texts = [
                "Charles is a software engineer specializing in AI and machine learning.",
                "He has experience with Python, LangChain, and RAG systems.",
                "Charles enjoys building intelligent applications.",
                "The weather today is sunny and warm.",
                "Pizza is a popular Italian dish."
            ]

            store.add_texts(texts)

            # Search for relevant documents
            query = "What does Charles do?"
            results = store.similarity_search(query, k=3)

            assert len(results) == 3
            assert all(hasattr(doc, 'page_content') for doc in results)

            # The first result should be about Charles being a software engineer
            assert "Charles" in results[0].page_content
            print(f"Top result: {results[0].page_content}")

    @skip_without_api_key
    def test_simple_vector_store_persistence(self):
        """Test that SimpleVectorStore persists data correctly"""
        from simple_vector_store import SimpleVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and populate store
            store1 = SimpleVectorStore(
                store_path=tmpdir,
                embedding_model="models/gemini-embedding-001"
            )

            texts = ["Test document for persistence"]
            store1.add_texts(texts)

            # Load the same store in a new instance
            store2 = SimpleVectorStore(
                store_path=tmpdir,
                embedding_model="models/gemini-embedding-001"
            )

            assert len(store2.vectors) == 1
            assert len(store2.metadata) == 1
            assert store2.metadata[0]['text'] == texts[0]
            print("Persistence test passed")


class TestRAGPipeline:
    """Test end-to-end RAG pipeline with Google models"""

    @skip_without_api_key
    def test_rag_chain_initialization(self):
        """Test that RAG chain initializes with Google models"""
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain.prompts import PromptTemplate
        from langchain.chains.combine_documents import create_stuff_documents_chain

        # Create model
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0
        )

        # Create prompt
        prompt_template = """
        Answer the questions based on local knowledge base honestly

        Context:\n {context} \n
        Questions: \n {questions} \n

        Answers:
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "questions"],
            output_variables=["answers"]
        )

        # Create chain
        chain = create_stuff_documents_chain(
            llm=model,
            prompt=prompt,
            document_variable_name="context"
        )

        assert chain is not None
        print("RAG chain initialized successfully")

    @skip_without_api_key
    def test_rag_pipeline_end_to_end(self):
        """Test complete RAG pipeline from document ingestion to query"""
        from simple_vector_store import SimpleVectorStore
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain.prompts import PromptTemplate
        from langchain.chains.combine_documents import create_stuff_documents_chain

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create vector store and add documents
            store = SimpleVectorStore(
                store_path=tmpdir,
                embedding_model="models/gemini-embedding-001"
            )

            knowledge_base = [
                "Charles is a software engineer who specializes in artificial intelligence and machine learning.",
                "Charles has 5 years of experience building RAG systems using LangChain and Python.",
                "Charles's favorite programming languages are Python and JavaScript.",
                "Charles enjoys working on projects that combine AI with practical applications."
            ]

            store.add_texts(knowledge_base)

            # 2. Query the vector store
            query = "What does Charles specialize in?"
            relevant_docs = store.similarity_search(query, k=2)

            assert len(relevant_docs) > 0
            print(f"Found {len(relevant_docs)} relevant documents")

            # 3. Create LLM and chain
            model = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.0
            )

            prompt_template = """
            Answer the questions based on the provided context honestly.

            Context:\n {context} \n
            Questions: \n {questions} \n

            Answers:
            """

            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "questions"],
                output_variables=["answers"]
            )

            chain = create_stuff_documents_chain(
                llm=model,
                prompt=prompt,
                document_variable_name="context"
            )

            # 4. Get response
            response = chain.invoke({
                "context": relevant_docs,
                "questions": query
            })

            assert response is not None
            assert len(response) > 0
            assert "artificial intelligence" in response.lower() or "AI" in response or "machine learning" in response.lower()
            print(f"RAG Response: {response}")


class TestModelCompatibility:
    """Test backward compatibility and edge cases"""

    def test_simple_vector_store_default_model(self):
        """Test that SimpleVectorStore uses correct default model"""
        from simple_vector_store import SimpleVectorStore

        # Mock the embeddings to avoid API call
        with patch('simple_vector_store.GoogleGenerativeAIEmbeddings') as mock_embeddings:
            mock_instance = Mock()
            mock_embeddings.return_value = mock_instance

            with tempfile.TemporaryDirectory() as tmpdir:
                store = SimpleVectorStore(store_path=tmpdir)

                # Check that the correct model was used
                mock_embeddings.assert_called_once_with(model="models/gemini-embedding-001")

    def test_gemini_model_name_format(self):
        """Test that model names are in correct format"""
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

        # LLM model name should not have "models/" prefix
        llm_model = "gemini-2.5-flash"
        assert not llm_model.startswith("models/")

        # Embedding model name should have "models/" prefix
        embedding_model = "models/gemini-embedding-001"
        assert embedding_model.startswith("models/")


# Test configuration information
def test_print_configuration_info():
    """Print test configuration information"""
    has_google_key = bool(os.getenv("GOOGLE_API_KEY"))
    # Note: Configuration no longer needed - langchain_google_genai handles it automatically

    print("\n" + "="*60)
    print("Google Models Test Configuration")
    print("="*60)
    print(f"Google API Key Available: {has_google_key}")
    print(f"LLM Model: gemini-2.5-flash")
    print(f"Embedding Model: models/gemini-embedding-001")
    print(f"Embedding Dimensions: 3072")
    print("="*60 + "\n")

    if not has_google_key:
        print("⚠️  WARNING: Most tests will be skipped without Google API key")
        print("   Set GOOGLE_API_KEY environment variable to run all tests")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
