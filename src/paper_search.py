"""
Paper Search module for searching academic papers from various sources.
"""

import logging
from typing import Dict, List, Optional

import arxiv
from semanticscholar import SemanticScholar

from config import (
    ARXIV_CATEGORIES,
    SEMANTIC_SCHOLAR_API_KEY,
    ENABLE_SEMANTIC_SCHOLAR,
    MAX_SEARCH_RESULTS,
    SEARCH_SOURCE,
    SEMANTIC_SCHOLAR_SORT,
)

# Configure logging
logger = logging.getLogger(__name__)


class PaperSearchResult:
    """Class representing a paper search result."""

    def __init__(
        self,
        title: str,
        authors: List[str],
        abstract: str,
        url: str,
        pdf_url: Optional[str] = None,
        year: Optional[int] = None,
        source: str = "unknown",
        paper_id: Optional[str] = None,
        score: float = 0.0,
    ):
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.url = url
        self.pdf_url = pdf_url
        self.year = year
        self.source = source
        self.paper_id = paper_id
        self.score = score

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "year": self.year,
            "source": self.source,
            "paper_id": self.paper_id,
            "score": self.score,
        }

    def __str__(self) -> str:
        """String representation."""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."

        year_str = f" ({self.year})" if self.year else ""

        return f"{self.title} by {authors_str}{year_str} [{self.source}]"


class PaperSearch:
    """Class for searching academic papers from various sources."""

    def __init__(self):
        """Initialize the paper search engine."""
        logger.info("Initializing paper search engine")

        # Initialize Semantic Scholar client
        if ENABLE_SEMANTIC_SCHOLAR:
            try:
                # Initialize with API key if available, otherwise use default (rate-limited) client
                if (
                    SEMANTIC_SCHOLAR_API_KEY
                    and SEMANTIC_SCHOLAR_API_KEY != "your-semantic-scholar-api-key"
                ):
                    self.s2_client = SemanticScholar(api_key=SEMANTIC_SCHOLAR_API_KEY)
                    logger.info("Initialized Semantic Scholar client with API key")
                else:
                    self.s2_client = SemanticScholar()
                    logger.info(
                        "Initialized Semantic Scholar client without API key (rate limited)"
                    )
            except Exception as e:
                logger.error(f"Failed to initialize Semantic Scholar client: {e}")
                self.s2_client = None
        else:
            self.s2_client = None
            logger.info("Semantic Scholar is disabled")

    async def search_papers(
        self,
        query: str,
        max_results: int = MAX_SEARCH_RESULTS,
        source: str = None,
    ) -> List[PaperSearchResult]:
        """
        Search for papers from the configured source.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            source: Source to search (default: from SEARCH_SOURCE config)

        Returns:
            List of PaperSearchResult objects
        """
        if source is None:
            source = SEARCH_SOURCE

        logger.info(
            f"Searching for papers with query: '{query}' using source: {source}"
        )

        results = []

        # Search based on configured source
        if source == "arxiv":
            try:
                results = await self.search_arxiv(query, max_results)
                logger.info(f"Found {len(results)} results from arXiv")
            except Exception as e:
                logger.error(f"Error searching arXiv: {e}")
        elif source == "semantic_scholar" and ENABLE_SEMANTIC_SCHOLAR:
            try:
                results = await self.search_semantic_scholar(query, max_results)
                logger.info(f"Found {len(results)} results from Semantic Scholar")
            except Exception as e:
                logger.error(f"Error searching Semantic Scholar: {e}")
        else:
            logger.error(f"Invalid or disabled search source: {source}")

        return results

    async def search_arxiv(
        self, query: str, max_results: int = 5
    ) -> List[PaperSearchResult]:
        """
        Search for papers on arXiv.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of PaperSearchResult objects
        """
        logger.info(f"Searching arXiv for: {query}")

        # Add category filter if specified
        if ARXIV_CATEGORIES:
            categories = ARXIV_CATEGORIES.split(",")
            category_filter = " OR ".join([f"cat:{cat.strip()}" for cat in categories])
            search_query = f"({query}) AND ({category_filter})"
        else:
            search_query = query

        # Create arXiv search client
        client = arxiv.Client()

        # Create search
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = []

        # Execute search
        for result in client.results(search):
            # Extract year from published date
            year = result.published.year if result.published else None

            # Create PaperSearchResult
            paper_result = PaperSearchResult(
                title=result.title,
                authors=[author.name for author in result.authors],
                abstract=result.summary,
                url=result.entry_id,
                pdf_url=result.pdf_url,
                year=year,
                source="arxiv",
                paper_id=result.get_short_id(),
                score=1.0,  # Equal base score for arXiv results
            )

            results.append(paper_result)

        return results

    async def search_semantic_scholar(
        self, query: str, max_results: int = 5
    ) -> List[PaperSearchResult]:
        """
        Search for papers on Semantic Scholar using the semanticscholar library.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of PaperSearchResult objects
        """
        logger.info(f"Searching Semantic Scholar for: {query}")

        if not self.s2_client:
            logger.warning("Semantic Scholar client not initialized")
            return []

        try:
            results = self.s2_client.search_paper(
                query=query, sort=SEMANTIC_SCHOLAR_SORT, bulk=True
            )

            if not results or not results.items:
                logger.info(f"No results found for query: {query}")
                return []

            # Limit results to max_results
            papers = results.items[:max_results]
            paper_results = []

            for paper in papers:
                # Safely extract attributes using getattr to prevent crashes
                title = getattr(paper, "title", "Unknown Title")
                authors_list = getattr(paper, "authors", [])
                year = getattr(paper, "year", None)
                citation_count = getattr(paper, "citationCount", 0)
                abstract = getattr(paper, "abstract", "")
                url = getattr(paper, "url", "")
                paper_id = getattr(paper, "paperId", None)

                # Extract author names safely
                author_names = []
                if authors_list:
                    for author in authors_list:
                        if hasattr(author, "name"):
                            author_names.append(author.name)
                        else:
                            author_names.append(str(author))

                # Try to get PDF URL from openAccessPdf
                pdf_url = None
                open_access_pdf = getattr(paper, "openAccessPdf", None)
                if open_access_pdf and hasattr(open_access_pdf, "url"):
                    pdf_url = open_access_pdf.url

                # Calculate score based on citation count, but keep it balanced with arXiv
                # Base score of 1.0, with small bonus for high citations
                if citation_count:
                    # Add small bonus for citations, max 0.2 bonus
                    citation_bonus = min(citation_count / 10000, 0.2)
                    score = 1.0 + citation_bonus
                else:
                    score = 1.0

                # Create PaperSearchResult
                paper_result = PaperSearchResult(
                    title=title,
                    authors=author_names,
                    abstract=abstract,
                    url=url,
                    pdf_url=pdf_url,
                    year=year,
                    source="semantic_scholar",
                    paper_id=paper_id,
                    score=score,
                )

                paper_results.append(paper_result)

                # Log citation count if available
                if citation_count:
                    logger.info(
                        f"Found paper '{title[:50]}...' with {citation_count} citations"
                    )

            logger.info(
                f"Successfully found {len(paper_results)} papers from Semantic Scholar"
            )
            return paper_results

        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {e}")
            return []

    def format_results_for_user(self, results: List[PaperSearchResult]) -> str:
        """
        Format search results for user confirmation.

        Args:
            results: List of PaperSearchResult objects

        Returns:
            Formatted string with search results
        """
        if not results:
            return "No papers found matching your query."

        formatted = "I found the following papers that match your query:\n\n"

        for i, result in enumerate(results):
            authors_str = ", ".join(result.authors[:3])
            if len(result.authors) > 3:
                authors_str += " et al."

            year_str = f" ({result.year})" if result.year else ""

            formatted += f"{i + 1}. **{result.title}**\n"
            formatted += f"   Authors: {authors_str}{year_str}\n"
            formatted += f"   Source: {result.source.title()}\n"
            if result.abstract:
                # Truncate abstract if too long
                abstract = (
                    result.abstract[:200] + "..."
                    if len(result.abstract) > 200
                    else result.abstract
                )
                formatted += f"   Abstract: {abstract}\n"
            formatted += "\n"

        formatted += "Please select a paper by number to review, or provide more details to refine the search."

        return formatted
