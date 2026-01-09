"""
Pydantic schemas for request/response validation.
Defines all data structures used in the API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class CacheStatus(str, Enum):
    """Cache status for responses."""
    HIT = "hit"
    MISS = "miss"


class ModelInfo(BaseModel):
    """Information about an available LLM model."""
    id: str
    name: str
    description: str
    token_limit: int
    cost_per_1k_input: float
    cost_per_1k_output: float


class EnsembleRequest(BaseModel):
    """Request schema for ensemble endpoint."""
    question: str = Field(..., min_length=1, max_length=5000, description="The question to ask")
    models: Optional[List[str]] = Field(
        default=None,
        description="List of model IDs to use. If not provided, all available models will be used."
    )
    max_tokens: Optional[int] = Field(
        default=2000,
        ge=100,
        le=4000,
        description="Maximum tokens for each model response"
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for response generation"
    )
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and clean the question."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or only whitespace")
        return cleaned


class TokenUsage(BaseModel):
    """Token usage information for a response."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ModelResponse(BaseModel):
    """Response from a single LLM model."""
    model_name: str
    response_text: str
    tokens_used: TokenUsage
    cost_estimate: float
    response_time_seconds: float
    timestamp: datetime
    cache_status: CacheStatus
    error: Optional[str] = None
    success: bool = True


class SynthesisRequest(BaseModel):
    """Request schema for synthesis endpoint."""
    question: str = Field(..., min_length=1, max_length=5000)
    model_responses: List[ModelResponse]
    synthesis_model: Optional[str] = Field(default="gpt-4o")
    max_tokens: Optional[int] = Field(default=1500, ge=100, le=3000)


class SynthesisResult(BaseModel):
    """Result of synthesizing multiple model responses."""
    synthesized_answer: str
    synthesis_model: str
    tokens_used: TokenUsage
    cost_estimate: float
    response_time_seconds: float
    timestamp: datetime
    model_contributions: Optional[Dict[str, str]] = None


class EnsembleResponse(BaseModel):
    """Complete response from the ensemble endpoint."""
    question: str
    model_responses: List[ModelResponse]
    synthesis: Optional[SynthesisResult] = None
    total_cost: float
    total_time_seconds: float
    timestamp: datetime
    cached: bool = False


class HealthResponse(BaseModel):
    """Response schema for health check."""
    status: str
    timestamp: datetime
    version: str
    api_key_configured: bool
    cache_enabled: bool


class ModelsResponse(BaseModel):
    """Response schema for models list."""
    models: List[ModelInfo]
    default_models: List[str]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RateLimitResponse(BaseModel):
    """Response when rate limit is exceeded."""
    error: str = "Rate limit exceeded"
    retry_after_seconds: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
