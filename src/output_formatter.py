"""
Output Formatter module for formatting search results.
"""

import logging
from typing import Dict, List

# Configure logging
logger = logging.getLogger(__name__)


class OutputFormatter:
    """Class for formatting search results."""

    @staticmethod
    def format_search_results_for_confirmation(
        results: List[Dict], output_format: str = "markdown"
    ) -> str:
        """
        Format search results.

        Args:
            results: List of search result dictionaries
            output_format: Output format ("markdown", "text")

        Returns:
            Formatted search results
        """
        if not results:
            return "No papers found matching your query."

        if output_format == "markdown":
            return OutputFormatter._format_search_results_markdown(results)
        else:
            return OutputFormatter._format_search_results_text(results)

    @staticmethod
    def _format_search_results_markdown(results: List[Dict]) -> str:
        """Format search results as Markdown."""
        md = "# Search Results\n\n"
        md += "I found the following papers that match your query:\n\n"

        for i, result in enumerate(results):
            authors_str = ", ".join(result.get("authors", [])[:3])
            if len(result.get("authors", [])) > 3:
                authors_str += " et al."

            year_str = f" ({result.get('year')})" if result.get("year") else ""

            md += f"## {i + 1}. {result.get('title', 'Unknown Title')}\n\n"
            md += f"**Authors**: {authors_str}{year_str}\n\n"
            md += f"**Source**: {result.get('source', 'Unknown').title()}\n\n"

            if result.get("abstract"):
                # Truncate abstract if too long
                abstract = result["abstract"]
                if len(abstract) > 300:
                    abstract = abstract[:300] + "..."
                md += f"**Abstract**: {abstract}\n\n"

            if result.get("url"):
                md += f"**URL**: {result['url']}\n\n"

            if result.get("pdf_url"):
                md += f"**PDF**: {result['pdf_url']}\n\n"

            md += "---\n\n"

        md += "Here are the papers that match your search query."

        return md

    @staticmethod
    def _format_search_results_text(results: List[Dict]) -> str:
        """Format search results as plain text."""
        text = "Search Results\n\n"
        text += "I found the following papers that match your query:\n\n"

        for i, result in enumerate(results):
            authors_str = ", ".join(result.get("authors", [])[:3])
            if len(result.get("authors", [])) > 3:
                authors_str += " et al."

            year_str = f" ({result.get('year')})" if result.get("year") else ""

            text += f"{i + 1}. {result.get('title', 'Unknown Title')}\n"
            text += f"   Authors: {authors_str}{year_str}\n"
            text += f"   Source: {result.get('source', 'Unknown').title()}\n"

            if result.get("abstract"):
                # Truncate abstract if too long
                abstract = result["abstract"]
                if len(abstract) > 200:
                    abstract = abstract[:200] + "..."
                text += f"   Abstract: {abstract}\n"

            text += "\n"

        text += "Here are the papers that match your search query."

        return text
