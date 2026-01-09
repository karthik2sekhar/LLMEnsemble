"""
Database models for the application.
Currently using in-memory storage, but structured for easy database integration.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class QueryHistory:
    """Represents a historical query in the system."""
    id: str = field(default_factory=lambda: str(uuid4()))
    question: str = ""
    models_used: List[str] = field(default_factory=list)
    responses: Dict[str, Any] = field(default_factory=dict)
    synthesized_answer: Optional[str] = None
    total_cost: float = 0.0
    total_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None  # For future user authentication
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "question": self.question,
            "models_used": self.models_used,
            "responses": self.responses,
            "synthesized_answer": self.synthesized_answer,
            "total_cost": self.total_cost,
            "total_time": self.total_time,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
        }


@dataclass
class UsageStats:
    """Tracks usage statistics for monitoring."""
    total_queries: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    queries_by_model: Dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def record_query(self, model: str, tokens: int, cost: float, cached: bool = False):
        """Record a new query."""
        self.total_queries += 1
        self.total_cost += cost
        self.total_tokens += tokens
        self.queries_by_model[model] = self.queries_by_model.get(model, 0) + 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        self.last_updated = datetime.utcnow()
    
    def record_error(self):
        """Record an error."""
        self.errors += 1
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_queries": self.total_queries,
            "total_cost": round(self.total_cost, 4),
            "total_tokens": self.total_tokens,
            "queries_by_model": self.queries_by_model,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(
                self.cache_hits / max(self.cache_hits + self.cache_misses, 1) * 100, 2
            ),
            "errors": self.errors,
            "last_updated": self.last_updated.isoformat(),
        }


# Global usage stats instance
usage_stats = UsageStats()
