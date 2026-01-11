"""
Router API endpoints for intelligent query routing.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    RouteAndAnswerRequest, RouteAndAnswerResponse,
    RoutingStats, ErrorResponse
)
from ..services.router_service import router_service
from ..services.search_service import search_service
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["router"])


@router.post(
    "/route-and-answer",
    response_model=RouteAndAnswerResponse,
    responses={
        200: {"description": "Successfully routed and answered the query"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Intelligent Query Routing with Temporal Awareness",
    description="""
    Intelligently routes queries to optimal model combinations based on 
    complexity, intent, domain classification, and temporal awareness.
    
    **Flow:**
    1. Temporal detection analyzes query for time-sensitive content
    2. Query is classified using gpt-4o-mini (fast/cheap)
    3. Temporal overrides applied (temporal queries never classified as "simple")
    4. For temporal queries needing current data, web search is performed
    5. Based on classification, optimal models are selected (minimum 2 for temporal)
    6. Selected models are queried in parallel with search context
    7. For complex queries, responses are synthesized
    8. Full metadata returned including temporal info, search results, costs
    
    **Complexity Routing:**
    - Simple: gpt-4o-mini only (fastest, cheapest) - NOT for temporal queries
    - Moderate: gpt-4o-mini + gpt-4o (balanced) - minimum for temporal
    - Complex: All models + synthesis (highest quality)
    
    **Temporal Handling:**
    - Queries with "latest", "current", "2024+", etc. trigger temporal detection
    - Web search augments context for current information needs
    - UI warning returned when data may be beyond knowledge cutoff
    
    **Overrides:**
    - `override_models`: Manually specify which models to use
    - `force_synthesis`: Force synthesis regardless of complexity
    - `enable_search`: Enable/disable web search (default: true)
    """
)
async def route_and_answer(request: RouteAndAnswerRequest) -> RouteAndAnswerResponse:
    """
    Classify query and route to optimal models with temporal awareness.
    
    Returns comprehensive response including:
    - Query classification details
    - Routing decision rationale
    - Temporal detection results
    - Search results (if web search was used)
    - Individual model responses
    - Final synthesized answer (if applicable)
    - Cost breakdown and savings vs full ensemble
    - Execution time metrics
    - UI warning message for temporal queries
    """
    try:
        logger.info(f"Route-and-answer request: {request.question[:100]}...")
        
        response = await router_service.route_and_answer(
            question=request.question,
            max_tokens=request.max_tokens or 2000,
            temperature=request.temperature or 0.7,
            override_models=request.override_models,
            force_synthesis=request.force_synthesis,
            enable_search=request.enable_search
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error in route-and-answer: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in route-and-answer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process request: {str(e)}"
        )


@router.get(
    "/routing-stats",
    response_model=RoutingStats,
    summary="Get Routing Statistics",
    description="Returns statistics about query routing including usage distribution and cost savings."
)
async def get_routing_stats() -> RoutingStats:
    """Get routing statistics."""
    try:
        stats = router_service.get_stats()
        return RoutingStats(
            total_queries=stats["total_queries"],
            simple_queries=stats["simple_queries"],
            moderate_queries=stats["moderate_queries"],
            complex_queries=stats["complex_queries"],
            total_cost=stats["total_cost"],
            total_savings=stats["total_savings"],
            average_savings_percentage=stats["average_savings_percentage"],
            model_usage_distribution=stats["model_usage_distribution"],
            fallback_count=stats["fallback_count"]
        )
    except Exception as e:
        logger.error(f"Error getting routing stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/clear-classification-cache",
    summary="Clear Classification Cache",
    description="Clears the query classification cache."
)
async def clear_classification_cache():
    """Clear the classification cache."""
    try:
        router_service.clear_classification_cache()
        return {"message": "Classification cache cleared", "timestamp": datetime.utcnow()}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
