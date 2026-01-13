"""
Streaming API Routes

Provides Server-Sent Events (SSE) endpoints for real-time streaming
of time-travel results.
"""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.streaming_time_travel import (
    streaming_time_travel_service,
    StreamEvent,
    StreamEventType
)
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["streaming"])


class StreamingTimeTravelRequest(BaseModel):
    """Request body for streaming time-travel."""
    question: str = Field(..., min_length=1, max_length=5000)
    force_time_travel: bool = Field(default=False)


async def event_generator(
    question: str,
    force: bool = False
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events from the streaming time-travel service.
    
    Yields SSE-formatted strings that can be consumed by EventSource.
    """
    try:
        async for event in streaming_time_travel_service.stream_time_travel(
            question=question,
            force=force
        ):
            yield event.to_sse()
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)
            
    except asyncio.CancelledError:
        # Client disconnected
        logger.info("Client disconnected from stream")
        yield StreamEvent(
            type=StreamEventType.ERROR,
            data={"error": "Stream cancelled", "recoverable": False}
        ).to_sse()
        
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield StreamEvent(
            type=StreamEventType.ERROR,
            data={"error": str(e), "recoverable": False}
        ).to_sse()


@router.post(
    "/time-travel-stream",
    summary="Streaming Time-Travel Answers",
    description="""
    Stream time-travel results using Server-Sent Events (SSE).
    
    **Key Benefits:**
    - First result in ~8-12s instead of waiting ~35s
    - Progressive loading improves perceived performance
    - Same backend processing time, much better UX
    
    **Event Types:**
    - `start` - Stream started, initial metadata
    - `classification` - Question complexity classified
    - `snapshot` - A single time-point answer (multiple events)
    - `narrative` - Evolution narrative generated
    - `insight` - Individual insights (multiple events)
    - `timing` - Final timing breakdown
    - `complete` - Stream complete with full data
    - `error` - Error occurred (may be recoverable)
    - `heartbeat` - Keep-alive during long operations
    
    **SSE Format:**
    ```
    data: {"type": "snapshot", "data": {...}}
    
    data: {"type": "narrative", "data": {...}}
    ```
    
    **Frontend Usage (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/api/time-travel-stream', {
      method: 'POST',
      body: JSON.stringify({ question: "How has AI changed?" })
    });
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data.type, data);
    };
    ```
    
    **Note:** For POST requests with body, use fetch() with ReadableStream
    instead of EventSource (which only supports GET).
    """,
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE stream of time-travel events",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"type": "snapshot", "index": 1, "total": 4, "snapshot": {...}}\n\n'
                }
            }
        }
    }
)
async def stream_time_travel(
    request: StreamingTimeTravelRequest,
    req: Request
):
    """
    Stream time-travel answers as Server-Sent Events.
    
    Results are streamed as each snapshot completes, providing
    much faster time-to-first-result (~8s vs ~35s).
    """
    logger.info(f"Stream request: {request.question[:100]}...")
    
    return StreamingResponse(
        event_generator(
            question=request.question,
            force=request.force_time_travel
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get(
    "/time-travel-stream-test",
    summary="Test SSE Stream",
    description="Simple GET endpoint to test SSE streaming works."
)
async def test_stream():
    """Test endpoint for SSE streaming."""
    
    async def test_generator():
        for i in range(5):
            event = StreamEvent(
                type=StreamEventType.HEARTBEAT,
                data={"message": f"Test event {i + 1}/5", "index": i + 1}
            )
            yield event.to_sse()
            await asyncio.sleep(1)
        
        yield StreamEvent(
            type=StreamEventType.COMPLETE,
            data={"message": "Test complete", "success": True}
        ).to_sse()
    
    return StreamingResponse(
        test_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
