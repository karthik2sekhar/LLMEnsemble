"""
Streaming Time-Travel Service

Generates time-travel snapshots in parallel and streams each result
as it completes using Server-Sent Events (SSE).

Key Benefits:
- First result in ~8-12s instead of waiting 35s for all
- Progressive loading improves perceived performance
- Same total time, much better UX
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from openai import AsyncOpenAI
import httpx

from ..config import get_settings, ModelConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


class StreamEventType(str, Enum):
    """Types of streaming events."""
    START = "start"
    CLASSIFICATION = "classification"
    SNAPSHOT = "snapshot"
    KEY_CHANGES = "key_changes"
    NARRATIVE = "narrative"
    INSIGHT = "insight"
    TIMING = "timing"
    COMPLETE = "complete"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class StreamEvent:
    """A single streaming event."""
    type: StreamEventType
    data: Dict[str, Any]
    timestamp_ms: float = field(default_factory=lambda: time.time() * 1000)
    
    def to_sse(self) -> str:
        """Convert to Server-Sent Events format."""
        payload = {
            "type": self.type.value,
            "timestamp_ms": self.timestamp_ms,
            **self.data
        }
        return f"data: {json.dumps(payload)}\n\n"


@dataclass
class SnapshotTask:
    """A snapshot generation task with metadata."""
    date: datetime
    date_label: str
    task: asyncio.Task
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StreamingTimeTravelService:
    """
    Streaming Time-Travel Service
    
    Generates snapshots in parallel and yields results as they complete.
    """
    
    COMPLEXITY_PATTERNS = [
        'best', 'top', 'leading', 'compare', 'analysis', 'explain',
        'comprehensive', 'detailed', 'evolution', 'history'
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self._http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            timeout=httpx.Timeout(60.0, connect=10.0)
        )
        self.client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            http_client=self._http_client
        )
        self._semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls
    
    async def close(self):
        """Cleanup resources."""
        await self._http_client.aclose()
    
    def classify_complexity(self, question: str) -> Tuple[str, str]:
        """Classify question complexity."""
        question_lower = question.lower()
        matches = [p for p in self.COMPLEXITY_PATTERNS if p in question_lower]
        
        if len(matches) >= 3:
            return "complex", "gpt-4o"
        elif len(matches) >= 1 or len(question.split()) > 10:
            return "moderate", "gpt-4o"
        else:
            return "moderate", "gpt-4o"  # Default to moderate for temporal
    
    def get_time_points(self, question: str) -> List[Tuple[datetime, str]]:
        """Get time points for snapshots."""
        today = datetime.now()
        question_lower = question.lower()
        
        # AI-related questions use AI milestones
        if any(kw in question_lower for kw in ['ai', 'gpt', 'llm', 'chatgpt', 'claude', 'model']):
            return [
                (datetime(2023, 1, 1), "Jan 2023 - Pre-GPT-4"),
                (datetime(2023, 11, 1), "Nov 2023 - GPT-4 Turbo"),
                (datetime(2024, 5, 1), "May 2024 - GPT-4o"),
                (datetime(today.year, today.month, today.day), f"Today ({today.strftime('%b %d, %Y')})"),
            ]
        
        # Default time points
        return [
            (datetime(2023, 1, 1), "Jan 2023"),
            (datetime(2024, 1, 1), "Jan 2024"),
            (datetime(2025, 1, 1), "Jan 2025"),
            (datetime(today.year, today.month, today.day), f"Today ({today.strftime('%b %d, %Y')})"),
        ]
    
    async def generate_single_snapshot(
        self,
        question: str,
        date: datetime,
        date_label: str,
        model: str,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """Generate a single snapshot with timing."""
        start_time = time.time()
        date_str = date.strftime("%B %d, %Y")
        
        system_prompt = f"""You are answering as if today is {date_str}.
Only use information available up to {date_str}. Do NOT reference future events.
Be comprehensive and include specific details, names, and dates."""

        user_prompt = f"""Question: {question}

Answer as if today is {date_str}. Include specific details from this time period."""

        try:
            async with self._semaphore:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=max_tokens,
                        temperature=0.5
                    ),
                    timeout=45.0
                )
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            answer = response.choices[0].message.content.strip()
            tokens = response.usage.total_tokens if response.usage else 0
            cost = ModelConfig.get_cost(
                model,
                response.usage.prompt_tokens if response.usage else 0,
                response.usage.completion_tokens if response.usage else 0
            )
            
            return {
                "date": date.isoformat(),
                "date_label": date_label,
                "answer": answer,
                "model": model,
                "tokens": tokens,
                "cost": cost,
                "duration_ms": round(duration_ms, 2),
                "success": True
            }
            
        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            logger.error(f"Snapshot error for {date_label}: {e}")
            
            return {
                "date": date.isoformat(),
                "date_label": date_label,
                "answer": f"Error generating snapshot: {str(e)}",
                "model": model,
                "tokens": 0,
                "cost": 0,
                "duration_ms": round(duration_ms, 2),
                "success": False,
                "error": str(e)
            }
    
    async def generate_narrative(
        self,
        question: str,
        snapshots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate evolution narrative from snapshots."""
        start_time = time.time()
        
        snapshot_summaries = "\n\n".join([
            f"**{s['date_label']}**:\n{s['answer'][:500]}..."
            for s in snapshots if s.get('success', True)
        ])
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze how answers evolved over time. Provide:
1. A narrative summary of the evolution (2-3 paragraphs)
2. Key insights (3-4 bullet points)
3. Change velocity (fast/moderate/slow)
4. Future outlook (1 paragraph)

Format as JSON with keys: narrative, insights, velocity, outlook"""
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\n\nAnswers over time:\n{snapshot_summaries}"
                    }
                ],
                max_tokens=800,
                temperature=0.5
            )
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse as JSON, fallback to raw text
            try:
                # Remove markdown code blocks if present
                clean_content = content
                if "```" in clean_content:
                    # Extract content between code blocks
                    parts = clean_content.split("```")
                    for part in parts:
                        part = part.strip()
                        if part.startswith("json"):
                            part = part[4:].strip()
                        if part.startswith("{") and part.endswith("}"):
                            clean_content = part
                            break
                
                # Also try to find JSON object in the content
                if not clean_content.startswith("{"):
                    start_idx = content.find("{")
                    end_idx = content.rfind("}") + 1
                    if start_idx != -1 and end_idx > start_idx:
                        clean_content = content[start_idx:end_idx]
                
                parsed = json.loads(clean_content)
                
                # Ensure insights is a list of strings, not dicts
                insights_list = parsed.get("insights", [])
                if insights_list and isinstance(insights_list[0], dict):
                    insights_list = [i.get("text", str(i)) for i in insights_list]
                
                return {
                    "narrative": parsed.get("narrative", content),
                    "insights": insights_list,
                    "velocity": parsed.get("velocity", "moderate"),
                    "outlook": parsed.get("outlook", ""),
                    "duration_ms": round(duration_ms, 2),
                    "success": True
                }
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse narrative JSON: {e}, using raw content")
                return {
                    "narrative": content,
                    "insights": [],
                    "velocity": "moderate",
                    "outlook": "",
                    "duration_ms": round(duration_ms, 2),
                    "success": True
                }
            
        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            logger.error(f"Narrative generation error: {e}")
            
            return {
                "narrative": f"Error generating narrative: {str(e)}",
                "insights": [],
                "velocity": "unknown",
                "outlook": "",
                "duration_ms": round(duration_ms, 2),
                "success": False,
                "error": str(e)
            }
    
    async def stream_time_travel(
        self,
        question: str,
        force: bool = False
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream time-travel results as they complete.
        
        Yields events in this order:
        1. START - Initial metadata
        2. CLASSIFICATION - Complexity classification
        3. SNAPSHOT (multiple) - Each snapshot as it completes
        4. NARRATIVE - Evolution narrative
        5. TIMING - Final timing breakdown
        6. COMPLETE - Stream complete
        
        Args:
            question: The user's question
            force: Force time-travel even for low-sensitivity questions
            
        Yields:
            StreamEvent objects that can be converted to SSE format
        """
        total_start = time.time()
        all_snapshots = []
        timing_steps = []
        
        # Event 1: START
        yield StreamEvent(
            type=StreamEventType.START,
            data={
                "question": question,
                "message": "Starting time-travel analysis..."
            }
        )
        
        # Event 2: CLASSIFICATION
        classification_start = time.time()
        complexity, model = self.classify_complexity(question)
        time_points = self.get_time_points(question)
        classification_ms = (time.time() - classification_start) * 1000
        
        timing_steps.append({
            "step": "classification",
            "ms": round(classification_ms, 2),
            "provider": "system"
        })
        
        yield StreamEvent(
            type=StreamEventType.CLASSIFICATION,
            data={
                "complexity": complexity,
                "model": model,
                "num_snapshots": len(time_points),
                "time_points": [tp[1] for tp in time_points],
                "duration_ms": round(classification_ms, 2)
            }
        )
        
        # Create snapshot tasks (all start in parallel)
        # Store task -> metadata mapping
        pending_tasks = set()
        task_metadata = {}
        
        for date, label in time_points:
            task = asyncio.create_task(
                self.generate_single_snapshot(question, date, label, model)
            )
            pending_tasks.add(task)
            task_metadata[task] = (date, label)
        
        # Event 3: SNAPSHOT (stream as each completes)
        snapshots_start = time.time()
        completed_count = 0
        
        # Use asyncio.wait with FIRST_COMPLETED to get actual task objects
        while pending_tasks:
            done, pending_tasks = await asyncio.wait(
                pending_tasks, 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for completed_task in done:
                try:
                    result = await completed_task
                    date, label = task_metadata[completed_task]
                    completed_count += 1
                    
                    all_snapshots.append(result)
                    
                    timing_steps.append({
                        "step": f"snapshot_{label.replace(' ', '_')}",
                        "ms": result["duration_ms"],
                        "provider": "openai",
                        "model": result["model"]
                    })
                    
                    yield StreamEvent(
                        type=StreamEventType.SNAPSHOT,
                        data={
                            "index": completed_count,
                            "total": len(time_points),
                            "snapshot": result,
                            "remaining": len(time_points) - completed_count
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Snapshot task error: {e}")
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        data={
                            "error": str(e),
                            "step": "snapshot",
                            "recoverable": True
                        }
                    )
        
        snapshots_total_ms = (time.time() - snapshots_start) * 1000
        
        # Sort snapshots by date for narrative
        all_snapshots.sort(key=lambda x: x["date"])
        
        # Send heartbeat before narrative (can take a while)
        yield StreamEvent(
            type=StreamEventType.HEARTBEAT,
            data={"message": "Generating evolution narrative..."}
        )
        
        # Event 4: NARRATIVE
        narrative_result = await self.generate_narrative(question, all_snapshots)
        
        timing_steps.append({
            "step": "narrative",
            "ms": narrative_result["duration_ms"],
            "provider": "openai",
            "model": "gpt-4o"
        })
        
        yield StreamEvent(
            type=StreamEventType.NARRATIVE,
            data=narrative_result
        )
        
        # Event 5: INSIGHTS (send individually for progressive display)
        for i, insight in enumerate(narrative_result.get("insights", [])):
            yield StreamEvent(
                type=StreamEventType.INSIGHT,
                data={
                    "index": i + 1,
                    "total": len(narrative_result.get("insights", [])),
                    "insight": insight
                }
            )
        
        # Calculate final timing
        total_ms = (time.time() - total_start) * 1000
        
        # Calculate what sequential would have taken
        sequential_estimate = sum(s["duration_ms"] for s in all_snapshots) + narrative_result["duration_ms"]
        parallelization_savings = sequential_estimate - total_ms
        
        # Find bottleneck
        step_times = {s["step"]: s["ms"] for s in timing_steps}
        slowest_step = max(timing_steps, key=lambda x: x["ms"])
        
        # Event 6: TIMING
        yield StreamEvent(
            type=StreamEventType.TIMING,
            data={
                "total_ms": round(total_ms, 2),
                "snapshots_parallel_ms": round(snapshots_total_ms, 2),
                "narrative_ms": narrative_result["duration_ms"],
                "sequential_estimate_ms": round(sequential_estimate, 2),
                "parallelization_savings_ms": round(parallelization_savings, 2),
                "steps": timing_steps,
                "bottleneck": slowest_step["step"],
                "bottleneck_ms": slowest_step["ms"]
            }
        )
        
        # Event 7: COMPLETE
        total_cost = sum(s.get("cost", 0) for s in all_snapshots)
        total_tokens = sum(s.get("tokens", 0) for s in all_snapshots)
        
        yield StreamEvent(
            type=StreamEventType.COMPLETE,
            data={
                "success": True,
                "total_snapshots": len(all_snapshots),
                "total_cost": round(total_cost, 6),
                "total_tokens": total_tokens,
                "total_ms": round(total_ms, 2),
                "snapshots": all_snapshots,
                "narrative": narrative_result.get("narrative", ""),
                "insights": narrative_result.get("insights", []),
                "velocity": narrative_result.get("velocity", "moderate"),
                "outlook": narrative_result.get("outlook", "")
            }
        )
        
        # Log metrics
        logger.info(
            f"STREAM_METRICS: total_ms={total_ms:.0f} "
            f"snapshots={len(all_snapshots)} "
            f"parallel_ms={snapshots_total_ms:.0f} "
            f"narrative_ms={narrative_result['duration_ms']:.0f} "
            f"savings_ms={parallelization_savings:.0f}"
        )


# Global streaming service instance
streaming_time_travel_service = StreamingTimeTravelService()
