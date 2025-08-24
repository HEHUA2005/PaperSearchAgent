#!/usr/bin/env python3
"""
Test script to verify the new single search source configuration works correctly.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from paper_search import PaperSearch
from config import SEARCH_SOURCE, SEMANTIC_SCHOLAR_SORT


async def test_configuration():
    """Test the new single search source configuration."""
    print("=== Testing Paper Search Configuration ===")
    print(f"Configured search source: {SEARCH_SOURCE}")
    print(f"Semantic Scholar sort order: {SEMANTIC_SCHOLAR_SORT}")
    print()

    # Initialize search engine
    search_engine = PaperSearch()

    # Test search with configured source
    query = "transformer attention mechanisms"
    print(f"Testing search query: '{query}'")
    print(f"Searching with configured source: {SEARCH_SOURCE}")

    try:
        results = await search_engine.search_papers(query, max_results=5)

        if results:
            print(f"\n✅ Found {len(results)} papers:")
            for i, paper in enumerate(results, 1):
                print(f"\n{i}. {paper.title}")
                print(f"   Authors: {', '.join(paper.authors[:3])}")
                if len(paper.authors) > 3:
                    print("   (and more...)")
                print(f"   Year: {paper.year or 'Unknown'}")
                print(f"   Source: {paper.source}")
                print(f"   Score: {paper.score:.2f}")
                if paper.abstract:
                    abstract_preview = (
                        paper.abstract[:150] + "..."
                        if len(paper.abstract) > 150
                        else paper.abstract
                    )
                    print(f"   Abstract: {abstract_preview}")
        else:
            print("❌ No papers found")

    except Exception as e:
        print(f"❌ Error during search: {e}")
        import traceback

        traceback.print_exc()

    print("\n=== Testing Alternative Source Configuration ===")

    # Test the other source to show it works
    alternative_source = (
        "arxiv" if SEARCH_SOURCE == "semantic_scholar" else "semantic_scholar"
    )
    print(f"\nTesting {alternative_source} search...")
    try:
        alt_results = await search_engine.search_papers(
            query, max_results=2, source=alternative_source
        )
        print(f"✅ {alternative_source} search returned {len(alt_results)} results")
        for paper in alt_results:
            print(f"   - {paper.title} [{paper.source}] (Score: {paper.score:.2f})")
    except Exception as e:
        print(f"❌ {alternative_source} search failed: {e}")

    print("\n=== Configuration Test Complete ===")
    print(f"Current configuration uses: {SEARCH_SOURCE}")
    print("To change source, modify SEARCH_SOURCE in .env file:")
    print("  - Set to 'arxiv' for arXiv-only search")
    print("  - Set to 'semantic_scholar' for Semantic Scholar-only search")


if __name__ == "__main__":
    asyncio.run(test_configuration())
