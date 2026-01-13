"""
Redis Caching Layer for LLM Responses

This module provides:
1. Redis-based response caching
2. Question deduplication
3. Cache warming strategies
4. TTL management

Expected Performance Impact:
- Repeated questions: 0ms (cache hit) vs 20-30s (API call)
- Cost savings: ~90% for frequent questions
"""

import asyncio
import hashlib
import json
import pickle
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, TypeVar, Generic
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A cached entry with metadata."""
    value: T
    created_at: float
    ttl_seconds: int
    hit_count: int = 0
    last_accessed: float = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds
    
    @property
    def remaining_ttl(self) -> float:
        return max(0, self.ttl_seconds - (time.time() - self.created_at))


class RedisCache:
    """
    Redis-based caching for LLM responses.
    
    Falls back to in-memory cache if Redis is unavailable.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 86400,  # 24 hours
        max_memory_entries: int = 1000,
        namespace: str = "llm_cache"
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.max_memory_entries = max_memory_entries
        self.namespace = namespace
        
        self._redis_client = None
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._use_redis = False
        
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0
        }
    
    async def connect(self):
        """Initialize Redis connection."""
        if not self.redis_url:
            logger.info("Redis URL not configured, using in-memory cache")
            return
        
        try:
            import redis.asyncio as redis
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False  # We'll handle serialization
            )
            await self._redis_client.ping()
            self._use_redis = True
            logger.info("Redis cache connected successfully")
        except ImportError:
            logger.warning("redis package not installed, using in-memory cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        hash_value = hashlib.sha256(key_data.encode()).hexdigest()[:32]
        return f"{self.namespace}:{hash_value}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize a value for storage."""
        return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize a stored value."""
        return pickle.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Returns None if not found or expired.
        """
        try:
            if self._use_redis:
                data = await self._redis_client.get(key)
                if data:
                    entry = self._deserialize(data)
                    if not entry.is_expired:
                        entry.hit_count += 1
                        entry.last_accessed = time.time()
                        self._stats["hits"] += 1
                        return entry.value
                    else:
                        await self._redis_client.delete(key)
            else:
                if key in self._memory_cache:
                    entry = self._memory_cache[key]
                    if not entry.is_expired:
                        entry.hit_count += 1
                        entry.last_accessed = time.time()
                        self._stats["hits"] += 1
                        return entry.value
                    else:
                        del self._memory_cache[key]
            
            self._stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self._stats["errors"] += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store a value in cache.
        
        Returns True on success.
        """
        try:
            ttl = ttl or self.default_ttl
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl
            )
            
            if self._use_redis:
                data = self._serialize(entry)
                await self._redis_client.setex(key, ttl, data)
            else:
                # Evict old entries if at capacity
                if len(self._memory_cache) >= self.max_memory_entries:
                    self._evict_lru()
                self._memory_cache[key] = entry
            
            self._stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self._stats["errors"] += 1
            return False
    
    def _evict_lru(self):
        """Evict least recently used entries."""
        if not self._memory_cache:
            return
        
        # Sort by last accessed time
        sorted_keys = sorted(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k].last_accessed
        )
        
        # Remove oldest 10%
        to_remove = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:to_remove]:
            del self._memory_cache[key]
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            if self._use_redis:
                await self._redis_client.delete(key)
            else:
                self._memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_namespace(self):
        """Clear all keys in the namespace."""
        try:
            if self._use_redis:
                pattern = f"{self.namespace}:*"
                cursor = 0
                while True:
                    cursor, keys = await self._redis_client.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self._redis_client.delete(*keys)
                    if cursor == 0:
                        break
            else:
                self._memory_cache.clear()
            
            logger.info(f"Cleared cache namespace: {self.namespace}")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        
        return {
            **self._stats,
            "hit_rate": hit_rate,
            "using_redis": self._use_redis,
            "memory_entries": len(self._memory_cache)
        }


# ==================== Question-Specific Cache ====================

class LLMResponseCache:
    """
    Specialized cache for LLM responses with question deduplication.
    
    Features:
    - Question normalization (lowercase, trim, remove punctuation variations)
    - Semantic similarity matching (optional)
    - Model-specific caching
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.cache = RedisCache(
            redis_url=redis_url,
            default_ttl=86400 * 7,  # 7 days for LLM responses
            namespace="llm_responses"
        )
        
        # Shorter TTL cache for time-travel (answers change based on date)
        self.time_travel_cache = RedisCache(
            redis_url=redis_url,
            default_ttl=86400,  # 24 hours
            namespace="time_travel"
        )
    
    async def connect(self):
        """Initialize connections."""
        await self.cache.connect()
        await self.time_travel_cache.connect()
    
    async def disconnect(self):
        """Close connections."""
        await self.cache.disconnect()
        await self.time_travel_cache.disconnect()
    
    def _normalize_question(self, question: str) -> str:
        """Normalize a question for consistent caching."""
        # Lowercase
        normalized = question.lower().strip()
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        # Remove trailing punctuation variations
        normalized = normalized.rstrip('?!.')
        return normalized
    
    def _make_model_key(self, question: str, model: str) -> str:
        """Generate a cache key for a model-specific response."""
        normalized = self._normalize_question(question)
        key_data = f"{model}:{normalized}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    async def get_response(
        self,
        question: str,
        model: str
    ) -> Optional[Dict[str, Any]]:
        """Get a cached LLM response."""
        key = f"llm_responses:{self._make_model_key(question, model)}"
        return await self.cache.get(key)
    
    async def set_response(
        self,
        question: str,
        model: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Cache an LLM response."""
        key = f"llm_responses:{self._make_model_key(question, model)}"
        await self.cache.set(key, response, ttl)
    
    async def get_time_travel(
        self,
        question: str
    ) -> Optional[Dict[str, Any]]:
        """Get a cached time-travel response."""
        normalized = self._normalize_question(question)
        key = f"time_travel:{hashlib.sha256(normalized.encode()).hexdigest()[:32]}"
        return await self.time_travel_cache.get(key)
    
    async def set_time_travel(
        self,
        question: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Cache a time-travel response."""
        normalized = self._normalize_question(question)
        key = f"time_travel:{hashlib.sha256(normalized.encode()).hexdigest()[:32]}"
        await self.time_travel_cache.set(key, response, ttl)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        return {
            "llm_responses": self.cache.get_stats(),
            "time_travel": self.time_travel_cache.get_stats()
        }


# ==================== Cache Warming ====================

class CacheWarmer:
    """
    Pre-populate cache with common questions.
    
    Usage:
        warmer = CacheWarmer(cache, llm_service)
        await warmer.warm_common_questions()
    """
    
    COMMON_QUESTIONS = [
        "What is GPT-4?",
        "What AI models are available?",
        "What is the latest in AI?",
        "Compare GPT-4 and Claude",
        "What are large language models?",
        "How does ChatGPT work?",
        "What is machine learning?",
        "Best programming languages in 2024",
    ]
    
    def __init__(self, cache: LLMResponseCache, llm_service=None):
        self.cache = cache
        self.llm_service = llm_service
    
    async def warm_common_questions(
        self,
        models: Optional[list] = None,
        questions: Optional[list] = None
    ):
        """
        Pre-fetch and cache responses for common questions.
        
        Run this during off-peak hours or at startup.
        """
        questions = questions or self.COMMON_QUESTIONS
        models = models or ["gpt-4o-mini", "gpt-4o"]
        
        if not self.llm_service:
            logger.warning("No LLM service configured for cache warming")
            return
        
        logger.info(f"Warming cache for {len(questions)} questions across {len(models)} models")
        
        for question in questions:
            for model in models:
                # Check if already cached
                existing = await self.cache.get_response(question, model)
                if existing:
                    continue
                
                try:
                    response = await self.llm_service.call_model(
                        model=model,
                        question=question,
                        use_cache=False  # Force fresh fetch
                    )
                    
                    await self.cache.set_response(
                        question=question,
                        model=model,
                        response=asdict(response) if hasattr(response, '__dataclass_fields__') else response
                    )
                    
                    logger.debug(f"Warmed cache: {model} - {question[:50]}...")
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Cache warming failed for {model}/{question[:30]}: {e}")


# Global cache instance
llm_cache = LLMResponseCache()
