"""
Monitoring and Metrics API Endpoints

Provides:
1. Prometheus-compatible metrics endpoint
2. Performance statistics endpoint
3. Health check with detailed metrics
4. Alert status endpoint
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from ..utils.monitoring import (
    metrics_collector,
    get_prometheus_metrics,
    check_alerts,
    ALERT_THRESHOLDS
)
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Export metrics in Prometheus format for scraping"
)
async def prometheus_metrics():
    """
    Export metrics in Prometheus format.
    
    Add to your Prometheus config:
    ```yaml
    scrape_configs:
      - job_name: 'llm-ensemble'
        static_configs:
          - targets: ['your-alb-url:80']
        metrics_path: '/api/monitoring/metrics'
    ```
    """
    content = get_prometheus_metrics()
    return Response(content=content, media_type="text/plain")


@router.get(
    "/stats",
    summary="Performance Statistics",
    description="Get detailed performance statistics for all operations"
)
async def get_performance_stats() -> Dict[str, Any]:
    """
    Get performance statistics.
    
    Returns p50, p95, p99 latencies for each operation.
    """
    stats = metrics_collector.get_stats()
    return {
        **stats,
        "alert_thresholds": ALERT_THRESHOLDS
    }


@router.get(
    "/alerts",
    summary="Active Alerts",
    description="Check for any active performance alerts"
)
async def get_active_alerts() -> Dict[str, Any]:
    """
    Check for active alerts based on configured thresholds.
    
    Returns any warnings or critical alerts.
    """
    alerts = check_alerts()
    
    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "has_critical": any(a["severity"] == "critical" for a in alerts),
        "has_warning": any(a["severity"] == "warning" for a in alerts),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/latency-breakdown",
    summary="Time-Travel Latency Breakdown",
    description="Get detailed latency breakdown for time-travel operations"
)
async def get_latency_breakdown() -> Dict[str, Any]:
    """
    Get detailed latency breakdown for performance analysis.
    
    Shows:
    - Total time-travel latency
    - Individual component latencies
    - Comparison with baseline
    """
    operations = [
        "time_travel_total",
        "parallel_snapshot_generation",
        "batch_key_changes_extraction",
        "evolution_narrative",
        "generate_snapshot"
    ]
    
    breakdown = {}
    for op in operations:
        stats = metrics_collector.get_percentiles(op)
        if stats:
            breakdown[op] = stats
    
    # Calculate improvement metrics if we have data
    baseline_sequential = 90000  # 90 seconds baseline
    current_p95 = breakdown.get("time_travel_total", {}).get("p95", baseline_sequential)
    
    return {
        "breakdown": breakdown,
        "baseline_ms": baseline_sequential,
        "current_p95_ms": current_p95,
        "improvement_percentage": round((1 - current_p95 / baseline_sequential) * 100, 1),
        "target_ms": 30000,  # 30 seconds target
        "on_target": current_p95 <= 30000,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post(
    "/reset-stats",
    summary="Reset Statistics",
    description="Reset all performance statistics (admin only)"
)
async def reset_stats():
    """Reset all collected statistics."""
    global metrics_collector
    from ..utils.monitoring import MetricsCollector
    metrics_collector = MetricsCollector()
    
    return {
        "message": "Statistics reset successfully",
        "timestamp": datetime.utcnow().isoformat()
    }
