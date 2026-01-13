"""
Performance Monitoring and Distributed Tracing Utilities

This module provides:
1. CloudWatch/Prometheus-compatible metrics
2. Distributed tracing (X-Ray, Jaeger compatible)
3. Latency tracking decorators
4. Performance dashboards

Usage:
    from utils.monitoring import trace, track_latency, metrics_collector
    
    @trace("api.time_travel")
    @track_latency
    async def my_endpoint():
        ...
"""

import time
import asyncio
import functools
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import asynccontextmanager
import uuid

logger = logging.getLogger(__name__)


# ==================== Metrics Collection ====================

@dataclass
class LatencyMetric:
    """Single latency measurement."""
    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates performance metrics.
    Compatible with CloudWatch/Prometheus exporters.
    """
    
    def __init__(self, flush_interval: int = 60):
        self._metrics: Dict[str, List[LatencyMetric]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._flush_interval = flush_interval
        self._start_time = time.time()
    
    def record_latency(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **metadata
    ):
        """Record a latency measurement."""
        metric = LatencyMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            success=success,
            metadata=metadata
        )
        self._metrics[operation].append(metric)
        
        # Keep only last 1000 measurements per operation
        if len(self._metrics[operation]) > 1000:
            self._metrics[operation] = self._metrics[operation][-1000:]
        
        # Log for external collection (CloudWatch/Prometheus)
        logger.info(
            f"METRIC: operation={operation} duration_ms={duration_ms:.2f} "
            f"success={success} {' '.join(f'{k}={v}' for k, v in metadata.items())}"
        )
    
    def increment_counter(self, counter: str, value: int = 1):
        """Increment a counter."""
        self._counters[counter] += value
    
    def get_percentiles(
        self,
        operation: str,
        percentiles: List[int] = [50, 95, 99]
    ) -> Dict[str, float]:
        """Calculate percentile latencies for an operation."""
        metrics = self._metrics.get(operation, [])
        if not metrics:
            return {}
        
        durations = sorted([m.duration_ms for m in metrics])
        n = len(durations)
        
        result = {}
        for p in percentiles:
            idx = int(n * p / 100)
            idx = min(idx, n - 1)
            result[f"p{p}"] = durations[idx]
        
        result["count"] = n
        result["avg"] = sum(durations) / n
        result["min"] = durations[0]
        result["max"] = durations[-1]
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics statistics."""
        return {
            "operations": {
                op: self.get_percentiles(op)
                for op in self._metrics.keys()
            },
            "counters": dict(self._counters),
            "uptime_seconds": time.time() - self._start_time,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def export_cloudwatch_format(self) -> List[Dict[str, Any]]:
        """Export metrics in CloudWatch-compatible format."""
        metrics = []
        
        for operation, data in self._metrics.items():
            if not data:
                continue
            
            stats = self.get_percentiles(operation)
            
            metrics.append({
                "MetricName": f"{operation}_latency_p50",
                "Value": stats.get("p50", 0),
                "Unit": "Milliseconds",
                "Timestamp": datetime.utcnow().isoformat()
            })
            metrics.append({
                "MetricName": f"{operation}_latency_p95",
                "Value": stats.get("p95", 0),
                "Unit": "Milliseconds",
                "Timestamp": datetime.utcnow().isoformat()
            })
            metrics.append({
                "MetricName": f"{operation}_latency_p99",
                "Value": stats.get("p99", 0),
                "Unit": "Milliseconds",
                "Timestamp": datetime.utcnow().isoformat()
            })
        
        return metrics


# Global metrics collector
metrics_collector = MetricsCollector()


# ==================== Distributed Tracing ====================

@dataclass
class TraceSpan:
    """A span in a distributed trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "in_progress"
    
    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    def set_tag(self, key: str, value: Any):
        self.tags[key] = value
    
    def log(self, message: str, **kwargs):
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            **kwargs
        })
    
    def finish(self, status: str = "ok"):
        self.end_time = time.time()
        self.status = status
        
        # Export span (X-Ray/Jaeger format)
        logger.info(
            f"TRACE_SPAN: trace_id={self.trace_id} span_id={self.span_id} "
            f"operation={self.operation_name} duration_ms={self.duration_ms:.2f} "
            f"status={self.status} tags={json.dumps(self.tags)}"
        )
    
    def to_xray_format(self) -> Dict[str, Any]:
        """Export span in AWS X-Ray format."""
        return {
            "trace_id": f"1-{self.trace_id[:8]}-{self.trace_id[8:]}",
            "id": self.span_id[:16],
            "name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time or time.time(),
            "annotations": self.tags,
            "metadata": {"logs": self.logs}
        }
    
    def to_jaeger_format(self) -> Dict[str, Any]:
        """Export span in Jaeger format."""
        return {
            "traceID": self.trace_id,
            "spanID": self.span_id,
            "operationName": self.operation_name,
            "startTime": int(self.start_time * 1000000),  # microseconds
            "duration": int(self.duration_ms * 1000),  # microseconds
            "tags": [{"key": k, "value": v} for k, v in self.tags.items()],
            "logs": self.logs
        }


class TraceContext:
    """
    Thread-local trace context for propagating trace IDs.
    """
    _current_trace: Optional[TraceSpan] = None
    _spans: Dict[str, TraceSpan] = {}
    
    @classmethod
    def start_trace(cls, operation_name: str) -> TraceSpan:
        """Start a new trace."""
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation_name=operation_name,
            start_time=time.time()
        )
        
        cls._current_trace = span
        cls._spans[span_id] = span
        
        return span
    
    @classmethod
    def start_span(cls, operation_name: str) -> TraceSpan:
        """Start a child span."""
        parent = cls._current_trace
        trace_id = parent.trace_id if parent else uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        parent_span_id = parent.span_id if parent else None
        
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time()
        )
        
        cls._spans[span_id] = span
        return span
    
    @classmethod
    def get_current_trace_id(cls) -> Optional[str]:
        """Get current trace ID."""
        return cls._current_trace.trace_id if cls._current_trace else None


@asynccontextmanager
async def trace_operation(operation_name: str, **tags):
    """
    Context manager for tracing an operation.
    
    Usage:
        async with trace_operation("api.time_travel", question=q) as span:
            # do work
            span.log("Processing snapshot 1")
    """
    span = TraceContext.start_span(operation_name)
    for key, value in tags.items():
        span.set_tag(key, value)
    
    try:
        yield span
        span.finish("ok")
    except Exception as e:
        span.set_tag("error", str(e))
        span.finish("error")
        raise


# ==================== Decorators ====================

def track_latency(operation: Optional[str] = None):
    """
    Decorator to track function latency.
    
    Usage:
        @track_latency("api.time_travel")
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        op_name = operation or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                metrics_collector.record_latency(op_name, duration_ms, success)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            try:
                return func(*args, **kwargs)
            except Exception as e:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                metrics_collector.record_latency(op_name, duration_ms, success)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    # Handle @track_latency without parentheses
    if callable(operation):
        func = operation
        operation = None
        return decorator(func)
    
    return decorator


def trace(operation_name: str):
    """
    Decorator to add distributed tracing to a function.
    
    Usage:
        @trace("api.time_travel")
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            span = TraceContext.start_span(operation_name)
            try:
                result = await func(*args, **kwargs)
                span.finish("ok")
                return result
            except Exception as e:
                span.set_tag("error", str(e))
                span.finish("error")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            span = TraceContext.start_span(operation_name)
            try:
                result = func(*args, **kwargs)
                span.finish("ok")
                return result
            except Exception as e:
                span.set_tag("error", str(e))
                span.finish("error")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ==================== Alert Thresholds ====================

ALERT_THRESHOLDS = {
    "time_travel_total": {
        "p95_warning_ms": 45000,   # 45 seconds
        "p95_critical_ms": 90000,  # 90 seconds
        "error_rate_warning": 0.05,  # 5%
        "error_rate_critical": 0.10   # 10%
    },
    "generate_snapshot": {
        "p95_warning_ms": 25000,   # 25 seconds
        "p95_critical_ms": 45000,  # 45 seconds
    },
    "parallel_snapshot_generation": {
        "p95_warning_ms": 30000,   # 30 seconds (all 4 in parallel)
        "p95_critical_ms": 60000,  # 60 seconds
    }
}


def check_alerts() -> List[Dict[str, Any]]:
    """Check metrics against alert thresholds."""
    alerts = []
    
    for operation, thresholds in ALERT_THRESHOLDS.items():
        stats = metrics_collector.get_percentiles(operation)
        if not stats:
            continue
        
        p95 = stats.get("p95", 0)
        
        if p95 > thresholds.get("p95_critical_ms", float('inf')):
            alerts.append({
                "severity": "critical",
                "operation": operation,
                "metric": "p95_latency",
                "value": p95,
                "threshold": thresholds["p95_critical_ms"],
                "message": f"CRITICAL: {operation} p95 latency ({p95:.0f}ms) exceeds threshold ({thresholds['p95_critical_ms']}ms)"
            })
        elif p95 > thresholds.get("p95_warning_ms", float('inf')):
            alerts.append({
                "severity": "warning",
                "operation": operation,
                "metric": "p95_latency",
                "value": p95,
                "threshold": thresholds["p95_warning_ms"],
                "message": f"WARNING: {operation} p95 latency ({p95:.0f}ms) exceeds threshold ({thresholds['p95_warning_ms']}ms)"
            })
    
    return alerts


# ==================== CloudWatch Metrics Pusher ====================

class CloudWatchMetricsPusher:
    """
    Push metrics to AWS CloudWatch.
    
    Requires boto3 and AWS credentials configured.
    """
    
    def __init__(self, namespace: str = "LLMEnsemble"):
        self.namespace = namespace
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of CloudWatch client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client('cloudwatch')
            except ImportError:
                logger.warning("boto3 not installed, CloudWatch metrics disabled")
        return self._client
    
    async def push_metrics(self):
        """Push current metrics to CloudWatch."""
        client = self._get_client()
        if not client:
            return
        
        try:
            metric_data = metrics_collector.export_cloudwatch_format()
            
            if metric_data:
                # CloudWatch allows max 20 metrics per call
                for i in range(0, len(metric_data), 20):
                    batch = metric_data[i:i+20]
                    client.put_metric_data(
                        Namespace=self.namespace,
                        MetricData=batch
                    )
                    logger.debug(f"Pushed {len(batch)} metrics to CloudWatch")
        except Exception as e:
            logger.error(f"Failed to push CloudWatch metrics: {e}")


# Global CloudWatch pusher
cloudwatch_pusher = CloudWatchMetricsPusher()


# ==================== Prometheus Metrics Endpoint ====================

def get_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus format.
    
    Add this endpoint to your FastAPI app:
        @app.get("/metrics")
        def prometheus_metrics():
            return Response(content=get_prometheus_metrics(), media_type="text/plain")
    """
    lines = []
    
    for operation, data in metrics_collector._metrics.items():
        if not data:
            continue
        
        stats = metrics_collector.get_percentiles(operation)
        safe_op = operation.replace(".", "_").replace("-", "_")
        
        lines.append(f"# HELP {safe_op}_duration_seconds Latency for {operation}")
        lines.append(f"# TYPE {safe_op}_duration_seconds summary")
        lines.append(f'{safe_op}_duration_seconds{{quantile="0.5"}} {stats.get("p50", 0) / 1000:.6f}')
        lines.append(f'{safe_op}_duration_seconds{{quantile="0.95"}} {stats.get("p95", 0) / 1000:.6f}')
        lines.append(f'{safe_op}_duration_seconds{{quantile="0.99"}} {stats.get("p99", 0) / 1000:.6f}')
        lines.append(f'{safe_op}_duration_seconds_count {stats.get("count", 0)}')
        lines.append(f'{safe_op}_duration_seconds_sum {stats.get("avg", 0) * stats.get("count", 0) / 1000:.6f}')
        lines.append("")
    
    return "\n".join(lines)
