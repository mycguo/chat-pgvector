"""
Web search functionality using DuckDuckGo.
Provides internet search capabilities for the AI assistant.
"""

import os
from typing import List, Dict, Optional

# Set USER_AGENT environment variable if not already set
# This prevents warnings from duckduckgo_search library
if "USER_AGENT" not in os.environ:
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

from duckduckgo_search import DDGS


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
    
    Returns:
        List of dictionaries with 'title', 'url', and 'snippet' keys
    """
    try:
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(query, max_results=max_results):
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', '')
                })
            return results
    except Exception as e:
        print(f"Web search error: {e}")
        return []


def format_search_results(results: List[Dict[str, str]]) -> str:
    """
    Format search results for LLM context.
    
    Args:
        results: List of search result dictionaries
    
    Returns:
        Formatted string with search results
    """
    if not results:
        return "No web search results found."
    
    formatted = "=== Web Search Results ===\n\n"
    for i, result in enumerate(results, 1):
        formatted += f"[{i}] {result['title']}\n"
        formatted += f"URL: {result['url']}\n"
        formatted += f"Summary: {result['snippet']}\n\n"
    
    return formatted


def is_search_needed(question: str) -> bool:
    """
    Detect if a question requires web search.
    
    Args:
        question: User's question
    
    Returns:
        True if web search is recommended, False otherwise
    """
    question_lower = question.lower()
    
    # Time-sensitive keywords
    time_keywords = [
        'current', 'latest', 'recent', 'today', 'now', '2024', '2025',
        'this year', 'this month', 'upcoming', 'next'
    ]
    
    # Explicit search requests
    search_keywords = [
        'search for', 'look up', 'find information about', 'what is',
        'tell me about', 'information about', 'details about'
    ]
    
    # Market/salary queries
    market_keywords = [
        'salary', 'compensation', 'pay', 'job market', 'hiring trends',
        'industry trends', 'market rate', 'average salary'
    ]
    
    # Company information queries
    company_keywords = [
        'company', 'about', 'overview', 'what does', 'what is'
    ]
    
    # Check for time-sensitive queries
    if any(keyword in question_lower for keyword in time_keywords):
        return True
    
    # Check for explicit search requests
    if any(keyword in question_lower for keyword in search_keywords):
        return True
    
    # Check for market/salary queries
    if any(keyword in question_lower for keyword in market_keywords):
        return True
    
    # Check for company information (but not if it's about user's own applications)
    if any(keyword in question_lower for keyword in company_keywords):
        # Don't search if asking about user's own applications
        if 'my application' in question_lower or 'my interview' in question_lower:
            return False
        return True
    
    return False


def extract_search_query(question: str) -> str:
    """
    Extract a clean search query from the user's question.
    
    Args:
        question: User's original question
    
    Returns:
        Cleaned search query optimized for web search
    """
    # Remove common prefixes that don't help search
    prefixes_to_remove = [
        'search for', 'look up', 'find information about',
        'tell me about', 'what is', 'what are', 'who is', 'who are'
    ]
    
    query = question.strip()
    query_lower = query.lower()
    
    for prefix in prefixes_to_remove:
        if query_lower.startswith(prefix):
            query = query[len(prefix):].strip()
            # Remove leading "about" or "the" if present
            if query.lower().startswith('about '):
                query = query[6:].strip()
            if query.lower().startswith('the '):
                query = query[4:].strip()
            break
    
    return query.strip() if query else question

