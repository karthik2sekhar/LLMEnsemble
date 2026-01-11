"""
Query Router Service for intelligent query classification and routing.
Classifies incoming queries and routes them to optimal model combinations
based on complexity, intent, domain, and requirements.
Includes temporal awareness to detect time-sensitive queries.
Uses Perplexity API for real-time web search + reasoning on temporal queries.
"""

import asyncio
import json
import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from openai import AsyncOpenAI

from ..config import get_settings, ModelConfig, TemporalConfig
from ..schemas import (
    QueryClassification, RoutingDecision, CostBreakdown, ExecutionMetrics,
    ComplexityLevel, QueryIntent, QueryDomain, TemporalScope, TemporalDetectionResult,
    ModelResponse, SynthesisResult, TokenUsage, CacheStatus,
    RouteAndAnswerResponse
)
from ..utils.logging import get_logger
from ..utils.cache import cache_manager
from .llm_service import llm_service
from .synthesis_service import synthesis_service
from .search_service import search_service
from .perplexity_service import perplexity_service

logger = get_logger(__name__)


# Classification cache with 24-hour TTL
_classification_cache: Dict[str, Tuple[QueryClassification, datetime]] = {}
CLASSIFICATION_CACHE_TTL = timedelta(hours=24)


# Cost per 1K tokens (input/output)
MODEL_COSTS = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.0075},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-5.2": {"input": 0.02, "output": 0.06},
}


def detect_temporal_query(question: str) -> TemporalDetectionResult:
    """
    Detect temporal aspects of a query using multi-layer analysis.
    
    Layer 1: Keyword scanning for temporal markers
    Layer 2: Year detection for future/recent years
    Layer 3: Determine temporal scope
    
    Args:
        question: The query to analyze
        
    Returns:
        TemporalDetectionResult with detection details
    """
    question_lower = question.lower()
    matched_keywords: List[str] = []
    detected_years: List[int] = []
    
    # Layer 1: Keyword scanning using individual patterns
    for pattern in TemporalConfig.get_compiled_patterns():
        matches = pattern.findall(question_lower)
        if matches:
            # Flatten if matches are tuples and filter empty strings
            for match in matches:
                if isinstance(match, tuple):
                    matched_keywords.extend([m for m in match if m])
                elif match:
                    matched_keywords.append(match)
    
    # Deduplicate and clean keywords
    matched_keywords = list(set(kw.strip() for kw in matched_keywords if kw.strip()))
    
    # Layer 2: Year detection
    year_pattern = re.compile(r'\b(20[2-3]\d)\b')  # 2020-2039
    year_matches = year_pattern.findall(question)
    detected_years = [int(y) for y in year_matches]
    
    # Determine if temporal
    current_year = datetime.now().year
    knowledge_cutoff_year = int(TemporalConfig.MODEL_KNOWLEDGE_CUTOFF.split("-")[0])
    
    is_temporal = bool(matched_keywords) or any(y > knowledge_cutoff_year for y in detected_years)
    requires_current_data = any(kw in question_lower for kw in ["latest", "current", "today", "now", "2024", "2025", "2026", "2027", "breaking", "trending"])
    
    # Layer 3: Determine scope
    if not is_temporal:
        scope = TemporalScope.EVERGREEN
    elif any(y > current_year for y in detected_years):
        scope = TemporalScope.FUTURE
    elif detected_years and all(y <= knowledge_cutoff_year for y in detected_years):
        scope = TemporalScope.HISTORICAL
    else:
        scope = TemporalScope.CURRENT
    
    # Calculate confidence based on strength of signals
    if matched_keywords and detected_years:
        confidence = 0.95
    elif matched_keywords:
        confidence = 0.85
    elif detected_years:
        confidence = 0.80 if any(y > knowledge_cutoff_year for y in detected_years) else 0.60
    else:
        confidence = 0.50
    
    reasoning_parts = []
    if matched_keywords:
        reasoning_parts.append(f"Temporal keywords detected: {matched_keywords}")
    if detected_years:
        reasoning_parts.append(f"Years mentioned: {detected_years}")
    if requires_current_data:
        reasoning_parts.append("Query explicitly requests current/recent information")
    if not reasoning_parts:
        reasoning_parts.append("No temporal indicators found")
    
    return TemporalDetectionResult(
        is_temporal=is_temporal,
        temporal_scope=scope,
        requires_current_data=requires_current_data,
        detected_keywords=matched_keywords,
        detected_years=detected_years,
        confidence=confidence,
        reasoning="; ".join(reasoning_parts)
    )


# Classification prompt with comprehensive examples
CLASSIFICATION_PROMPT = """You are an expert query classifier for an AI assistant system. Your task is to analyze incoming queries and classify them to route them to the optimal AI models.

IMPORTANT MODEL KNOWLEDGE CUTOFF: All models have knowledge only up to October 2023. Any query asking about events, data, or information after this date REQUIRES web search.

Classify the query on these dimensions:

## COMPLEXITY
- **simple**: Single-step, direct answer queries. Facts, definitions, quick lookups, straightforward questions with clear answers.
- **moderate**: Two-step reasoning or multi-part analysis. Requires some explanation, comparison, or moderate depth.
- **complex**: Deep reasoning, analysis, subjective topics, multi-perspective discussions, creative generation, or specialized knowledge.

CRITICAL TEMPORAL RULE: If a query contains temporal keywords (latest, current, recent, 2024, 2025, 2026, trending, breaking, this week, this month, now, today) or asks about anything after October 2023, it should NEVER be classified as "simple". Minimum complexity for temporal queries is "moderate".

## INTENT
- **factual**: Looking for facts, information, data, or verified knowledge.
- **creative**: Generate original content (writing, ideas, designs, stories).
- **analytical**: Analyze, breakdown, explain concepts, provide insights.
- **procedural**: How-to guides, step-by-step instructions, tutorials.
- **comparative**: Compare alternatives, pros/cons, make recommendations.

## DOMAIN
- **coding**: Software development, debugging, architecture, programming languages.
- **technical**: Science, engineering, mathematics, systems, specialized technical topics.
- **general**: General knowledge, common topics, everyday questions.
- **creative**: Art, writing, music, design, creative projects.
- **research**: Academic topics, specialized research, deep domain expertise needed.

## REQUIRES_SEARCH
- **true**: Query needs real-time data, current events, information after October 2023, or explicitly asks for "latest", "current", "recent", "2024", "2025", "2026", "trending", "breaking news", etc.
- **false**: Query can be answered with training knowledge alone (pre-October 2023 knowledge).

## RECOMMENDED_MODELS
Based on classification, recommend which models to use:
- **gpt-4o-mini**: Fast, cost-efficient. Best for simple factual queries, quick lookups, straightforward tasks.
- **gpt-4o**: Balanced performance. Good for moderate complexity, creative tasks, multimodal understanding.
- **gpt-4-turbo**: Complex reasoning, deep analysis, detailed explanations, specialized knowledge.

Note: For temporal queries requiring search, recommend at least 2 models to cross-validate information.

## EXAMPLES

Query: "What is the capital of France?"
Classification: {{"complexity": "simple", "intent": "factual", "domain": "general", "requires_search": false, "recommended_models": ["gpt-4o-mini"], "reasoning": "Simple factual lookup with a single definitive answer.", "confidence": 0.98}}

Query: "Write a haiku about autumn leaves"
Classification: {{"complexity": "simple", "intent": "creative", "domain": "creative", "requires_search": false, "recommended_models": ["gpt-4o-mini"], "reasoning": "Simple creative task with clear constraints.", "confidence": 0.95}}

Query: "What are the latest AI breakthroughs in 2026?"
Classification: {{"complexity": "complex", "intent": "factual", "domain": "research", "requires_search": true, "recommended_models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], "reasoning": "TEMPORAL QUERY: Asks about 2026 which is after model knowledge cutoff (Oct 2023). Requires web search for current information. Using all models to synthesize and validate search results.", "confidence": 0.95}}

Query: "What's trending in tech right now?"
Classification: {{"complexity": "moderate", "intent": "factual", "domain": "technical", "requires_search": true, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "TEMPORAL QUERY: 'trending' and 'right now' indicate need for current data beyond knowledge cutoff. Requires search.", "confidence": 0.92}}

Query: "Explain how photosynthesis works"
Classification: {{"complexity": "moderate", "intent": "analytical", "domain": "technical", "requires_search": false, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "Requires explanation of a multi-step biological process.", "confidence": 0.92}}

Query: "Compare React vs Vue for a new web project"
Classification: {{"complexity": "moderate", "intent": "comparative", "domain": "coding", "requires_search": false, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "Comparative analysis requiring knowledge of both frameworks.", "confidence": 0.90}}

Query: "How do I make pasta carbonara?"
Classification: {{"complexity": "simple", "intent": "procedural", "domain": "general", "requires_search": false, "recommended_models": ["gpt-4o-mini"], "reasoning": "Straightforward recipe/procedure request.", "confidence": 0.96}}

Query: "Debug this Python code that's throwing a TypeError"
Classification: {{"complexity": "moderate", "intent": "procedural", "domain": "coding", "requires_search": false, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "Debugging requires analysis but is typically methodical.", "confidence": 0.88}}

Query: "Design a microservices architecture for an e-commerce platform"
Classification: {{"complexity": "complex", "intent": "analytical", "domain": "coding", "requires_search": false, "recommended_models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], "reasoning": "Complex architectural design requiring deep expertise and multiple considerations.", "confidence": 0.94}}

Query: "What's the weather in New York today?"
Classification: {{"complexity": "moderate", "intent": "factual", "domain": "general", "requires_search": true, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "TEMPORAL QUERY: 'today' requires real-time weather data. Must use search.", "confidence": 0.97}}

Query: "What are the current stock prices for NVIDIA?"
Classification: {{"complexity": "moderate", "intent": "factual", "domain": "general", "requires_search": true, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "TEMPORAL QUERY: 'current' stock prices change constantly and require real-time data.", "confidence": 0.96}}

Query: "Analyze the themes in Shakespeare's Hamlet"
Classification: {{"complexity": "complex", "intent": "analytical", "domain": "research", "requires_search": false, "recommended_models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], "reasoning": "Deep literary analysis requiring nuanced interpretation.", "confidence": 0.91}}

Query: "Write a 2000-word short story about a time traveler"
Classification: {{"complexity": "complex", "intent": "creative", "domain": "creative", "requires_search": false, "recommended_models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], "reasoning": "Extended creative writing requiring sustained narrative quality.", "confidence": 0.93}}

Query: "What is 25 * 4?"
Classification: {{"complexity": "simple", "intent": "factual", "domain": "general", "requires_search": false, "recommended_models": ["gpt-4o-mini"], "reasoning": "Simple arithmetic calculation.", "confidence": 0.99}}

Query: "Explain the ethical implications of AI in healthcare"
Classification: {{"complexity": "complex", "intent": "analytical", "domain": "research", "requires_search": false, "recommended_models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], "reasoning": "Complex topic requiring multi-perspective ethical analysis.", "confidence": 0.92}}

Query: "Convert this JSON to TypeScript interfaces"
Classification: {{"complexity": "moderate", "intent": "procedural", "domain": "coding", "requires_search": false, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "Structured transformation task with clear input/output.", "confidence": 0.94}}

Query: "What are the best practices for REST API design?"
Classification: {{"complexity": "moderate", "intent": "factual", "domain": "coding", "requires_search": false, "recommended_models": ["gpt-4o-mini", "gpt-4o"], "reasoning": "Well-established knowledge but requires comprehensive coverage.", "confidence": 0.91}}

Query: "Help me understand quantum entanglement"
Classification: {{"complexity": "complex", "intent": "analytical", "domain": "technical", "requires_search": false, "recommended_models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], "reasoning": "Complex physics concept requiring detailed explanation.", "confidence": 0.90}}

Query: "Translate 'Hello' to Spanish"
Classification: {{"complexity": "simple", "intent": "factual", "domain": "general", "requires_search": false, "recommended_models": ["gpt-4o-mini"], "reasoning": "Simple translation of a single word.", "confidence": 0.99}}

Query: "What happened at CES 2025?"
Classification: {{"complexity": "complex", "intent": "factual", "domain": "technical", "requires_search": true, "recommended_models": ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], "reasoning": "TEMPORAL QUERY: CES 2025 is after knowledge cutoff (Oct 2023). Requires web search to get accurate information about this future event.", "confidence": 0.95}}

Now classify this query:

Query: "{question}"

Respond with ONLY a valid JSON object in this exact format:
{{"complexity": "simple|moderate|complex", "intent": "factual|creative|analytical|procedural|comparative", "domain": "coding|technical|general|creative|research", "requires_search": true|false, "recommended_models": ["model1", "model2"], "reasoning": "explanation", "confidence": 0.0-1.0}}"""


class RouterService:
    """Service for intelligent query routing."""
    
    def __init__(self):
        """Initialize the router service."""
        self.settings = get_settings()
        self.client: Optional[AsyncOpenAI] = None
        self.classifier_model = "gpt-4o-mini"  # Fast and cheap for classification
        self._initialize_client()
        
        # Routing statistics
        self.stats = {
            "total_queries": 0,
            "simple_queries": 0,
            "moderate_queries": 0,
            "complex_queries": 0,
            "total_cost": 0.0,
            "total_savings": 0.0,
            "model_usage": {},
            "fallback_count": 0,
        }
    
    def _initialize_client(self):
        """Initialize the OpenAI client."""
        if self.settings.validate_api_key():
            self.client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                organization=self.settings.openai_org_id,
                timeout=30,  # Shorter timeout for classifier
            )
            logger.info("Router service client initialized")
        else:
            logger.warning("Router service: API key not configured")
    
    def _get_cache_key(self, question: str) -> str:
        """Generate cache key for classification."""
        return hashlib.sha256(question.lower().strip().encode()).hexdigest()
    
    def _get_cached_classification(self, question: str) -> Optional[QueryClassification]:
        """Get cached classification if available and not expired."""
        cache_key = self._get_cache_key(question)
        if cache_key in _classification_cache:
            classification, timestamp = _classification_cache[cache_key]
            if datetime.utcnow() - timestamp < CLASSIFICATION_CACHE_TTL:
                logger.info(f"Classification cache hit for question hash: {cache_key[:8]}")
                return classification
            else:
                # Expired, remove from cache
                del _classification_cache[cache_key]
        return None
    
    def _cache_classification(self, question: str, classification: QueryClassification):
        """Cache classification result."""
        cache_key = self._get_cache_key(question)
        _classification_cache[cache_key] = (classification, datetime.utcnow())
        logger.info(f"Cached classification for question hash: {cache_key[:8]}")
    
    async def classify_query(
        self,
        question: str,
        temporal_hint: Optional[TemporalDetectionResult] = None
    ) -> Tuple[QueryClassification, float, TokenUsage]:
        """
        Classify a query using gpt-4o-mini for speed and cost efficiency.
        Applies temporal overrides if temporal detection provided.
        
        Args:
            question: The query to classify
            temporal_hint: Optional pre-computed temporal detection result
            
        Returns:
            Tuple of (QueryClassification, cost, token_usage)
        """
        start_time = time.time()
        
        # Check cache first
        cached = self._get_cached_classification(question)
        if cached:
            return cached, 0.0, TokenUsage()
        
        if not self.client:
            logger.error("OpenAI client not initialized - API key may be missing")
            raise ValueError("OpenAI client not initialized. Check API key configuration.")
        
        try:
            prompt = CLASSIFICATION_PROMPT.format(question=question)
            logger.info(f"Classifying query with model: {self.classifier_model}")
            logger.debug(f"Classification prompt length: {len(prompt)} chars")
            
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.classifier_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a query classifier. Respond only with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=300,
                    temperature=0.1,  # Low temperature for consistent classification
                    response_format={"type": "json_object"}
                ),
                timeout=10  # Fast timeout for classifier
            )
            
            # Parse response
            response_text = response.choices[0].message.content or "{}"
            classification_data = json.loads(response_text)
            
            # Build classification object
            classification = QueryClassification(
                complexity=ComplexityLevel(classification_data.get("complexity", "moderate")),
                intent=QueryIntent(classification_data.get("intent", "factual")),
                domain=QueryDomain(classification_data.get("domain", "general")),
                requires_search=classification_data.get("requires_search", False),
                recommended_models=classification_data.get("recommended_models", ["gpt-4o-mini"]),
                reasoning=classification_data.get("reasoning", "Default classification"),
                confidence=classification_data.get("confidence", 0.8),
                temporal_scope=temporal_hint.temporal_scope if temporal_hint else TemporalScope.EVERGREEN
            )
            
            # Apply temporal overrides if temporal hint provided
            if temporal_hint and temporal_hint.is_temporal:
                original_complexity = classification.complexity
                original_search = classification.requires_search
                
                # CRITICAL: Temporal queries should NEVER be simple
                if classification.complexity == ComplexityLevel.SIMPLE:
                    classification.complexity = ComplexityLevel.MODERATE
                    logger.info(f"Temporal override: Upgraded complexity from SIMPLE to MODERATE")
                
                # Ensure requires_search is true for temporal queries needing current data
                if temporal_hint.requires_current_data and not classification.requires_search:
                    classification.requires_search = True
                    logger.info(f"Temporal override: Set requires_search=True")
                
                # Update reasoning to reflect temporal detection
                temporal_note = f" [TEMPORAL OVERRIDE: {temporal_hint.reasoning}]"
                classification.reasoning += temporal_note
                classification.temporal_scope = temporal_hint.temporal_scope
            
            # Calculate cost
            usage = response.usage
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )
            cost = self._calculate_cost(self.classifier_model, token_usage)
            
            # Cache the classification
            self._cache_classification(question, classification)
            
            elapsed = time.time() - start_time
            logger.info(f"Query classified in {elapsed:.2f}s: complexity={classification.complexity.value}, "
                       f"intent={classification.intent.value}, domain={classification.domain.value}")
            
            return classification, cost, token_usage
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification response: {e}")
            # Return default moderate classification
            return self._default_classification(), 0.0, TokenUsage()
        except asyncio.TimeoutError:
            logger.error("Classification timed out after 10 seconds")
            return self._default_classification(), 0.0, TokenUsage()
        except Exception as e:
            logger.error(f"Classification failed with error type {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return self._default_classification(), 0.0, TokenUsage()
    
    def _default_classification(self) -> QueryClassification:
        """Return default classification for fallback scenarios."""
        return QueryClassification(
            complexity=ComplexityLevel.MODERATE,
            intent=QueryIntent.FACTUAL,
            domain=QueryDomain.GENERAL,
            requires_search=False,
            recommended_models=["gpt-4o-mini", "gpt-4o"],
            reasoning="Default classification due to classifier failure",
            confidence=0.5
        )
    
    def _calculate_cost(self, model: str, token_usage: TokenUsage) -> float:
        """Calculate cost for a model call."""
        if model not in MODEL_COSTS:
            return 0.0
        costs = MODEL_COSTS[model]
        return (token_usage.prompt_tokens * costs["input"] / 1000) + \
               (token_usage.completion_tokens * costs["output"] / 1000)
    
    def determine_execution_path(
        self,
        classification: QueryClassification,
        override_models: Optional[List[str]] = None,
        force_synthesis: Optional[bool] = None,
        temporal_detection: Optional[TemporalDetectionResult] = None
    ) -> RoutingDecision:
        """
        Determine execution path based on classification.
        
        Args:
            classification: The query classification
            override_models: Optional list of models to use (overrides automatic selection)
            force_synthesis: Optional flag to force synthesis
            temporal_detection: Optional temporal detection result for routing adjustments
            
        Returns:
            RoutingDecision with models to use and synthesis flag
        """
        min_models_for_temporal = 2  # Minimum models for temporal queries
        add_search_recommendation = False
        
        # Handle manual override
        if override_models:
            models = override_models
            use_synthesis = force_synthesis if force_synthesis is not None else len(models) > 1
            synthesis_model = self.settings.synthesis_model if use_synthesis else None
            rationale = f"Manual override: using specified models {models}"
        else:
            # Automatic routing based on complexity
            if classification.complexity == ComplexityLevel.SIMPLE:
                models = ["gpt-4o-mini"]
                use_synthesis = False
                synthesis_model = None
                rationale = (f"Simple query ({classification.intent.value}, {classification.domain.value}): "
                           f"Using single fast model for cost efficiency. {classification.reasoning}")
            
            elif classification.complexity == ComplexityLevel.MODERATE:
                models = ["gpt-4o-mini", "gpt-4o"]
                use_synthesis = False
                synthesis_model = None
                rationale = (f"Moderate query ({classification.intent.value}, {classification.domain.value}): "
                           f"Using two models for balanced quality. {classification.reasoning}")
            
            else:  # COMPLEX
                models = ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
                use_synthesis = True
                synthesis_model = self.settings.synthesis_model
                rationale = (f"Complex query ({classification.intent.value}, {classification.domain.value}): "
                           f"Using all models with synthesis for comprehensive answer. {classification.reasoning}")
        
        # Apply temporal routing adjustments
        if temporal_detection and temporal_detection.is_temporal:
            # Ensure minimum models for temporal queries
            if len(models) < min_models_for_temporal:
                if "gpt-4o" not in models:
                    models.append("gpt-4o")
                rationale += f" [TEMPORAL: Added models to meet minimum {min_models_for_temporal} for temporal queries]"
            
            # Recommend search for temporal queries requiring current data
            if temporal_detection.requires_current_data:
                add_search_recommendation = True
                rationale += " [TEMPORAL: Web search recommended for current data]"
        
        # Override synthesis if explicitly requested
        if force_synthesis is not None:
            use_synthesis = force_synthesis
            if use_synthesis and not synthesis_model:
                synthesis_model = self.settings.synthesis_model
        
        # Estimate cost
        estimated_cost = self._estimate_cost(models, use_synthesis)
        
        # Estimate time (rough estimates based on typical response times)
        time_estimates = {
            "gpt-4o-mini": 1.5,
            "gpt-4o": 3.0,
            "gpt-4-turbo": 5.0,
            "gpt-5.2": 4.0,
        }
        # Models run in parallel, so time is max of individual times
        model_time = max(time_estimates.get(m, 3.0) for m in models)
        synthesis_time = time_estimates.get(synthesis_model, 4.0) if use_synthesis else 0
        estimated_time = model_time + synthesis_time
        
        return RoutingDecision(
            models_to_use=models,
            use_synthesis=use_synthesis,
            synthesis_model=synthesis_model,
            estimated_cost=estimated_cost,
            estimated_time_seconds=estimated_time,
            routing_rationale=rationale,
            minimum_models_for_temporal=min_models_for_temporal if (temporal_detection and temporal_detection.is_temporal) else None,
            add_web_search_recommendation=add_search_recommendation
        )
    
    def _estimate_cost(self, models: List[str], use_synthesis: bool) -> float:
        """Estimate cost for a query execution."""
        # Assume average tokens: 500 input, 1000 output per model
        avg_input = 500
        avg_output = 1000
        
        total_cost = 0.0
        for model in models:
            if model in MODEL_COSTS:
                costs = MODEL_COSTS[model]
                total_cost += (avg_input * costs["input"] / 1000) + (avg_output * costs["output"] / 1000)
        
        if use_synthesis:
            # Synthesis has larger input (all responses) but moderate output
            synth_input = avg_output * len(models) + 500  # All responses + prompt
            synth_output = 800
            synth_model = self.settings.synthesis_model
            if synth_model in MODEL_COSTS:
                costs = MODEL_COSTS[synth_model]
                total_cost += (synth_input * costs["input"] / 1000) + (synth_output * costs["output"] / 1000)
        
        return round(total_cost, 6)
    
    def calculate_cost_breakdown(
        self,
        model_responses: List[ModelResponse],
        synthesis_result: Optional[SynthesisResult],
        classification_cost: float,
        search_cost: float = 0.0
    ) -> CostBreakdown:
        """Calculate detailed cost breakdown."""
        model_costs = {}
        for response in model_responses:
            model_costs[response.model_name] = response.cost_estimate
        
        synthesis_cost = synthesis_result.cost_estimate if synthesis_result else 0.0
        total_cost = sum(model_costs.values()) + synthesis_cost + classification_cost + search_cost
        
        # Calculate what full ensemble would have cost
        full_ensemble_models = ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
        full_ensemble_cost = 0.0
        avg_input, avg_output = 500, 1000
        for model in full_ensemble_models:
            if model in MODEL_COSTS:
                costs = MODEL_COSTS[model]
                full_ensemble_cost += (avg_input * costs["input"] / 1000) + (avg_output * costs["output"] / 1000)
        
        # Add synthesis cost for full ensemble
        synth_model = self.settings.synthesis_model
        if synth_model in MODEL_COSTS:
            synth_input = avg_output * 3 + 500
            synth_output = 800
            costs = MODEL_COSTS[synth_model]
            full_ensemble_cost += (synth_input * costs["input"] / 1000) + (synth_output * costs["output"] / 1000)
        
        savings = max(0, full_ensemble_cost - total_cost)
        savings_percentage = (savings / full_ensemble_cost * 100) if full_ensemble_cost > 0 else 0
        
        return CostBreakdown(
            model_costs=model_costs,
            synthesis_cost=synthesis_cost,
            classification_cost=classification_cost,
            total_cost=round(total_cost, 6),
            full_ensemble_cost=round(full_ensemble_cost, 6),
            savings=round(savings, 6),
            savings_percentage=round(savings_percentage, 2),
            search_cost=round(search_cost, 6)
        )
    
    async def route_and_answer(
        self,
        question: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        override_models: Optional[List[str]] = None,
        force_synthesis: Optional[bool] = None,
        enable_search: bool = True
    ) -> RouteAndAnswerResponse:
        """
        Main entry point: classify query, route to optimal models, and return answer.
        Now includes temporal detection and optional web search integration.
        
        Args:
            question: The question to answer
            max_tokens: Maximum tokens per model response
            temperature: Temperature for generation
            override_models: Optional list of models to use
            force_synthesis: Optional flag to force synthesis
            enable_search: Whether to enable web search for temporal queries
            
        Returns:
            RouteAndAnswerResponse with full details including temporal metadata
        """
        start_time = time.time()
        timestamp = datetime.utcnow()
        execution_times: Dict[str, float] = {}
        fallback_used = False
        fallback_reason = None
        routing_override_applied = False
        routing_override_reason = None
        ui_warning_message = None
        was_search_used = False
        search_results_data = None
        search_cost = 0.0
        augmented_question = question  # Will be augmented with search context if needed
        
        # Step 0: Temporal Detection (fast, pre-classification)
        temporal_start = time.time()
        temporal_detection = detect_temporal_query(question)
        execution_times["temporal_detection"] = (time.time() - temporal_start) * 1000
        
        if temporal_detection.is_temporal:
            logger.info(f"Temporal query detected: scope={temporal_detection.temporal_scope.value}, "
                       f"keywords={temporal_detection.detected_keywords}, years={temporal_detection.detected_years}")
        
        # Step 1: Classify the query (with temporal hints)
        classification_start = time.time()
        try:
            classification, classification_cost, _ = await self.classify_query(question, temporal_detection)
        except Exception as e:
            logger.error(f"Classification failed, using fallback: {e}")
            classification = self._default_classification()
            classification_cost = 0.0
            fallback_used = True
            fallback_reason = f"Classification failed: {str(e)}"
        execution_times["classification"] = (time.time() - classification_start) * 1000
        
        # Check if temporal override was applied
        if temporal_detection.is_temporal and temporal_detection.requires_current_data:
            routing_override_applied = True
            routing_override_reason = f"Temporal query detected: {temporal_detection.reasoning}"
        
        # Step 2: Web search for temporal queries using Perplexity (preferred) or fallback
        search_time_ms = 0.0
        perplexity_used = False
        perplexity_answer = None
        perplexity_cost_data = None
        
        if temporal_detection.requires_current_data and enable_search:
            search_start = time.time()
            
            # Try Perplexity first (preferred - combines search + reasoning)
            if perplexity_service.is_configured():
                try:
                    logger.info("Using Perplexity API for real-time search + reasoning")
                    perplexity_response = await perplexity_service.search(
                        query=question,
                        model=self.settings.perplexity_model,
                        recency_filter=self.settings.perplexity_recency_filter,
                    )
                    
                    if perplexity_response.success and perplexity_response.answer:
                        perplexity_used = True
                        was_search_used = True
                        perplexity_answer = perplexity_response.answer
                        perplexity_cost_data = perplexity_response.calculate_cost()
                        search_cost = perplexity_cost_data.get("total_cost", 0.0)
                        
                        search_results_data = {
                            "query": perplexity_response.query,
                            "results": [
                                {
                                    "title": c.title,
                                    "url": c.url,
                                    "snippet": c.snippet,
                                    "source": "perplexity"
                                }
                                for c in perplexity_response.citations
                            ],
                            "total_results": perplexity_response.citations_count,
                            "search_provider": f"perplexity ({perplexity_response.model})"
                        }
                        
                        # Format context for other models if needed
                        search_context = perplexity_service.format_for_context(perplexity_response)
                        augmented_question = f"{question}\n\n{search_context}"
                        
                        logger.info(
                            f"Perplexity search completed: {perplexity_response.citations_count} citations, "
                            f"cost=${search_cost:.4f}, {perplexity_response.response_time_ms:.0f}ms"
                        )
                        
                        ui_warning_message = (
                            f"✓ Real-time web search used (Perplexity {perplexity_response.model}). "
                            f"{perplexity_response.citations_count} sources cited."
                        )
                    else:
                        logger.warning(f"Perplexity search returned no results: {perplexity_response.error_message}")
                except Exception as e:
                    logger.warning(f"Perplexity search failed: {e}")
            
            # Fallback to Tavily/Serper if Perplexity not configured or failed
            if not perplexity_used and search_service.is_configured():
                try:
                    search_response = await search_service.search(question, max_results=5)
                    if search_response and search_response.results:
                        was_search_used = True
                        search_results_data = {
                            "query": search_response.query,
                            "results": [
                                {
                                    "title": r.title,
                                    "url": r.url,
                                    "snippet": r.snippet,
                                    "source": r.source
                                }
                                for r in search_response.results
                            ],
                            "total_results": search_response.total_results,
                            "search_provider": search_response.search_provider
                        }
                        search_context = search_service.format_search_context(search_response)
                        augmented_question = f"{question}\n\n{search_context}"
                        search_cost = 0.001
                        logger.info(f"Fallback search completed: {len(search_response.results)} results from {search_response.search_provider}")
                        
                        ui_warning_message = (
                            f"⚠️ This query asks about recent information. "
                            f"Web search was used to augment the response."
                        )
                except Exception as e:
                    logger.warning(f"Fallback web search failed (continuing without): {e}")
            
            # No search available
            if not was_search_used:
                ui_warning_message = (
                    f"⚠️ This query asks about information that may be more recent than the AI models' "
                    f"knowledge cutoff (October 2023). Consider verifying with current sources."
                )
            
            search_time_ms = (time.time() - search_start) * 1000
            execution_times["search"] = search_time_ms
        
        # Step 3: Determine execution path (with temporal context)
        routing_decision = self.determine_execution_path(
            classification, override_models, force_synthesis, temporal_detection
        )
        
        # Step 4: Execute with selected models (using augmented question if search was used)
        model_execution_start = time.time()
        model_execution_times: Dict[str, float] = {}
        
        try:
            model_responses = await llm_service.call_models_parallel(
                models=routing_decision.models_to_use,
                question=augmented_question,
                max_tokens=max_tokens,
                temperature=temperature,
                use_cache=True
            )
            
            # Track individual model times
            for response in model_responses:
                model_execution_times[response.model_name] = response.response_time_seconds * 1000
                
        except Exception as e:
            logger.error(f"Model execution failed, falling back to full ensemble: {e}")
            fallback_used = True
            fallback_reason = f"Model execution failed: {str(e)}"
            
            # Fallback to full ensemble
            try:
                model_responses = await llm_service.call_models_parallel(
                    models=["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
                    question=question,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    use_cache=True
                )
                routing_decision.models_to_use = ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
                routing_decision.use_synthesis = True
                routing_decision.routing_rationale = "Fallback to full ensemble due to routing failure"
                
                for response in model_responses:
                    model_execution_times[response.model_name] = response.response_time_seconds * 1000
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                raise
        
        execution_times["model_execution"] = (time.time() - model_execution_start) * 1000
        
        # Step 5: Synthesize if needed
        synthesis_result = None
        synthesis_time = 0.0
        
        successful_responses = [r for r in model_responses if r.success]
        
        if routing_decision.use_synthesis and len(successful_responses) > 1:
            synthesis_start = time.time()
            try:
                synthesis_result = await synthesis_service.synthesize(
                    question=question,
                    model_responses=successful_responses,
                    synthesis_model=routing_decision.synthesis_model,
                    max_tokens=1500
                )
                synthesis_time = (time.time() - synthesis_start) * 1000
            except Exception as e:
                logger.error(f"Synthesis failed: {e}")
                synthesis_result = None
        
        execution_times["synthesis"] = synthesis_time
        
        # Determine final answer
        if synthesis_result:
            final_answer = synthesis_result.synthesized_answer
        elif successful_responses:
            # Use the best response (prefer in order: gpt-4-turbo, gpt-4o, gpt-4o-mini)
            priority_order = ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
            best_response = successful_responses[0]
            for model in priority_order:
                for response in successful_responses:
                    if response.model_name == model:
                        best_response = response
                        break
            final_answer = best_response.response_text
        else:
            final_answer = "Unable to generate a response. Please try again."
        
        # Calculate cost breakdown
        cost_breakdown = self.calculate_cost_breakdown(
            model_responses, synthesis_result, classification_cost, search_cost
        )
        
        # Build execution metrics
        total_time = (time.time() - start_time) * 1000
        execution_metrics = ExecutionMetrics(
            classification_time_ms=execution_times.get("classification", 0),
            model_execution_time_ms=model_execution_times,
            synthesis_time_ms=execution_times.get("synthesis", 0),
            total_time_ms=total_time,
            temporal_detection_time_ms=execution_times.get("temporal_detection", 0),
            search_time_ms=search_time_ms
        )
        
        # Update statistics
        self._update_stats(classification.complexity, cost_breakdown, model_responses)
        
        # Log routing decision
        logger.info(
            f"Route complete: complexity={classification.complexity.value}, "
            f"models={routing_decision.models_to_use}, "
            f"synthesis={routing_decision.use_synthesis}, "
            f"temporal={temporal_detection.is_temporal}, "
            f"search_used={was_search_used}, "
            f"cost=${cost_breakdown.total_cost:.4f}, "
            f"savings=${cost_breakdown.savings:.4f} ({cost_breakdown.savings_percentage:.1f}%), "
            f"time={total_time:.0f}ms"
        )
        
        return RouteAndAnswerResponse(
            question=question,
            classification=classification,
            routing_decision=routing_decision,
            models_used=routing_decision.models_to_use,
            individual_responses=model_responses,
            final_answer=final_answer,
            synthesis=synthesis_result,
            cost_breakdown=cost_breakdown,
            execution_metrics=execution_metrics,
            timestamp=timestamp,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            temporal_detection=temporal_detection,
            was_search_used=was_search_used,
            search_results=search_results_data,
            routing_override_applied=routing_override_applied,
            routing_override_reason=routing_override_reason,
            ui_warning_message=ui_warning_message
        )
    
    def _update_stats(
        self,
        complexity: ComplexityLevel,
        cost_breakdown: CostBreakdown,
        responses: List[ModelResponse]
    ):
        """Update routing statistics."""
        self.stats["total_queries"] += 1
        
        if complexity == ComplexityLevel.SIMPLE:
            self.stats["simple_queries"] += 1
        elif complexity == ComplexityLevel.MODERATE:
            self.stats["moderate_queries"] += 1
        else:
            self.stats["complex_queries"] += 1
        
        self.stats["total_cost"] += cost_breakdown.total_cost
        self.stats["total_savings"] += cost_breakdown.savings
        
        for response in responses:
            model = response.model_name
            if model not in self.stats["model_usage"]:
                self.stats["model_usage"][model] = 0
            self.stats["model_usage"][model] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        avg_savings = 0.0
        if self.stats["total_queries"] > 0:
            total_full_cost = self.stats["total_cost"] + self.stats["total_savings"]
            if total_full_cost > 0:
                avg_savings = (self.stats["total_savings"] / total_full_cost) * 100
        
        return {
            "total_queries": self.stats["total_queries"],
            "simple_queries": self.stats["simple_queries"],
            "moderate_queries": self.stats["moderate_queries"],
            "complex_queries": self.stats["complex_queries"],
            "total_cost": round(self.stats["total_cost"], 4),
            "total_savings": round(self.stats["total_savings"], 4),
            "average_savings_percentage": round(avg_savings, 2),
            "model_usage_distribution": self.stats["model_usage"],
            "fallback_count": self.stats["fallback_count"],
        }
    
    def clear_classification_cache(self):
        """Clear the classification cache."""
        _classification_cache.clear()
        logger.info("Classification cache cleared")


# Global router service instance
router_service = RouterService()
