"""
Configuration management for the LLM Ensemble application.
Handles environment variables, model settings, and application configuration.
"""

import os
from typing import Optional, Dict
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class ModelConfig:
    """Configuration for individual LLM models."""
    
    # Model costs per 1K tokens (input/output)
    COSTS = {
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    }
    
    # Model token limits
    TOKEN_LIMITS = {
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
    }
    
    # Model descriptions for UI tooltips
    DESCRIPTIONS = {
        "gpt-4-turbo": "Primary reasoning model - excellent for complex analysis and detailed explanations",
        "gpt-4o": "Multimodal and creative model - great for diverse perspectives and creative solutions",
        "gpt-4o-mini": "Fast and cost-efficient model - ideal for quick responses and simple queries",
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
        default="gpt-4-turbo,gpt-4o,gpt-4o-mini",
        env="DEFAULT_MODELS"
    )
    
    # Synthesis model
    synthesis_model: str = Field(default="gpt-4o", env="SYNTHESIS_MODEL")
    
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
