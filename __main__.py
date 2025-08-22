"""
Main entry point for the Paper Search Agent.

This module sets up the A2A server and defines the agent card and skills.
"""

import logging
import os
import sys
import uvicorn
from dotenv import load_dotenv
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import PaperSearchAgentExecutor
from config import (
    HOST,
    PORT,
    AGENT_URL,
    get_agent_skills,
    get_public_agent_card,
    validate_config,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("paper_search_agent.log"),
    ],
)
logger = logging.getLogger(__name__)
load_dotenv()


def main():
    """Main entry point."""
    logger.info("Starting Paper Search Agent")
    load_dotenv()
    # Validate configuration
    validate_config()

    task_store = InMemoryTaskStore()

    agent_executor = PaperSearchAgentExecutor()

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
    )

    agent_card = get_public_agent_card()

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    # Print startup message
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                   PAPER SEARCH AGENT                         ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Server URL: {AGENT_URL:<48}║
║  Version: {agent_card.version:<51}║
║                                                              ║
║  Features:                                                   ║
║    - Search academic papers from arXiv & Semantic Scholar   ║
║    - Natural language queries in multiple languages          ║
║    - Returns up to 5 most relevant papers                   ║
║    - Direct links to papers and PDFs                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Start server
    uvicorn.run(server.build(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
