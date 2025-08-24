import os
from typing import List
from a2a.types import AgentCapabilities, AgentSkill, AgentCard
from dotenv import load_dotenv

load_dotenv()

# Server Configuration
HOST = os.getenv("AGENT_HOST", "0.0.0.0")
PORT = int(os.getenv("AGENT_PORT", "9998"))
AGENT_URL = os.getenv("AGENT_URL", f"http://localhost:{PORT}/")

# Paper Search Configuration
ARXIV_CATEGORIES = os.getenv("ARXIV_CATEGORIES", "cs.AI,cs.LG,cs.CL")
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
ENABLE_SEMANTIC_SCHOLAR = os.getenv("ENABLE_SEMANTIC_SCHOLAR", "true").lower() == "true"
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))

# Search Source Configuration (single source only)
SEARCH_SOURCE = os.getenv("SEARCH_SOURCE", "semantic_scholar").strip().lower()
SEMANTIC_SCHOLAR_SORT = os.getenv("SEMANTIC_SCHOLAR_SORT", "citationCount:desc")

# Validate search source
if SEARCH_SOURCE not in ["arxiv", "semantic_scholar"]:
    print(
        f"WARNING: Invalid SEARCH_SOURCE '{SEARCH_SOURCE}'. Using 'semantic_scholar' as default."
    )
    SEARCH_SOURCE = "semantic_scholar"

# LLM Configuration for Query Analysis
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
USE_FALLBACK_ON_LLM_ERROR = (
    os.getenv("USE_FALLBACK_ON_LLM_ERROR", "false").lower() == "true"
)

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# Agent Skills Configuration
def get_agent_skills() -> List[AgentSkill]:
    """Define all agent skills."""
    return [
        AgentSkill(
            id="search_papers",
            name="Search Academic Papers",
            description="Search for academic papers from arXiv and Semantic Scholar based on natural language queries. Returns a numbered list of results (up to 5 papers) with titles, authors, abstracts, and links.",
            tags=[
                "search",
                "academic",
                "arxiv",
                "semantic-scholar",
                "papers",
            ],
            examples=[
                "Find papers about transformer attention mechanisms",
                "Search for recent papers on reinforcement learning",
                "找一些关于GAN的论文",
                "Papers on quantum computing",
                "Latest research on neural networks",
            ],
        ),
    ]


def get_public_agent_card() -> AgentCard:
    """Create the public agent card."""
    return AgentCard(
        name="Paper Search Agent",
        description="""A specialized AI agent for searching academic papers using the A2A protocol.

A2A MESSAGE FORMAT:
The agent accepts messages following the A2A (Agent-to-Agent) protocol structure:
{
  "message": {
    "role": "user",
    "parts": [
      {"kind": "text", "text": "your search query here"}
    ]
  }
}

INPUT:
- TEXT MESSAGES (kind: "text"): Natural language search queries for academic papers
  Examples:
  - "Find papers about transformer attention mechanisms"
  - "Search for recent papers on reinforcement learning"
  - "Papers on quantum computing"
  - "找一些关于GAN的论文"

OUTPUT:
- Paper search results: Formatted list with:
  * Paper title
  * Authors and year
  * Source (arXiv or Semantic Scholar)
  * Abstract (truncated if too long)
  * URL and PDF links (when available)

FEATURES:
- Searches multiple academic databases (arXiv and Semantic Scholar)
- Returns up to 5 most relevant papers per search
- Supports queries in multiple languages
- Provides direct links to papers and PDFs when available

TECHNICAL DETAILS:
- Protocol: A2A JSON-RPC 2.0
- Streaming: Supports real-time response streaming
- Simple stateless operation - each search is independent""",
        url=AGENT_URL,
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=get_agent_skills(),
        supportsAuthenticatedExtendedCard=False,
    )


# Validate configuration
def validate_config():
    """Validate the configuration and print warnings for missing values."""
    if not SEMANTIC_SCHOLAR_API_KEY:
        print(
            "WARNING: SEMANTIC_SCHOLAR_API_KEY environment variable is not set. Semantic Scholar search will be limited."
        )
