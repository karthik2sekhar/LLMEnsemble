"""
Caching and rate limiting utilities.
Implements in-memory caching with TTL and request rate limiting.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict, Optional
from threading import Lock
from dataclasses import dataclass, field

from ..config import get_settings

settings = get_settings()


@dataclass
class CacheEntry:
    """A single cache entry with TTL."""
    value: Any
    created_at: float
    ttl: int
    
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        return time.time() - self.created_at > self.ttl


class CacheManager:
    """
    In-memory cache with TTL support.
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self, default_ttl: int = 86400):
        """
        Initialize the cache manager.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 24 hours)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
        self._stats = {"hits": 0, "misses": 0, "sets": 0}
    
    def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            SHA256 hash string as cache key
        """
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            self._stats["hits"] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl or self.default_ttl
            )
            self._stats["sets"] += 1
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was found and deleted
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            return {
                **self._stats,
                "size": len(self._cache),
                "hit_rate": round(hit_rate, 2),
            }


@dataclass
class RateLimitEntry:
    """Track rate limit for a client."""
    requests: list = field(default_factory=list)
    
    def add_request(self, timestamp: float):
        """Add a request timestamp."""
        self.requests.append(timestamp)
    
    def cleanup(self, window: int):
        """Remove requests outside the window."""
        cutoff = time.time() - window
        self.requests = [ts for ts in self.requests if ts > cutoff]
    
    def count(self) -> int:
        """Get current request count."""
        return len(self.requests)


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self._clients: Dict[str, RateLimitEntry] = {}
        self._lock = Lock()
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if a client is allowed to make a request.
        
        Args:
            client_id: Unique identifier for the client (e.g., IP address)
            
        Returns:
            True if the request is allowed
        """
        with self._lock:
            current_time = time.time()
            
            if client_id not in self._clients:
                self._clients[client_id] = RateLimitEntry()
            
            entry = self._clients[client_id]
            entry.cleanup(self.window_seconds)
            
            if entry.count() >= self.max_requests:
                return False
            
            entry.add_request(current_time)
            return True
    
    def get_retry_after(self, client_id: str) -> int:
        """
        Get the number of seconds until the client can retry.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Seconds until retry is allowed
        """
        with self._lock:
            if client_id not in self._clients:
                return 0
            
            entry = self._clients[client_id]
            entry.cleanup(self.window_seconds)
            
            if not entry.requests:
                return 0
            
            oldest_request = min(entry.requests)
            return max(0, int(self.window_seconds - (time.time() - oldest_request)))
    
    def get_remaining(self, client_id: str) -> int:
        """
        Get the number of remaining requests for a client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Number of remaining requests in the current window
        """
        with self._lock:
            if client_id not in self._clients:
                return self.max_requests
            
            entry = self._clients[client_id]
            entry.cleanup(self.window_seconds)
            
            return max(0, self.max_requests - entry.count())
    
    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client."""
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
    
    def clear(self) -> None:
        """Clear all rate limit data."""
        with self._lock:
            self._clients.clear()


# Global instances
cache_manager = CacheManager(default_ttl=settings.cache_ttl)
rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)
