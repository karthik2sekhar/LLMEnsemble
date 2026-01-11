"""
Web Search Service for augmenting LLM responses with current information.
Supports Tavily API (primary) and Serper API (fallback).
"""

import asyncio
import hashlib
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from ..config import get_settings, TemporalConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Individual search result."""
    title: str
    url: str
    snippet: str
    source: str
    publish_date: Optional[str] = None
    score: float = 0.0


@dataclass
class SearchResponse:
    """Response from web search."""
    success: bool
    results: List[SearchResult] = field(default_factory=list)
    query: str = ""
    search_time_ms: float = 0.0
    provider: str = ""
    error_message: Optional[str] = None
    cached: bool = False
    cache_timestamp: Optional[datetime] = None
    
    @property
    def search_provider(self) -> str:
        """Alias for provider for API compatibility."""
        return self.provider
    
    @property
    def total_results(self) -> int:
        """Return total number of results."""
        return len(self.results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                    "publish_date": r.publish_date,
                    "score": r.score,
                }
                for r in self.results
            ],
            "query": self.query,
            "search_time_ms": self.search_time_ms,
            "provider": self.provider,
            "error_message": self.error_message,
            "cached": self.cached,
            "cache_timestamp": self.cache_timestamp.isoformat() if self.cache_timestamp else None,
        }


# Search result cache: query_hash -> (SearchResponse, timestamp)
_search_cache: Dict[str, tuple[SearchResponse, datetime]] = {}


class SearchService:
    """Service for web search integration."""
    
    def __init__(self):
        """Initialize the search service."""
        self.settings = get_settings()
        self.tavily_base_url = "https://api.tavily.com"
        self.serper_base_url = "https://google.serper.dev"
    
    def is_configured(self) -> bool:
        """Check if any search API is configured."""
        return bool(self.settings.tavily_api_key or self.settings.serper_api_key)
    
    async def search(self, query: str, max_results: int = 5) -> SearchResponse:
        """Alias for search_web for API compatibility."""
        return await self.search_web(query, num_results=max_results)
        
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for search query."""
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _get_cached_result(self, query: str) -> Optional[SearchResponse]:
        """Get cached search result if available and not expired."""
        cache_key = self._get_cache_key(query)
        if cache_key in _search_cache:
            response, timestamp = _search_cache[cache_key]
            ttl_hours = self.settings.search_result_cache_ttl_hours
            if datetime.utcnow() - timestamp < timedelta(hours=ttl_hours):
                logger.info(f"Search cache hit for query: {query[:50]}...")
                response.cached = True
                response.cache_timestamp = timestamp
                return response
            else:
                # Expired
                del _search_cache[cache_key]
        return None
    
    def _cache_result(self, query: str, response: SearchResponse):
        """Cache search result."""
        cache_key = self._get_cache_key(query)
        _search_cache[cache_key] = (response, datetime.utcnow())
        logger.info(f"Cached search result for query: {query[:50]}...")
    
    async def search_web(
        self,
        query: str,
        num_results: Optional[int] = None
    ) -> SearchResponse:
        """
        Search the web for current information.
        
        Args:
            query: The search query
            num_results: Number of results to return (default from settings)
            
        Returns:
            SearchResponse with results or error
        """
        if num_results is None:
            num_results = self.settings.search_max_results
        
        # Check cache first
        cached = self._get_cached_result(query)
        if cached:
            return cached
        
        start_time = datetime.utcnow()
        
        # Try primary provider
        provider = self.settings.search_api_provider
        
        if provider == "tavily" and self.settings.tavily_api_key:
            response = await self._search_tavily(query, num_results)
        elif provider == "serper" and self.settings.serper_api_key:
            response = await self._search_serper(query, num_results)
        else:
            # Try fallback
            if self.settings.tavily_api_key:
                response = await self._search_tavily(query, num_results)
            elif self.settings.serper_api_key:
                response = await self._search_serper(query, num_results)
            else:
                logger.warning("No search API configured")
                return SearchResponse(
                    success=False,
                    query=query,
                    error_message="No search API configured. Set TAVILY_API_KEY or SERPER_API_KEY.",
                    provider="none"
                )
        
        # Calculate search time
        response.search_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Cache successful results
        if response.success:
            self._cache_result(query, response)
        
        return response
    
    async def _search_tavily(self, query: str, num_results: int) -> SearchResponse:
        """Search using Tavily API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.tavily_base_url}/search",
                    json={
                        "api_key": self.settings.tavily_api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "include_answer": False,
                        "include_raw_content": False,
                        "max_results": num_results,
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Tavily API error: {response.status_code} - {response.text}")
                    return SearchResponse(
                        success=False,
                        query=query,
                        error_message=f"Tavily API error: {response.status_code}",
                        provider="tavily"
                    )
                
                data = response.json()
                results = []
                
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", "")[:500],
                        source=self._extract_domain(item.get("url", "")),
                        publish_date=item.get("published_date"),
                        score=item.get("score", 0.0)
                    ))
                
                logger.info(f"Tavily search returned {len(results)} results for: {query[:50]}...")
                
                return SearchResponse(
                    success=True,
                    results=results,
                    query=query,
                    provider="tavily"
                )
                
        except httpx.TimeoutException:
            logger.error("Tavily API timeout")
            return SearchResponse(
                success=False,
                query=query,
                error_message="Search request timed out",
                provider="tavily"
            )
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return SearchResponse(
                success=False,
                query=query,
                error_message=str(e),
                provider="tavily"
            )
    
    async def _search_serper(self, query: str, num_results: int) -> SearchResponse:
        """Search using Serper API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.serper_base_url}/search",
                    headers={
                        "X-API-KEY": self.settings.serper_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "num": num_results
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Serper API error: {response.status_code} - {response.text}")
                    return SearchResponse(
                        success=False,
                        query=query,
                        error_message=f"Serper API error: {response.status_code}",
                        provider="serper"
                    )
                
                data = response.json()
                results = []
                
                for item in data.get("organic", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", "")[:500],
                        source=self._extract_domain(item.get("link", "")),
                        publish_date=item.get("date"),
                        score=item.get("position", 0) / 10.0  # Convert position to score
                    ))
                
                logger.info(f"Serper search returned {len(results)} results for: {query[:50]}...")
                
                return SearchResponse(
                    success=True,
                    results=results,
                    query=query,
                    provider="serper"
                )
                
        except httpx.TimeoutException:
            logger.error("Serper API timeout")
            return SearchResponse(
                success=False,
                query=query,
                error_message="Search request timed out",
                provider="serper"
            )
        except Exception as e:
            logger.error(f"Serper search error: {e}")
            return SearchResponse(
                success=False,
                query=query,
                error_message=str(e),
                provider="serper"
            )
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return url
    
    def format_search_context(
        self,
        search_response: SearchResponse,
        max_results: int = 5
    ) -> str:
        """
        Format search results as context for LLM.
        
        Args:
            search_response: The search response to format
            max_results: Maximum number of results to include
            
        Returns:
            Formatted context string
        """
        if not search_response.success or not search_response.results:
            return ""
        
        current_date = datetime.now().strftime("%B %d, %Y")
        
        lines = [
            f"**Current Information from Web Search (as of {current_date}):**",
            "",
        ]
        
        for i, result in enumerate(search_response.results[:max_results], 1):
            date_str = f" ({result.publish_date})" if result.publish_date else ""
            lines.extend([
                f"**Source {i}: {result.source}{date_str}**",
                f"Title: {result.title}",
                f"Content: {result.snippet}",
                "",
            ])
        
        lines.extend([
            "---",
            f"*Note: The above information was retrieved from web search on {current_date}. "
            f"LLM knowledge cutoff is {TemporalConfig.MODEL_KNOWLEDGE_CUTOFF_DISPLAY}.*",
            "",
        ])
        
        return "\n".join(lines)
    
    def clear_cache(self):
        """Clear the search result cache."""
        global _search_cache
        _search_cache.clear()
        logger.info("Search cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_queries": len(_search_cache),
            "ttl_hours": self.settings.search_result_cache_ttl_hours,
        }


# Singleton instance
search_service = SearchService()
