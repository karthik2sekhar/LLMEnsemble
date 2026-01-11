"""
Perplexity API Service for real-time web search with LLM reasoning.
Combines web search + reasoning in a single API call for temporal queries.
"""

import asyncio
import httpx
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from ..config import get_settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PerplexityCitation:
    """Citation from Perplexity search."""
    title: str
    url: str
    snippet: str = ""
    date: Optional[str] = None


@dataclass
class PerplexityResponse:
    """Response from Perplexity API."""
    success: bool
    answer: str = ""
    citations: List[PerplexityCitation] = field(default_factory=list)
    query: str = ""
    model: str = ""
    timestamp: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: Optional[str] = None
    response_time_ms: float = 0.0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def citations_count(self) -> int:
        return len(self.citations)
    
    def calculate_cost(self) -> Dict[str, float]:
        """Calculate cost based on Perplexity pricing."""
        # pplx-70b-online pricing: $0.007/1K input, $0.028/1K output
        input_cost = (self.input_tokens / 1000) * 0.007
        output_cost = (self.output_tokens / 1000) * 0.028
        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(input_cost + output_cost, 6),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "answer": self.answer,
            "citations": [
                {
                    "title": c.title,
                    "url": c.url,
                    "snippet": c.snippet,
                    "date": c.date,
                }
                for c in self.citations
            ],
            "query": self.query,
            "model": self.model,
            "timestamp": self.timestamp,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "response_time_ms": self.response_time_ms,
            "cost": self.calculate_cost(),
        }


class PerplexityService:
    """Service for Perplexity API integration."""
    
    PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
    
    def __init__(self):
        """Initialize the Perplexity service."""
        self.settings = get_settings()
        self._api_key = getattr(self.settings, 'perplexity_api_key', None)
    
    def is_configured(self) -> bool:
        """Check if Perplexity API is configured."""
        return bool(self._api_key)
    
    async def search(
        self,
        query: str,
        model: str = "sonar",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        recency_filter: str = "month",
    ) -> PerplexityResponse:
        """
        Search the web and get reasoned answer using Perplexity API.
        
        Args:
            query: The search query/question
            model: Perplexity model to use (sonar, sonar-pro, etc.)
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.0-1.0)
            recency_filter: Filter for search results (day, week, month, year)
            
        Returns:
            PerplexityResponse with answer and citations
        """
        if not self.is_configured():
            logger.warning("Perplexity API key not configured")
            return PerplexityResponse(
                success=False,
                query=query,
                error_message="Perplexity API key not configured. Set PERPLEXITY_API_KEY in environment.",
                timestamp=datetime.utcnow().isoformat(),
            )
        
        start_time = datetime.utcnow()
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides accurate, up-to-date information based on web search results. Always cite your sources."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "search_recency_filter": recency_filter,
            "return_citations": True,
            "return_related_questions": False,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.PERPLEXITY_API_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
            
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Extract answer
            answer = ""
            if result.get("choices"):
                answer = result["choices"][0].get("message", {}).get("content", "")
            
            # Extract citations
            citations = []
            raw_citations = result.get("citations", [])
            for cite in raw_citations:
                if isinstance(cite, str):
                    # Simple URL string
                    citations.append(PerplexityCitation(
                        title=cite,
                        url=cite,
                    ))
                elif isinstance(cite, dict):
                    citations.append(PerplexityCitation(
                        title=cite.get("title", cite.get("url", "Unknown")),
                        url=cite.get("url", ""),
                        snippet=cite.get("snippet", ""),
                        date=cite.get("date"),
                    ))
            
            # Extract token usage
            usage = result.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            logger.info(
                f"Perplexity search completed: {len(citations)} citations, "
                f"{input_tokens + output_tokens} tokens, {elapsed_ms:.0f}ms"
            )
            
            return PerplexityResponse(
                success=True,
                answer=answer,
                citations=citations,
                query=query,
                model=model,
                timestamp=datetime.utcnow().isoformat(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                response_time_ms=elapsed_ms,
            )
            
        except httpx.TimeoutException:
            logger.error("Perplexity API request timed out")
            return PerplexityResponse(
                success=False,
                query=query,
                error_message="Request timed out after 30 seconds",
                timestamp=datetime.utcnow().isoformat(),
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity API HTTP error: {e.response.status_code}")
            return PerplexityResponse(
                success=False,
                query=query,
                error_message=f"HTTP error: {e.response.status_code}",
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return PerplexityResponse(
                success=False,
                query=query,
                error_message=str(e),
                timestamp=datetime.utcnow().isoformat(),
            )
    
    def format_for_context(self, response: PerplexityResponse) -> str:
        """
        Format Perplexity response as context for other models.
        
        Args:
            response: PerplexityResponse from search
            
        Returns:
            Formatted string to prepend to questions
        """
        if not response.success or not response.answer:
            return ""
        
        try:
            timestamp = datetime.fromisoformat(response.timestamp.replace('Z', '+00:00'))
            formatted_time = timestamp.strftime("%B %d, %Y at %I:%M %p UTC")
        except:
            formatted_time = response.timestamp
        
        lines = [
            "=" * 60,
            "CURRENT INFORMATION FROM WEB SEARCH",
            f"Retrieved: {formatted_time}",
            f"Source: Perplexity API ({response.model})",
            "=" * 60,
            "",
            response.answer,
            "",
        ]
        
        if response.citations:
            lines.append("Sources:")
            for i, cite in enumerate(response.citations[:5], 1):
                lines.append(f"  [{i}] {cite.title}")
                if cite.url:
                    lines.append(f"      URL: {cite.url}")
                if cite.date:
                    lines.append(f"      Date: {cite.date}")
            lines.append("")
        
        lines.extend([
            "=" * 60,
            "Use the above current information to answer the user's question.",
            "=" * 60,
            "",
        ])
        
        return "\n".join(lines)


# Singleton instance
perplexity_service = PerplexityService()
