"""
Ensemble routes for LLM ensemble operations.
Handles model selection, parallel calls, and synthesis.
"""

import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from ..config import get_settings, ModelConfig
from ..schemas import (
    EnsembleRequest,
    EnsembleResponse,
    SynthesisRequest,
    SynthesisResult,
    ModelResponse,
    ModelsResponse,
    ModelInfo,
    ErrorResponse,
    RateLimitResponse,
)
from ..services.llm_service import llm_service
from ..services.synthesis_service import synthesis_service
from ..utils.cache import rate_limiter
from ..utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["ensemble"])
settings = get_settings()


async def check_rate_limit(request: Request):
    """Dependency to check rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_ip):
        retry_after = rate_limiter.get_retry_after(client_ip)
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after_seconds": retry_after,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


async def validate_api_key():
    """Dependency to validate API key is configured."""
    if not settings.validate_api_key():
        logger.error("API key not configured")
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    Get list of available LLM models.
    
    Returns information about all available models including:
    - Model ID and name
    - Description of model capabilities
    - Token limits
    - Pricing information
    """
    logger.info("Fetching available models")
    
    models_data = ModelConfig.get_available_models()
    models = [ModelInfo(**model) for model in models_data]
    
    return ModelsResponse(
        models=models,
        default_models=settings.default_models_list
    )


@router.post("/ensemble", response_model=EnsembleResponse)
async def ensemble_query(
    request: EnsembleRequest,
    _rate_limit: None = Depends(check_rate_limit),
    _api_key: None = Depends(validate_api_key),
):
    """
    Query multiple LLM models in parallel and synthesize responses.
    
    This endpoint:
    1. Validates the question
    2. Calls selected models in parallel
    3. Synthesizes responses into a unified answer
    4. Returns all individual responses plus the synthesis
    
    Request body:
    - question: The question to ask (required, max 5000 chars)
    - models: List of model IDs to use (optional, defaults to all)
    - max_tokens: Max tokens per response (optional, default 2000)
    - temperature: Temperature for generation (optional, default 0.7)
    """
    start_time = time.time()
    timestamp = datetime.utcnow()
    
    logger.info(f"Ensemble query received: '{request.question[:100]}...'")
    
    # Determine which models to use
    available_models = [m["id"] for m in ModelConfig.get_available_models()]
    
    if request.models:
        # Validate requested models
        invalid_models = [m for m in request.models if m not in available_models]
        if invalid_models:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model(s): {invalid_models}. Available: {available_models}"
            )
        models_to_use = request.models
    else:
        models_to_use = settings.default_models_list
    
    logger.info(f"Using models: {models_to_use}")
    
    # Call models in parallel
    model_responses = await llm_service.call_models_parallel(
        models=models_to_use,
        question=request.question,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )
    
    # Check if any models succeeded
    successful_responses = [r for r in model_responses if r.success]
    
    if not successful_responses:
        logger.error("All model calls failed")
        raise HTTPException(
            status_code=503,
            detail="All model calls failed. Please try again later."
        )
    
    # Synthesize responses
    synthesis_result = await synthesis_service.synthesize(
        question=request.question,
        model_responses=model_responses,
    )
    
    # Calculate totals
    total_cost = sum(r.cost_estimate for r in model_responses) + synthesis_result.cost_estimate
    total_time = time.time() - start_time
    
    # Check if all responses were cached
    all_cached = all(r.cache_status.value == "hit" for r in model_responses if r.success)
    
    logger.info(f"Ensemble query complete in {total_time:.2f}s, cost: ${total_cost:.4f}")
    
    return EnsembleResponse(
        question=request.question,
        model_responses=model_responses,
        synthesis=synthesis_result,
        total_cost=round(total_cost, 6),
        total_time_seconds=round(total_time, 3),
        timestamp=timestamp,
        cached=all_cached,
    )


@router.post("/synthesize", response_model=SynthesisResult)
async def synthesize_responses(
    request: SynthesisRequest,
    _rate_limit: None = Depends(check_rate_limit),
    _api_key: None = Depends(validate_api_key),
):
    """
    Synthesize multiple model responses into a unified answer.
    
    This endpoint is useful when you have pre-collected responses
    and want to synthesize them separately.
    
    Request body:
    - question: The original question
    - model_responses: List of ModelResponse objects
    - synthesis_model: Model to use for synthesis (optional)
    - max_tokens: Max tokens for synthesis (optional)
    """
    logger.info(f"Synthesis request for {len(request.model_responses)} responses")
    
    result = await synthesis_service.synthesize(
        question=request.question,
        model_responses=request.model_responses,
        synthesis_model=request.synthesis_model,
        max_tokens=request.max_tokens,
    )
    
    logger.info(f"Synthesis complete in {result.response_time_seconds:.2f}s")
    
    return result


@router.get("/stats")
async def get_stats():
    """
    Get usage statistics.
    
    Returns information about:
    - Total queries
    - Total cost
    - Cache hit rate
    - Queries by model
    """
    from ..models import usage_stats
    
    return usage_stats.to_dict()
