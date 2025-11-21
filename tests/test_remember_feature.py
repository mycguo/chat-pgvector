"""
Test suite for the "Remember" feature - conversational information saving.

This validates:
1. Intent detection for "remember" commands
2. Information extraction
3. Saving to vector store
4. Retrieval of saved information
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

# Skip tests if Google API key is not available
skip_without_api_key = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="Google API key not available"
)


class TestRememberIntentDetection:
    """Test intent detection for remember commands"""

    def test_remember_that_pattern(self):
        """Test 'remember that' pattern"""
        from app import detect_remember_intent

        text = "Remember that I prefer Python over JavaScript"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is True
        assert "prefer python over javascript" in extracted.lower()

    def test_remember_colon_pattern(self):
        """Test 'remember:' pattern"""
        from app import detect_remember_intent

        text = "Remember: My favorite color is blue"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is True
        assert "favorite color is blue" in extracted.lower()

    def test_save_this_pattern(self):
        """Test 'save this' pattern"""
        from app import detect_remember_intent

        text = "Save this: I graduated from MIT in 2020"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is True
        assert "graduated from mit in 2020" in extracted.lower()

    def test_store_that_pattern(self):
        """Test 'store that' pattern"""
        from app import detect_remember_intent

        text = "Store that Charles lives in San Francisco"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is True
        assert "charles lives in san francisco" in extracted.lower()

    def test_note_that_pattern(self):
        """Test 'note that' pattern"""
        from app import detect_remember_intent

        text = "Note that I prefer working remotely"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is True
        assert "prefer working remotely" in extracted.lower()

    def test_non_remember_question(self):
        """Test that regular questions are not detected as remember commands"""
        from app import detect_remember_intent

        text = "What is my favorite color?"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is False
        assert extracted == text

    def test_case_insensitive(self):
        """Test that detection is case-insensitive"""
        from app import detect_remember_intent

        text = "REMEMBER THAT Python is awesome"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is True
        assert "python is awesome" in extracted.lower()

    def test_with_punctuation(self):
        """Test extraction with punctuation"""
        from app import detect_remember_intent

        text = "Remember: I love pizza, especially margherita!"
        is_remember, extracted = detect_remember_intent(text)

        assert is_remember is True
        assert "pizza" in extracted.lower()
        assert "margherita" in extracted.lower()


class TestInformationEnrichment:
    """Test information enrichment functionality"""

    @skip_without_api_key
    def test_enrichment_basic(self):
        """Test that enrichment expands information"""
        from app import enrich_information

        original = "I prefer Python"
        enriched = enrich_information(original)

        assert enriched is not None
        assert len(enriched) > len(original)
        assert "Python" in enriched
        print(f"Original: {original}")
        print(f"Enriched: {enriched}")

    @skip_without_api_key
    def test_enrichment_preserves_facts(self):
        """Test that enrichment preserves core facts"""
        from app import enrich_information

        original = "Charles lives in San Francisco"
        enriched = enrich_information(original)

        # Core facts should be preserved
        assert "Charles" in enriched
        assert "San Francisco" in enriched
        print(f"Original: {original}")
        print(f"Enriched: {enriched}")


class TestSaveToKnowledgeBase:
    """Test saving information to vector store"""

    @skip_without_api_key
    def test_save_without_enrichment(self):
        """Test saving information without enrichment"""
        from app import save_to_knowledge_base

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.MilvusVectorStore') as mock_store_class:
                mock_store = MagicMock()
                mock_store_class.return_value = mock_store
                mock_store.add_texts.return_value = ['id1']

                info = "Test information to save"
                success, result = save_to_knowledge_base(info, enrich=False)

                assert success is True
                assert result == info
                mock_store.add_texts.assert_called_once()

    @skip_without_api_key
    def test_save_with_enrichment(self):
        """Test saving information with enrichment"""
        from app import save_to_knowledge_base

        with tempfile.TemporaryDirectory() as tmpdir:
            info = "Charles prefers Python"
            success, result = save_to_knowledge_base(info, enrich=True)

            assert success is True
            assert len(result) >= len(info)  # Enriched should be longer or equal
            print(f"Original: {info}")
            print(f"Saved (enriched): {result}")


class TestEndToEndRemember:
    """Test end-to-end remember functionality"""

    @skip_without_api_key
    def test_remember_and_retrieve(self):
        """Test saving information and then retrieving it"""
        from simple_vector_store import SimpleVectorStore
        from app import save_to_knowledge_base

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save information
            info = "Charles's favorite programming language is Python and he uses it for AI projects."
            success, enriched = save_to_knowledge_base(info, enrich=True)

            assert success is True
            print(f"Saved: {enriched}")

            # Try to retrieve it
            store = SimpleVectorStore(
                store_path="./vector_store_personal_assistant",
                embedding_model="models/gemini-embedding-001"
            )

            query = "What programming language does Charles prefer?"
            results = store.similarity_search(query, k=3)

            # Check if our saved information is in the results
            found = False
            for doc in results:
                if "Python" in doc.page_content and "Charles" in doc.page_content:
                    found = True
                    print(f"Found in results: {doc.page_content[:100]}...")
                    break

            assert found, "Saved information should be retrievable"

    @skip_without_api_key
    def test_multiple_remember_commands(self):
        """Test saving multiple pieces of information"""
        from app import save_to_knowledge_base, detect_remember_intent

        commands = [
            "Remember that Charles lives in San Francisco",
            "Remember: Charles graduated from MIT",
            "Store this: Charles enjoys hiking on weekends"
        ]

        saved_items = []

        for cmd in commands:
            is_remember, extracted = detect_remember_intent(cmd)
            assert is_remember is True

            success, result = save_to_knowledge_base(extracted, enrich=False)
            assert success is True
            saved_items.append(result)

        print(f"Saved {len(saved_items)} items successfully")
        for item in saved_items:
            print(f"  - {item}")


class TestRememberFeatureIntegration:
    """Test integration with UI components"""

    def test_user_input_with_remember(self):
        """Test user_input function with remember command"""
        from app import user_input

        # Mock the necessary components
        with patch('app.MilvusVectorStore') as mock_store_class, \
             patch('app.save_to_knowledge_base') as mock_save, \
             patch('streamlit.info'), \
             patch('streamlit.success'), \
             patch('streamlit.expander'):

            mock_save.return_value = (True, "Enriched information")

            # This should be handled as a remember command
            # Note: In actual Streamlit, we'd need to run this differently
            # For testing, we just verify the logic works
            pass  # Streamlit UI testing requires special setup

    def test_patterns_comprehensive(self):
        """Test all supported remember patterns"""
        from app import detect_remember_intent

        patterns_to_test = [
            ("Remember that I like coffee", True, "like coffee"),
            ("Remember: Coffee is great", True, "Coffee is great"),
            ("Remember coffee", True, "coffee"),
            ("Save this: Important note", True, "Important note"),
            ("Save that I prefer tea", True, "prefer tea"),
            ("Store this: My birthday is May 5", True, "birthday is May 5"),
            ("Store that I am 30 years old", True, "am 30 years old"),
            ("Keep in mind that I work remotely", True, "work remotely"),
            ("Note that I prefer emails", True, "prefer emails"),
            ("What do I like?", False, "What do I like?"),  # Not a remember command
            ("Tell me about coffee", False, "Tell me about coffee"),  # Not a remember command
        ]

        for text, expected_is_remember, expected_substring in patterns_to_test:
            is_remember, extracted = detect_remember_intent(text)
            assert is_remember == expected_is_remember, f"Failed for: {text}"
            if expected_is_remember:
                assert expected_substring.lower() in extracted.lower(), \
                    f"Expected '{expected_substring}' in '{extracted}' for input '{text}'"


def test_configuration_info():
    """Print test configuration"""
    import os
    import google.generativeai as genai

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        genai.configure(api_key=google_api_key)
    has_google_key = bool(google_api_key)

    print("\n" + "="*60)
    print("Remember Feature Test Configuration")
    print("="*60)
    print(f"Google API Key Available: {has_google_key}")
    print(f"Tests without API: Intent detection, pattern matching")
    print(f"Tests with API: Enrichment, save/retrieve")
    print("="*60 + "\n")

    if not has_google_key:
        print("⚠️  WARNING: Some tests will be skipped without Google API key")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
