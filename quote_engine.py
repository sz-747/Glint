"""
Quote Search & Ranking Engine

A custom keyword-based search algorithm that finds and ranks quotes
from the database by relevance to a user's query.

Algorithm steps:
    1. TOKENIZE  - Split text into lowercase words, strip punctuation,
                   remove common stop words.
    2. SCORE     - For each QuoteEntry, count keyword matches using set
                   intersection (exact matches) and substring checks
                   (partial matches). Exact matches are weighted higher.
    3. RANK      - Sort quotes by score descending. Ties are broken by
                   the best quality_score among the quote's AnalysisChunks.
    4. RETURN    - Return the top N results with their analysis chunks.

Data structures used:
    - Sets for O(1) keyword lookup and fast intersection
    - Dictionaries for accumulating per-quote scores
    - Lists for ordered ranked output

Author: Steve
Date: February 2026
"""

import re
import string
from models import QuoteEntry, AnalysisChunk

# ============================================
# Stop Words
# ============================================
# Common English words that carry little meaning for search.
# Removing these improves result relevance by focusing on
# content-bearing keywords.
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
    'for', 'of', 'with', 'by', 'from', 'is', 'it', 'as', 'be', 'was',
    'are', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'may', 'might', 'shall', 'can',
    'not', 'no', 'nor', 'so', 'if', 'then', 'than', 'too', 'very',
    'just', 'about', 'up', 'out', 'that', 'this', 'these', 'those',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'they',
    'his', 'her', 'its', 'them', 'their', 'what', 'which', 'who',
    'when', 'where', 'how', 'all', 'each', 'every', 'both', 'few',
    'more', 'most', 'other', 'some', 'such', 'only', 'own', 'same',
    'also', 'into', 'over', 'after', 'before', 'between', 'under',
    'again', 'there', 'here', 'once', 'during', 'while',
}

# Precompiled regex to strip punctuation from word boundaries
_PUNCTUATION_RE = re.compile(r'[{}]'.format(re.escape(string.punctuation)))


def tokenize(text):
    """
    Convert raw text into a list of meaningful keyword tokens.

    Steps:
        1. Convert to lowercase for case-insensitive matching
        2. Replace punctuation with spaces so "well-known" becomes
           two tokens: "well" and "known"
        3. Split on whitespace into individual words
        4. Filter out stop words and single-character tokens
        5. Return the cleaned token list

    Args:
        text (str): The raw input text to tokenize.

    Returns:
        list[str]: A list of lowercase keyword tokens with stop words
                   and punctuation removed.

    Example:
        >>> tokenize("The quick brown fox jumps over the lazy dog!")
        ['quick', 'brown', 'fox', 'jumps', 'lazy', 'dog']
    """
    if not text:
        return []

    # Step 1 & 2: lowercase and strip punctuation
    cleaned = _PUNCTUATION_RE.sub(' ', text.lower())

    # Step 3: split into words
    words = cleaned.split()

    # Step 4 & 5: remove stop words and short tokens
    tokens = [word for word in words if word not in STOP_WORDS and len(word) > 1]

    return tokens


def search_quotes(query_text, limit=5):
    """
    Search all QuoteEntry records and rank them by relevance to the query.

    Scoring algorithm:
        - Each quote's text is tokenized into a set of keywords.
        - The query is also tokenized into a set of keywords.
        - EXACT matches (set intersection) score 2 points each.
        - PARTIAL matches (query keyword is a substring of a quote
          keyword, or vice versa) score 1 point each.
        - The total score determines ranking.
        - Ties are broken by the highest quality_score among the
          quote's AnalysisChunks (higher is better).

    Args:
        query_text (str): The user's search query string.
        limit (int): Maximum number of results to return (default 5).

    Returns:
        list[dict]: Ranked list of quote results, each containing:
            - quote_id (int): The database ID of the quote
            - quote_text (str): The full quote text
            - source_label (str|None): Attribution/source of the quote
            - score (int): The relevance score
            - chunks (list[dict]): Associated analysis chunks, each with
              chunk_text (str) and quality_score (float)
    """
    # Tokenize the query and build a set for fast lookup
    query_tokens = tokenize(query_text)
    if not query_tokens:
        return []

    query_set = set(query_tokens)

    # Fetch all quotes from the database
    all_quotes = QuoteEntry.query.all()

    scored_results = []

    for quote in all_quotes:
        # Tokenize the quote text into a set of keywords
        quote_tokens = set(tokenize(quote.quote_text))

        # --- Scoring ---

        # Exact matches: words that appear in both query and quote
        # Uses set intersection for O(min(n, m)) efficiency
        exact_matches = query_set & quote_tokens
        score = len(exact_matches) * 2  # Weight exact matches at 2 points

        # Partial matches: query keyword is a substring of a quote keyword
        # or a quote keyword is a substring of a query keyword
        # Only count partials that weren't already exact matches
        for q_token in query_set - exact_matches:
            for quote_token in quote_tokens - exact_matches:
                if q_token in quote_token or quote_token in q_token:
                    score += 1
                    break  # Count each query token at most once

        # Skip quotes with zero relevance
        if score == 0:
            continue

        # --- Tie-breaking: best analysis chunk quality score ---
        best_quality = 0.0
        chunks_data = []
        for chunk in quote.analysis_chunks:
            chunks_data.append({
                'chunk_text': chunk.chunk_text,
                'quality_score': chunk.quality_score,
            })
            if chunk.quality_score > best_quality:
                best_quality = chunk.quality_score

        scored_results.append({
            'quote_id': quote.id,
            'quote_text': quote.quote_text,
            'source_label': quote.source_label,
            'score': score,
            'best_quality': best_quality,
            'chunks': chunks_data,
        })

    # --- Ranking ---
    # Primary sort: score descending
    # Secondary sort (tie-breaker): best_quality descending
    scored_results.sort(key=lambda r: (r['score'], r['best_quality']), reverse=True)

    # --- Return top N results ---
    top_results = scored_results[:limit]

    # Remove the internal tie-breaking field before returning
    for result in top_results:
        del result['best_quality']

    return top_results
