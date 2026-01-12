"""
Router API endpoints for intelligent query routing.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    RouteAndAnswerRequest, RouteAndAnswerResponse,
    RoutingStats, ErrorResponse,
    TimeTravelRequest, TimeTravelResponse, TimeSnapshot, TemporalSensitivityLevel
)
from ..services.router_service import router_service
from ..services.search_service import search_service
from ..services.time_travel_service import time_travel_service
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


# ==================== Time-Travel Answers Endpoint ====================

@router.post(
    "/time-travel",
    response_model=TimeTravelResponse,
    responses={
        200: {"description": "Successfully generated time-travel answer"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Time-Travel Answers",
    description="""
    Generate answers showing how responses would have changed across different time periods.
    
    **Purpose:**
    This feature demonstrates answer evolution for temporally sensitive questions,
    showing users how information changes over time.
    
    **Flow:**
    1. Question is analyzed for temporal sensitivity (HIGH/MEDIUM/LOW/NONE)
    2. For HIGH/MEDIUM sensitivity, time points are identified
    3. Answer snapshots are generated for each time point
    4. Key changes between periods are extracted
    5. Evolution narrative is synthesized
    
    **Temporal Sensitivity Levels:**
    - **HIGH**: Current events, tech releases, market data, sports results, rankings
    - **MEDIUM**: Business evolution, scientific understanding, industry standards
    - **LOW**: Historical facts, relatively stable information
    - **NONE**: Timeless facts, definitions, philosophical concepts
    
    **Time-Travel is Applied For:**
    - Questions with HIGH temporal sensitivity (automatic)
    - Questions with MEDIUM sensitivity (automatic)
    - Any question when `force_time_travel=true`
    
    **Time-Travel is Skipped When:**
    - LOW/NONE temporal sensitivity (unless forced)
    - Answers are identical across all time periods
    - Feature is disabled in configuration
    
    **Output Format:**
    Timeline view with snapshots, key changes, evolution narrative, and insights.
    """
)
async def time_travel_answer(request: TimeTravelRequest) -> TimeTravelResponse:
    """
    Generate time-travel answer showing how response evolves over time.
    
    Returns:
    - Temporal sensitivity classification
    - List of time snapshots with answers at each period
    - Key changes between periods
    - Evolution narrative
    - Insights and future outlook
    - Cost and timing metrics
    """
    try:
        logger.info(f"Time-travel request: {request.question[:100]}...")
        
        # Generate time-travel answer
        result = await time_travel_service.generate_time_travel_answer(
            question=request.question,
            force_time_travel=request.force_time_travel
        )
        
        # Convert to response schema
        snapshots = [
            TimeSnapshot(
                date=s.date,
                date_label=s.date_label,
                answer=s.answer,
                key_changes=s.key_changes,
                data_points=s.data_points,
                model_used=s.model_used,
                tokens_used=s.tokens_used,
                cost_estimate=s.cost_estimate,
                response_time_seconds=s.response_time_seconds
            )
            for s in result.snapshots
        ]
        
        return TimeTravelResponse(
            question=result.question,
            temporal_sensitivity=TemporalSensitivityLevel(result.temporal_sensitivity.value),
            sensitivity_reasoning=result.sensitivity_reasoning,
            is_eligible=result.is_eligible,
            skip_reason=result.skip_reason,
            snapshots=snapshots,
            evolution_narrative=result.evolution_narrative,
            insights=result.insights,
            change_velocity=result.change_velocity,
            future_outlook=result.future_outlook,
            total_cost=result.total_cost,
            total_time_seconds=result.total_time_seconds,
            timestamp=datetime.utcnow(),
            # Routing fix: expose complexity classification for transparency
            base_complexity=result.base_complexity.value if result.base_complexity else None,
            routing_validation_passed=result.routing_validation_passed
        )
        
    except ValueError as e:
        logger.error(f"Validation error in time-travel: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in time-travel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate time-travel answer: {str(e)}"
        )


@router.post(
    "/check-temporal-sensitivity",
    summary="Check Temporal Sensitivity",
    description="Check the temporal sensitivity of a question without generating time-travel answer."
)
async def check_temporal_sensitivity(question: str):
    """
    Check temporal sensitivity of a question.
    
    Returns just the sensitivity classification without generating full time-travel.
    """
    try:
        sensitivity, reasoning = time_travel_service.classify_temporal_sensitivity(question)
        time_points = time_travel_service.identify_time_points(question, sensitivity)
        
        return {
            "question": question,
            "temporal_sensitivity": sensitivity.value,
            "reasoning": reasoning,
            "suggested_time_points": [
                {"date": tp[0].isoformat(), "label": tp[1]}
                for tp in time_points
            ],
            "time_travel_eligible": sensitivity.value in ["high", "medium"],
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error checking temporal sensitivity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
