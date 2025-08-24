"""
Agent Executor module for the Paper Search Agent.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from src.paper_search import PaperSearch
from src.output_formatter import OutputFormatter
from src.query_analyzer import QueryAnalyzer
from config import (
    LLM_API_KEY,
    LLM_API_URL,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    USE_FALLBACK_ON_LLM_ERROR,
)
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)


class PaperSearchAgent:
    """Paper Search Agent for searching academic papers."""

    def __init__(self):
        """Initialize the paper search agent."""
        logger.info("Initializing PaperSearchAgent")
        # Initialize paper search component
        self.paper_search = PaperSearch()
        # Initialize query analyzer (required)
        self.query_analyzer = QueryAnalyzer(
            api_key=LLM_API_KEY,
            api_url=LLM_API_URL,
            base_url=LLM_BASE_URL,
            model=LLM_MODEL,
            provider=LLM_PROVIDER,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )
        self.max_search_results = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
        logger.info("Query analyzer initialized")

    async def analyze_query(self, query: str) -> Tuple[bool, str, Optional[List[str]]]:
        """
        Analyze the user query using LLM.

        Args:
            query: User query string

        Returns:
            Tuple containing:
                - is_valid: Boolean indicating if the query is valid and clear
                - search_query: Modified search query (translated to English if needed)
                - keywords: List of extracted keywords or None if query is invalid
        """
        if not self.query_analyzer:
            raise ValueError(
                "Query analyzer is required but not initialized. Please check your LLM API configuration."
            )

        logger.info(f"Analyzing query: {query}")
        return await self.query_analyzer.analyze_query(query)

    async def search_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search for papers."""
        logger.info(f"Searching for papers with query: {query}")
        results = await self.paper_search.search_papers(query, max_results)
        return [result.to_dict() for result in results]

    async def handle_search(self, query: str) -> str:
        """Handle search request."""
        logger.info(f"Handling search for original query: {query}")

        # Analyze query first if query analyzer is enabled
        is_valid, search_query, keywords = await self.analyze_query(query)
        if not is_valid:
            return "Your query seems unclear or incomplete. Please provide more specific details about the academic papers you're looking for."

        # If query was modified (e.g., translated from Chinese to English), log it
        if search_query != query:
            logger.info(f"Query modified from '{query}' to these keywords:'{keywords}'")

        # Search for papers using the processed query (use search_query, not keywords list)
        keywords_string = ", ".join(keywords) if keywords else ""
        search_results = await self.search_papers(
            query=keywords_string, max_results=self.max_search_results
        )

        if not search_results:
            # If no results with processed query, try with original query as fallback
            if search_query != query:
                logger.info(
                    f"No results with processed query, trying original query: {query}"
                )
                search_results = await self.search_papers(query)

            if not search_results:
                return "No papers found matching your query. Please try a different search term."

        # Format search results
        formatted_results = OutputFormatter.format_search_results_for_confirmation(
            search_results
        )

        # If query was modified, add a note about it

        return formatted_results


class PaperSearchAgentExecutor(AgentExecutor):
    """Paper Search Agent Executor for A2A protocol integration."""

    def __init__(self):
        """Initialize the PaperSearchAgentExecutor."""
        logger.info("Initializing PaperSearchAgentExecutor")
        self.agent = PaperSearchAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute the agent with the given context and event queue.

        Args:
            context: The request context
            event_queue: The event queue for sending messages
        """
        logger.info(
            "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
        )
        logger.info("Executing PaperSearchAgentExecutor")

        # Extract message from context
        msg = context.message
        text_content = []

        # Process message parts
        if msg and hasattr(msg, "parts"):
            for part in msg.parts:
                # Handle text parts only
                if hasattr(part.root, "kind") and part.root.kind == "text":
                    text_content.append(part.root.text)
                    logger.info(f"Received text message: {part.root.text}")

        # Combine text content
        combined_text = " ".join(text_content) if text_content else ""

        # Generate response based on input
        response = ""

        try:
            if combined_text:
                # Handle search request
                response = await self.agent.handle_search(combined_text)
            else:
                # Default welcome message if no input
                response = "Welcome to the Paper Search Agent! I can help you search for academic papers from arXiv and Semantic Scholar. What would you like to search for?"

            # Send response
            await event_queue.enqueue_event(new_agent_text_message(response))
            logger.info(f"Response sent: {response}")

        except Exception as e:
            logger.error(f"Error in PaperSearchAgentExecutor.execute: {e}")
            error_message = f"An error occurred while processing your request: {str(e)}"
            await event_queue.enqueue_event(new_agent_text_message(error_message))
        logger.info(
            "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Cancel the current execution.

        Args:
            context: The request context
            event_queue: The event queue for sending messages
        """
        logger.info(f"Cancelling task: {context.task_id}")

        # Send cancellation message
        await event_queue.enqueue_event(new_agent_text_message("Task cancelled."))
