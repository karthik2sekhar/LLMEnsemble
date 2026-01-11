"""
Configuration management for the LLM Ensemble application.
Handles environment variables, model settings, and application configuration.
"""

import os
import re
from typing import Optional, Dict, List
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from datetime import datetime


class TemporalConfig:
    """Configuration for temporal query detection."""
    
    # Model knowledge cutoff date
    MODEL_KNOWLEDGE_CUTOFF = "2023-10"
    MODEL_KNOWLEDGE_CUTOFF_DISPLAY = "October 2023"
    
    # Temporal keyword patterns (case-insensitive regex)
    TEMPORAL_KEYWORDS = [
        r'\blatest\b',
        r'\bcurrent\b',
        r'\bnow\b',
        r'\btoday\b',
        r'\brecent\b',
        r'\brecently\b',
        r'\b202[4-9]\b',  # Years 2024-2029
        r'\b203\d\b',     # Years 2030-2039
        r'\bthis\s+year\b',
        r'\bright\s+now\b',
        r'\bup[- ]to[- ]date\b',
        r'\bnewest\b',
        r'\bmost\s+recent\b',
        r'\bbreaking\b',
        r'\btrending\b',
        r'\bthis\s+month\b',
        r'\bthis\s+week\b',
        r'\bhappening\s+now\b',
        r'\bjust\s+announced\b',
        r'\bnew\s+in\s+\d{4}\b',
        r'\bas\s+of\s+\d{4}\b',
        r'\bjanuary|february|march|april|may|june|july|august|september|october|november|december\b.*\b202[4-9]\b',
    ]
    
    # Compiled patterns for efficiency
    _compiled_patterns = None
    _combined_pattern = None
    
    @classmethod
    def get_compiled_patterns(cls) -> List[re.Pattern]:
        """Get compiled regex patterns (cached)."""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in cls.TEMPORAL_KEYWORDS
            ]
        return cls._compiled_patterns
    
    @classmethod
    def get_compiled_pattern(cls) -> re.Pattern:
        """Get a single combined pattern for findall (cached)."""
        if cls._combined_pattern is None:
            # Combine all patterns into one with alternation
            combined = '|'.join(f'({p})' for p in cls.TEMPORAL_KEYWORDS)
            cls._combined_pattern = re.compile(combined, re.IGNORECASE)
        return cls._combined_pattern
    
    @classmethod
    def get_current_year(cls) -> int:
        """Get current year for temporal detection."""
        return datetime.now().year
    
    @classmethod
    def is_future_year(cls, year: int) -> bool:
        """Check if a year reference is current or future."""
        cutoff_year = int(cls.MODEL_KNOWLEDGE_CUTOFF.split("-")[0])
        return year > cutoff_year


class ModelConfig:
    """Configuration for individual LLM models."""
    
    # Model costs per 1K tokens (input/output)
    COSTS = {
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-5.2": {"input": 0.02, "output": 0.06},  # Example costs, update as needed
    }

    # Model token limits
    TOKEN_LIMITS = {
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-5.2": 128000,  # Example token limit, update as needed
    }

    # Model descriptions for UI tooltips
    DESCRIPTIONS = {
        "gpt-4-turbo": "Primary reasoning model - excellent for complex analysis and detailed explanations",
        "gpt-4o": "Multimodal and creative model - great for diverse perspectives and creative solutions",
        "gpt-4o-mini": "Fast and cost-efficient model - ideal for quick responses and simple queries",
        "gpt-5.2": "Latest generation model - advanced reasoning, creativity, and efficiency (example description)",
    }
    
    @classmethod
    def get_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost for a model call."""
        if model not in cls.COSTS:
            return 0.0
        costs = cls.COSTS[model]
        return (input_tokens * costs["input"] / 1000) + (output_tokens * costs["output"] / 1000)
    
    @classmethod
    def get_available_models(cls) -> list:
        """Return list of available models with their configurations."""
        return [
            {
                "id": model_id,
                "name": model_id,
                "description": cls.DESCRIPTIONS.get(model_id, ""),
                "token_limit": cls.TOKEN_LIMITS.get(model_id, 128000),
                "cost_per_1k_input": cls.COSTS.get(model_id, {}).get("input", 0),
                "cost_per_1k_output": cls.COSTS.get(model_id, {}).get("output", 0),
            }
            for model_id in cls.COSTS.keys()
        ]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_org_id: Optional[str] = Field(default=None, env="OPENAI_ORG_ID")
    
    # Database Configuration
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=60, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Cache Configuration
    cache_ttl: int = Field(default=86400, env="CACHE_TTL")  # 24 hours in seconds
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    
    # API Configuration
    max_question_length: int = Field(default=5000, env="MAX_QUESTION_LENGTH")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    
    # CORS Configuration
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", env="CORS_ORIGINS")
    
    # Default models to use
    default_models: str = Field(
        default="gpt-4-turbo,gpt-4o,gpt-4o-mini,gpt-5.2",
        env="DEFAULT_MODELS"
    )
    
    # Synthesis model
    synthesis_model: str = Field(default="gpt-5.2", env="SYNTHESIS_MODEL")
    
    # Temporal Detection Configuration
    temporal_upgrade_enabled: bool = Field(default=True, env="TEMPORAL_UPGRADE_ENABLED")
    require_search_enabled: bool = Field(default=True, env="REQUIRE_SEARCH_ENABLED")
    
    # Web Search API Configuration
    search_api_provider: str = Field(default="perplexity", env="SEARCH_API_PROVIDER")
    tavily_api_key: str = Field(default="", env="TAVILY_API_KEY")
    serper_api_key: str = Field(default="", env="SERPER_API_KEY")
    search_result_cache_ttl_hours: int = Field(default=24, env="SEARCH_RESULT_CACHE_TTL_HOURS")
    search_max_results: int = Field(default=5, env="SEARCH_MAX_RESULTS")
    
    # Perplexity API Configuration
    perplexity_api_key: str = Field(default="", env="PERPLEXITY_API_KEY")
    perplexity_model: str = Field(default="sonar", env="PERPLEXITY_MODEL")
    perplexity_enabled: bool = Field(default=True, env="PERPLEXITY_ENABLED")
    perplexity_timeout: int = Field(default=30, env="PERPLEXITY_TIMEOUT")
    perplexity_recency_filter: str = Field(default="month", env="PERPLEXITY_RECENCY_FILTER")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def cors_origins_list(self) -> list:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def default_models_list(self) -> list:
        """Return default models as a list."""
        return [model.strip() for model in self.default_models.split(",")]
    
    def validate_api_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key and self.openai_api_key.strip())
    
    def validate_search_api_key(self) -> bool:
        """Check if search API key is configured."""
        if self.search_api_provider == "tavily":
            return bool(self.tavily_api_key and self.tavily_api_key.strip())
        elif self.search_api_provider == "serper":
            return bool(self.serper_api_key and self.serper_api_key.strip())
        return False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
