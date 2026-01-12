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


# ==================== Query Router Schemas ====================

class ComplexityLevel(str, Enum):
    """Query complexity levels for routing."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class QueryIntent(str, Enum):
    """Query intent classification."""
    FACTUAL = "factual"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    PROCEDURAL = "procedural"
    COMPARATIVE = "comparative"


class QueryDomain(str, Enum):
    """Query domain classification."""
    CODING = "coding"
    TECHNICAL = "technical"
    GENERAL = "general"
    CREATIVE = "creative"
    RESEARCH = "research"


class TemporalScope(str, Enum):
    """Temporal scope of a query."""
    EVERGREEN = "evergreen"  # Timeless facts that don't change
    HISTORICAL = "historical"  # Past events with established facts
    CURRENT = "current"  # Recent/ongoing events, current state
    FUTURE = "future"  # Predictions, upcoming events


class TemporalDetectionResult(BaseModel):
    """Result of temporal detection analysis."""
    is_temporal: bool = False
    temporal_scope: TemporalScope = TemporalScope.EVERGREEN
    requires_current_data: bool = False
    detected_keywords: List[str] = Field(default_factory=list)
    detected_years: List[int] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""


class QueryClassification(BaseModel):
    """Classification result for a query."""
    complexity: ComplexityLevel
    intent: QueryIntent
    domain: QueryDomain
    requires_search: bool = False
    temporal_scope: TemporalScope = TemporalScope.EVERGREEN
    recommended_models: List[str]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)


class RoutingDecision(BaseModel):
    """Routing decision based on classification."""
    models_to_use: List[str]
    use_synthesis: bool
    synthesis_model: Optional[str] = None
    estimated_cost: float
    estimated_time_seconds: float
    routing_rationale: str
    minimum_models_for_temporal: Optional[int] = None
    add_web_search_recommendation: bool = False


class CostBreakdown(BaseModel):
    """Cost breakdown by model."""
    model_costs: Dict[str, float]
    synthesis_cost: float = 0.0
    classification_cost: float = 0.0
    search_cost: float = 0.0
    total_cost: float
    full_ensemble_cost: float
    savings: float
    savings_percentage: float


class ExecutionMetrics(BaseModel):
    """Execution time metrics by stage."""
    classification_time_ms: float
    temporal_detection_time_ms: float = 0.0
    search_time_ms: float = 0.0
    model_execution_time_ms: Dict[str, float]
    synthesis_time_ms: float = 0.0
    total_time_ms: float


class RouteAndAnswerRequest(BaseModel):
    """Request schema for intelligent routing endpoint."""
    question: str = Field(..., min_length=1, max_length=5000, description="The question to ask")
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
    override_models: Optional[List[str]] = Field(
        default=None,
        description="Override automatic model selection with specific models"
    )
    force_synthesis: Optional[bool] = Field(
        default=None,
        description="Force synthesis regardless of complexity"
    )
    enable_search: bool = Field(
        default=True,
        description="Enable web search for temporal queries"
    )
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and clean the question."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or only whitespace")
        return cleaned


class RouteAndAnswerResponse(BaseModel):
    """Response schema for intelligent routing endpoint."""
    question: str
    classification: QueryClassification
    routing_decision: RoutingDecision
    models_used: List[str]
    individual_responses: List[ModelResponse]
    final_answer: str
    synthesis: Optional[SynthesisResult] = None
    cost_breakdown: CostBreakdown
    execution_metrics: ExecutionMetrics
    timestamp: datetime
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    # Temporal/Search fields
    temporal_detection: Optional[TemporalDetectionResult] = None
    was_search_used: bool = False
    search_results: Optional[Dict[str, Any]] = None
    routing_override_applied: bool = False
    routing_override_reason: Optional[str] = None
    ui_warning_message: Optional[str] = None


class RoutingSettingsRequest(BaseModel):
    """User configurable routing settings."""
    complexity_threshold_for_multiple_models: ComplexityLevel = ComplexityLevel.MODERATE
    max_cost_per_query: Optional[float] = Field(default=None, ge=0.0)
    always_use_synthesis: bool = False
    preferred_models: Optional[List[str]] = None


class RoutingStats(BaseModel):
    """Statistics for routing decisions."""
    total_queries: int
    simple_queries: int
    moderate_queries: int
    complex_queries: int
    total_cost: float
    total_savings: float
    average_savings_percentage: float
    model_usage_distribution: Dict[str, int]
    fallback_count: int


# ==================== Time-Travel Answer Schemas ====================

class TemporalSensitivityLevel(str, Enum):
    """Classification of how temporally sensitive a question is."""
    HIGH = "high"      # Answer changes significantly over time
    MEDIUM = "medium"  # Answer may change moderately  
    LOW = "low"        # Answer is mostly timeless
    NONE = "none"      # Answer doesn't change at all


class TimeSnapshot(BaseModel):
    """A snapshot of the answer at a specific point in time."""
    date: datetime
    date_label: str  # e.g., "Jan 1, 2024 - Pre-GPT-4o Era"
    answer: str
    key_changes: List[str] = Field(default_factory=list)
    data_points: List[str] = Field(default_factory=list)
    model_used: str = ""
    tokens_used: int = 0
    cost_estimate: float = 0.0
    response_time_seconds: float = 0.0


class TimeTravelRequest(BaseModel):
    """Request schema for time-travel endpoint."""
    question: str = Field(..., min_length=1, max_length=5000, description="The question to analyze")
    force_time_travel: bool = Field(
        default=False,
        description="Force time-travel analysis even for low-sensitivity questions"
    )
    max_snapshots: Optional[int] = Field(
        default=None,
        ge=2,
        le=7,
        description="Maximum number of time snapshots to generate"
    )
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and clean the question."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or only whitespace")
        return cleaned


class TimeTravelResponse(BaseModel):
    """Response schema for time-travel endpoint."""
    question: str
    temporal_sensitivity: TemporalSensitivityLevel
    sensitivity_reasoning: str
    is_eligible: bool = True
    skip_reason: Optional[str] = None
    snapshots: List[TimeSnapshot] = Field(default_factory=list)
    evolution_narrative: str = ""
    insights: List[str] = Field(default_factory=list)
    change_velocity: str = ""  # "fast", "moderate", "slow", "minimal"
    future_outlook: str = ""
    total_cost: float = 0.0
    total_time_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

