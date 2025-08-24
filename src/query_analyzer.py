"""
Query Analyzer module for analyzing and extracting keywords from user queries.
"""

import logging
import os
import json
from typing import Dict, List, Optional, Tuple, Union
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """Class for analyzing user queries and extracting keywords."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ):
        """
        Initialize the query analyzer.

        Args:
            api_key: API key for the LLM service
            api_url: Full API URL for the LLM service
            base_url: Base URL for the LLM service (used if api_url not provided)
            model: Model name to use
            provider: LLM provider (openai, azure, etc.)
            max_tokens: Maximum tokens for completion
            temperature: Temperature for completion

        Raises:
            ValueError: If LLM API key is not provided
        """
        # 直接硬编码配置，确保使用正确的值
        self.api_key = os.getenv("LLM_API_KEY")  # 从.env文件中获取
        self.base_url = os.getenv("LLM_BASE_URL")
        self.model = os.getenv("LLM_MODEL")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", 4096))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", 0.3))

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def analyze_query(self, query: str) -> Tuple[bool, str, Optional[List[str]]]:
        """
        Analyze the user query and extract keywords.

        Args:
            query: User query string

        Returns:
            Tuple containing:
                - is_valid: Boolean indicating if the query is valid and clear
                - search_query: Modified search query (translated to English if needed)
                - keywords: List of extracted keywords or None if query is invalid
        """
        if not query.strip():
            return False, "Empty query", None

        try:
            # Call LLM to analyze query
            analysis_result = await self._call_llm_for_analysis(query)

            if not analysis_result["is_valid"]:
                return False, analysis_result["message"], None

            return True, analysis_result["search_query"], analysis_result["keywords"]

        except Exception as e:
            logger.error(f"Error analyzing query: {e}")

            # Check if we should use a fallback
            use_fallback = (
                os.getenv("USE_FALLBACK_ON_LLM_ERROR", "false").lower() == "true"
            )

            if use_fallback:
                logger.warning(f"Using fallback for query analysis due to error: {e}")
                # Simple fallback: just use the original query
                # For Chinese queries, this might not be ideal, but it's better than failing completely
                return True, query, [query]
            else:
                # Don't fallback to original query, raise the error
                raise ValueError(
                    f"LLM query analysis failed: {e}. Please check your LLM API configuration."
                )

    async def _call_llm_for_analysis(self, query: str) -> Dict:
        """
        Call LLM API to analyze the query.

        Args:
            query: User query string

        Returns:
            Dictionary with analysis results
        """
        # LLM API key is already checked in __init__, but double-check here
        if not self.api_key:
            raise ValueError(
                "LLM API key is required for query analysis. Please set the LLM_API_KEY environment variable."
            )

        try:
            # Prepare the prompt for the LLM
            prompt = f"""
            Analyze the following academic paper search query and extract relevant English keywords.
            If the query is in a non-English language (especially Chinese), translate the key concepts to English.
            If the query is unclear or doesn't appear to be a search for academic papers, indicate that it's invalid.
            请你注意, 在请求中, 可能包含一些复杂的项目格式等等, 在这种情况下, 请你重点关注请求中"你的任务"等关键词, 避免错误判断请求的有效性


            Query: "{query}"

            Respond with a JSON object in the following format:
            {{
                "is_valid": true/false,
                "search_query": "reformulated search query in English",
                "keywords": ["keyword1", "keyword2", ...],
                "message": "explanation or error message"
            }}
            其中, keywords部分尽量保证还原Query中的请求, 不要添加一些联想出来的内容, 也避免key words出现重复的单词
            注意, keywords中每个词语应当是独立的, 且是学术短语, 如"machine learning", "attention" 等, 不要出现"ability", "mechanisms"等不明确的东西
            """

            # Prepare messages for the OpenAI API
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes academic paper search queries.",
                },
                {"role": "user", "content": prompt},
            ]

            logger.info(f"Calling OpenAI API with model {self.model}")

            # Call the OpenAI API using the SDK
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

            # Log the response for debugging
            logger.info(f"OpenAI API response: {response}")

            # Extract the content from the response
            content = response.choices[0].message.content

            # Check if response is empty
            if not content or not content.strip():
                raise ValueError("Empty response received from LLM API")

            # Log the content before parsing
            logger.info(f"Content to parse as JSON: {content}")

            try:
                # Clean the content by removing markdown code block markers if present
                cleaned_content = content
                if cleaned_content.startswith("```json") or cleaned_content.startswith(
                    "```"
                ):
                    # Remove the opening markdown code block
                    cleaned_content = cleaned_content.split("\n", 1)[1]

                if cleaned_content.endswith("```"):
                    # Remove the closing markdown code block
                    cleaned_content = cleaned_content.rsplit("\n", 1)[0]

                # Parse the JSON response
                analysis = json.loads(cleaned_content)
                return analysis
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse content as JSON: {e}")

                # Fallback: If the content looks like it might contain our expected fields
                # but isn't valid JSON, try to extract information directly
                if "is_valid" in content and (
                    "true" in content.lower() or "false" in content.lower()
                ):
                    logger.info("Attempting fallback parsing of non-JSON response")
                    is_valid = "true" in content.lower()

                    # Create a basic response
                    return {
                        "is_valid": is_valid,
                        "search_query": query if is_valid else "",
                        "keywords": [query] if is_valid else [],
                        "message": "Extracted from non-JSON response",
                    }
                else:
                    raise ValueError(
                        f"Content is not valid JSON and fallback parsing failed: {content}"
                    )
        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            # Don't return a fallback result, raise the error
            raise ValueError(
                f"LLM API call failed: {e}. Please check your LLM API configuration."
            )
