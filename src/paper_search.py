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
    ENABLE_PDF_URL_ENHANCEMENT,
    REQUIRE_PDF_DOWNLOAD,
    TRUSTED_PDF_SOURCES,
)

# Backup search configuration
MAX_BACKUP_ATTEMPTS = 5  # Maximum number of backup search attempts
BACKUP_BATCH_SIZE = 20  # Number of papers to fetch in each backup attempt
MAX_TOTAL_PAPERS_TO_PROCESS = 200  # Maximum total papers to process during backup

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

    def _is_trusted_pdf_url(self, url: str) -> bool:
        """
        Check if a PDF URL is from a trusted source that allows direct downloads.

        Args:
            url: PDF URL to check

        Returns:
            True if the URL is from a trusted source, False otherwise
        """
        if not url:
            return False

        # Check if URL is from a trusted source
        for trusted_source in TRUSTED_PDF_SOURCES:
            if trusted_source in url:
                return True

        # ArXiv URLs are always trusted
        if "arxiv.org/pdf" in url:
            return True

        # Other URLs are not trusted (may require payment or authentication)
        return False

    def _extract_enhanced_pdf_urls(self, paper) -> Optional[str]:
        """
        Extract PDF URLs from paper data using multiple strategies.

        Args:
            paper: Semantic Scholar paper object

        Returns:
            First available PDF URL or None
        """
        pdf_urls = []

        # Strategy 1: OpenAccess PDF from Semantic Scholar
        open_access_pdf = getattr(paper, "openAccessPdf", None)
        if open_access_pdf and hasattr(open_access_pdf, "url") and open_access_pdf.url:
            pdf_urls.append(open_access_pdf.url)
            logger.info(f"Found openAccessPdf URL: {open_access_pdf.url}")

        # Strategy 2: Extract from externalIds
        external_ids = getattr(paper, "externalIds", {})
        if external_ids:
            # arXiv PDF links
            if "ArXiv" in external_ids:
                arxiv_id = external_ids["ArXiv"]
                arxiv_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                pdf_urls.append(arxiv_pdf_url)
                logger.info(f"Generated arXiv PDF URL: {arxiv_pdf_url}")

            # PubMed Central - many medical papers
            if (
                "PubMed" in external_ids
                or "PMID" in external_ids
                or "PMC" in external_ids
            ):
                pmc_id = external_ids.get("PMC", "")
                pmid = external_ids.get("PMID", "")
                if pmc_id:
                    pmc_pdf_url = (
                        f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
                    )
                    pdf_urls.append(pmc_pdf_url)
                    logger.info(f"Generated PMC PDF URL: {pmc_pdf_url}")
                elif pmid:
                    pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    pdf_urls.append(pubmed_url)
                    logger.info(f"Generated PubMed URL: {pubmed_url}")

            # DOI-based PDF links for various repositories
            if "DOI" in external_ids:
                doi = external_ids["DOI"]

                # bioRxiv and medRxiv papers
                if "10.1101" in doi:
                    biorxiv_pdf_url = (
                        f"https://www.biorxiv.org/content/{doi}v1.full.pdf"
                    )
                    pdf_urls.append(biorxiv_pdf_url)
                    logger.info(f"Generated bioRxiv PDF URL: {biorxiv_pdf_url}")

                # Nature papers
                if "10.1038" in doi:
                    nature_pdf_url = f"https://www.nature.com/articles/{doi.replace('10.1038/', '')}.pdf"
                    pdf_urls.append(nature_pdf_url)
                    logger.info(f"Generated Nature PDF URL: {nature_pdf_url}")

                # Science papers
                if "10.1126" in doi:
                    science_pdf_url = f"https://science.sciencemag.org/content/{doi.split('/')[-1]}.full.pdf"
                    pdf_urls.append(science_pdf_url)
                    logger.info(f"Generated Science PDF URL: {science_pdf_url}")

                # IEEE papers
                if "10.1109" in doi:
                    ieee_pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={doi.split('/')[-1]}"
                    pdf_urls.append(ieee_pdf_url)
                    logger.info(f"Generated IEEE PDF URL: {ieee_pdf_url}")

                # ACM papers
                if "10.1145" in doi:
                    acm_pdf_url = f"https://dl.acm.org/doi/pdf/{doi}"
                    pdf_urls.append(acm_pdf_url)
                    logger.info(f"Generated ACM PDF URL: {acm_pdf_url}")

                # arXiv DOI pattern
                if "10.48550" in doi:
                    arxiv_id = doi.split("/")[-1]
                    # Remove 'arXiv.' prefix if present
                    if arxiv_id.startswith("arXiv."):
                        arxiv_id = arxiv_id[6:]  # Remove 'arXiv.' prefix
                    arxiv_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    pdf_urls.append(arxiv_pdf_url)
                    logger.info(f"Generated arXiv PDF URL from DOI: {arxiv_pdf_url}")

                # Generic DOI PDF URL (fallback)
                if not pdf_urls:
                    generic_pdf_url = f"https://doi.org/{doi}"
                    pdf_urls.append(generic_pdf_url)
                    logger.info(f"Generated generic DOI URL: {generic_pdf_url}")

        # Filter and return only trusted PDF URLs
        trusted_pdf_urls = []
        for url in pdf_urls:
            if self._is_trusted_pdf_url(url):
                trusted_pdf_urls.append(url)
                logger.info(f"Found trusted PDF URL: {url}")

        # Return the first trusted PDF URL
        if trusted_pdf_urls:
            selected_url = trusted_pdf_urls[0]
            logger.info(f"Selected trusted PDF URL: {selected_url}")
            return selected_url

        logger.info("No trusted PDF URL found for this paper")
        return None

    def _process_semantic_scholar_paper(self, paper) -> Optional[PaperSearchResult]:
        """
        Process a single Semantic Scholar paper and return PaperSearchResult if it has trusted PDF URL.

        Args:
            paper: Semantic Scholar paper object

        Returns:
            PaperSearchResult if paper has trusted PDF URL, None otherwise
        """
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

        # Use enhanced PDF URL extraction method if enabled
        if ENABLE_PDF_URL_ENHANCEMENT:
            pdf_url = self._extract_enhanced_pdf_urls(paper)
        else:
            # Fallback to original method
            pdf_url = None
            open_access_pdf = getattr(paper, "openAccessPdf", None)
            if open_access_pdf and hasattr(open_access_pdf, "url"):
                pdf_url = open_access_pdf.url

        # Only return paper if it has trusted PDF URL when REQUIRE_PDF_DOWNLOAD is enabled
        if REQUIRE_PDF_DOWNLOAD:
            if not pdf_url or not self._is_trusted_pdf_url(pdf_url):
                logger.debug(f"Skipped paper without trusted PDF URL: {title[:50]}...")
                return None

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

        logger.info(f"Processed paper with trusted PDF URL: {title[:50]}...")
        return paper_result

    async def _fetch_additional_papers(
        self, query: str, max_results: int, current_count: int, processed_papers: List
    ) -> List[PaperSearchResult]:
        """
        Fetch additional papers from the remaining papers in the initial large search.
        Since Semantic Scholar API doesn't support offset, we use a larger initial search
        and process the remaining papers.

        Args:
            query: Search query
            max_results: Target number of results
            current_count: Current number of valid papers found
            processed_papers: List of all papers from initial search

        Returns:
            List of additional PaperSearchResult objects
        """
        additional_papers = []
        papers_needed = max_results - current_count

        logger.info(
            f"Processing remaining papers to find {papers_needed} more papers with trusted PDFs"
        )

        # Process remaining papers beyond the initial max_results limit
        remaining_papers = (
            processed_papers[max_results:]
            if len(processed_papers) > max_results
            else []
        )

        if not remaining_papers:
            logger.info("No additional papers available to process")
            return additional_papers

        logger.info(
            f"Processing {len(remaining_papers)} additional papers from initial search"
        )

        papers_processed = 0
        for paper in remaining_papers:
            if len(additional_papers) >= papers_needed:
                logger.info("Reached target number of additional papers")
                break

            papers_processed += 1
            paper_result = self._process_semantic_scholar_paper(paper)
            if paper_result:
                additional_papers.append(paper_result)
                logger.info(f"Added additional paper: {paper_result.title[:50]}...")

            # Limit processing to avoid excessive computation
            if papers_processed >= MAX_TOTAL_PAPERS_TO_PROCESS:
                logger.info(
                    f"Reached maximum processing limit of {MAX_TOTAL_PAPERS_TO_PROCESS} papers"
                )
                break

        final_count = len(additional_papers) + current_count
        logger.info(
            f"Additional paper processing completed. Found {len(additional_papers)} additional papers. Total: {final_count}/{max_results}"
        )

        if final_count < max_results:
            logger.warning(
                f"Could not find enough papers with trusted PDF URLs. Found {final_count}/{max_results}"
            )

        return additional_papers

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

            # Only add papers with trusted PDF URLs if REQUIRE_PDF_DOWNLOAD is enabled
            if REQUIRE_PDF_DOWNLOAD:
                if paper_result.pdf_url and self._is_trusted_pdf_url(
                    paper_result.pdf_url
                ):
                    results.append(paper_result)
                    logger.info(
                        f"Added arXiv paper with trusted PDF URL: {result.title[:50]}..."
                    )
                else:
                    logger.info(
                        f"Skipped arXiv paper without trusted PDF URL: {result.title[:50]}..."
                    )
            else:
                # Add all papers if REQUIRE_PDF_DOWNLOAD is disabled
                results.append(paper_result)

        filtered_count = len(results)
        logger.info(f"Found {filtered_count} arXiv papers with trusted PDF URLs")

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
            # Request a larger batch initially to have more papers to choose from
            # when filtering for trusted PDF URLs
            initial_limit = max_results * 10 if REQUIRE_PDF_DOWNLOAD else max_results

            # Request additional fields including externalIds for better PDF URL extraction
            results = self.s2_client.search_paper(
                query=query,
                sort=SEMANTIC_SCHOLAR_SORT,
                bulk=True,
                limit=initial_limit,
                fields=[
                    "title",
                    "authors",
                    "year",
                    "abstract",
                    "url",
                    "openAccessPdf",
                    "externalIds",
                    "citationCount",
                ],
            )

            if not results or not results.items:
                logger.info(f"No results found for query: {query}")
                return []

            all_papers = results.items
            logger.info(f"Retrieved {len(all_papers)} papers from Semantic Scholar")

            paper_results = []

            # Process papers in order until we have enough with trusted PDFs
            for i, paper in enumerate(all_papers):
                if len(paper_results) >= max_results:
                    break

                paper_result = self._process_semantic_scholar_paper(paper)
                if paper_result:
                    paper_results.append(paper_result)
                elif REQUIRE_PDF_DOWNLOAD:
                    # Log when papers are skipped due to PDF requirements
                    title = getattr(paper, "title", "Unknown Title")
                    logger.debug(
                        f"Skipped paper without trusted PDF URL: {title[:50]}..."
                    )

            filtered_count = len(paper_results)
            logger.info(
                f"Successfully found {filtered_count} papers from Semantic Scholar with trusted PDF URLs"
            )

            # Use enhanced backup logic if we need more papers and have more to process
            if (
                REQUIRE_PDF_DOWNLOAD
                and filtered_count < max_results
                and len(all_papers) > filtered_count
            ):
                logger.info(
                    f"Need {max_results - filtered_count} more papers. Processing remaining papers..."
                )
                try:
                    additional_papers = await self._fetch_additional_papers(
                        query, max_results, filtered_count, all_papers
                    )
                    paper_results.extend(additional_papers)
                    logger.info(
                        f"Additional processing added {len(additional_papers)} papers. "
                        f"Total: {len(paper_results)}/{max_results}"
                    )
                except Exception as e:
                    logger.error(f"Error in additional paper processing: {e}")

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
