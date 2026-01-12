"""
Time-Travel Answers Service

This service implements the "Time-Travel Answers" feature that shows users
how an answer would have changed across different time periods, demonstrating
answer evolution and temporal sensitivity.

Key Features:
1. Temporal sensitivity classification (HIGH/MEDIUM/LOW)
2. Complexity-aware routing (preserves classification across snapshots)
3. Historical snapshot generation at multiple time points
4. Evolution narrative synthesis
5. Answer comparison across time periods
"""

import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from openai import AsyncOpenAI

from ..config import get_settings, ModelConfig
from ..schemas import (
    ComplexityLevel, QueryIntent, QueryDomain, TemporalScope,
    ModelResponse, TokenUsage, CacheStatus
)
from ..utils.logging import get_logger
from ..utils.cache import cache_manager

logger = get_logger(__name__)


class TemporalSensitivityLevel(str, Enum):
    """Classification of how temporally sensitive a question is."""
    HIGH = "high"      # Answer changes significantly over time
    MEDIUM = "medium"  # Answer may change moderately
    LOW = "low"        # Answer is mostly timeless
    NONE = "none"      # Answer doesn't change at all


class SnapshotComplexity(str, Enum):
    """Complexity classification for snapshot generation routing."""
    SIMPLE = "simple"      # Single model (gpt-4o-mini)
    MODERATE = "moderate"  # Better model (gpt-4o)
    COMPLEX = "complex"    # Best model or ensemble (gpt-4-turbo)


@dataclass
class TimeSnapshot:
    """A snapshot of the answer at a specific point in time."""
    date: datetime
    date_label: str  # e.g., "Jan 1, 2024 - Pre-GPT-4o Era"
    answer: str
    key_changes: List[str] = field(default_factory=list)
    data_points: List[str] = field(default_factory=list)
    model_used: str = ""
    tokens_used: int = 0
    cost_estimate: float = 0.0
    response_time_seconds: float = 0.0


@dataclass
class TimeTravelResult:
    """Complete result of a time-travel analysis."""
    question: str
    temporal_sensitivity: TemporalSensitivityLevel
    sensitivity_reasoning: str
    base_complexity: SnapshotComplexity = SnapshotComplexity.MODERATE  # CRITICAL: Preserved complexity
    snapshots: List[TimeSnapshot] = field(default_factory=list)
    evolution_narrative: str = ""
    insights: List[str] = field(default_factory=list)
    change_velocity: str = ""  # "fast", "moderate", "slow", "none"
    future_outlook: str = ""
    total_cost: float = 0.0
    total_time_seconds: float = 0.0
    is_eligible: bool = True  # Whether time-travel is applicable
    skip_reason: Optional[str] = None  # Reason if not eligible
    routing_validation_passed: bool = True  # Whether routing validation passed


# Patterns for HIGH temporal sensitivity
HIGH_SENSITIVITY_PATTERNS = [
    # Current events & news
    r'\b(who is the current|who is|who\'s the)\s+(president|ceo|leader|prime minister|chairman)\b',
    r'\b(current|latest|recent|new)\s+(events?|news|developments?|updates?|breakthroughs?)\b',
    r'\b(what\'s happening|what is happening|what happened)\s+(today|now|recently)\b',
    r'\bbreaking news\b',
    
    # Technology releases & milestones
    r'\b(latest|newest|recent|current)\s+(ai|llm|gpt|claude|gemini|model|version|release)\b',
    r'\bwhat (ai|llm|gpt|language) models?\s+(exist|are available|are there)\b',
    r'\b(chatgpt|openai|anthropic|google|meta)\s+(released?|launched?|announced?)\b',
    
    # Market/financial data
    r'\b(stock|market|crypto|bitcoin|ethereum)\s+(price|performance|value)\b',
    r'\b(tech stocks?|s&p 500|nasdaq|dow jones)\s+(performing|trading)\b',
    r'\bmarket\s+(trends?|conditions?|outlook)\b',
    
    # Sports/competitive results
    r'\bwho won\s+(the|last|this year\'s)\s+\w+\s*(championship|cup|bowl|series|title|election|award)\b',
    r'\b(super bowl|world cup|olympics|grammy|oscar|emmy)\s+(winner|champion|results?)\b',
    r'\bcurrent\s+(champion|leader|holder|ranking)\b',
    
    # Rankings/leaderboards
    r'\b(top|best|most popular)\s+\d+\s+(programming languages?|frameworks?|tools?|apps?|games?)\b',
    r'\b(trending|popular)\s+(on|in)\s+(social media|twitter|x|tiktok|youtube)\b',
    r'\b(most used|most popular|top)\s+\w+\s+(in\s+)?\d{4}\b',
    
    # Trending topics
    r'\bwhat\'?s?\s+trending\b',
    r'\bviral\s+(content|video|post|meme)\b',
    
    # Recent discoveries/research
    r'\b(latest|recent|new)\s+(findings?|discoveries?|research|studies?|papers?)\b',
    r'\bbreakthrough\s+(in|for)\b',
    
    # Explicit time markers after model cutoff
    r'\b202[4-9]\b',
    r'\b203\d\b',
    r'\b(this year|this month|this week|today|right now)\b',
]

# Patterns for MEDIUM temporal sensitivity
MEDIUM_SENSITIVITY_PATTERNS = [
    # Business/product evolution
    r'\bhow has\s+\w+\s+(changed|evolved|grown|developed)\b',
    r'\b(company|product|service)\s+(strategy|direction|evolution)\b',
    
    # Scientific understanding
    r'\b(current|modern)\s+(understanding|knowledge|view)\s+of\b',
    r'\bstate of\s+(the art|research|science)\b',
    
    # Industry standards
    r'\b(best practices?|standards?|guidelines?)\s+(in|for)\b',
    r'\b(recommended|suggested)\s+(approach|method|practice)\b',
    
    # Regulatory landscape
    r'\b(regulations?|laws?|policies?|compliance)\s+(around|for|about)\b',
    r'\b(gdpr|ccpa|hipaa|data privacy)\s+(requirements?|updates?)\b',
]

# Patterns for LOW/NO temporal sensitivity (should skip time-travel)
TIMELESS_PATTERNS = [
    # Pure facts
    r'\bhow many\s+(continents?|planets?|states?|countries?)\b',
    r'\bwhat is\s+the\s+(capital|population|area|distance)\s+of\b',
    
    # Eternal truths
    r'\bwhat is\s+(photosynthesis|gravity|electricity|evolution)\b',
    r'\bhow does\s+(the body|the heart|the brain|digestion)\s+work\b',
    
    # Timeless technical concepts
    r'\bwhat is\s+(recursion|polymorphism|inheritance|encapsulation)\b',
    r'\b(explain|define)\s+(algorithm|data structure|design pattern)\b',
    
    # Philosophical questions
    r'\bwhat is\s+(happiness|love|meaning|consciousness|ethics)\b',
    r'\bwhy do\s+(humans?|we|people)\b',
    
    # Basic definitions
    r'\bwhat is\s+a\s+(database|server|variable|function|class)\b',
    r'\bdefinition of\b',
]


def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compile regex patterns for efficiency."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Pre-compile all patterns
_high_patterns = compile_patterns(HIGH_SENSITIVITY_PATTERNS)
_medium_patterns = compile_patterns(MEDIUM_SENSITIVITY_PATTERNS)
_timeless_patterns = compile_patterns(TIMELESS_PATTERNS)


class TimeTravelService:
    """Service for generating time-travel answers showing answer evolution."""
    
    # Model routing configuration based on complexity
    MODEL_ROUTING = {
        SnapshotComplexity.SIMPLE: "gpt-4o-mini",
        SnapshotComplexity.MODERATE: "gpt-4o",
        SnapshotComplexity.COMPLEX: "gpt-4-turbo",
    }
    
    # Complexity patterns - HIGH indicators for COMPLEX routing
    COMPLEX_PATTERNS = [
        r'\b(best|top|leading|most advanced|state of the art)\b',
        r'\b(compare|comparison|versus|vs\.?|difference between)\b',
        r'\b(architecture|design|implementation|strategy)\b',
        r'\b(comprehensive|detailed|in-depth|thorough)\b',
        r'\b(analysis|analyze|evaluate|assessment)\b',
        r'\b(explain|how does|why does|mechanism)\b',
        r'\b(future|prediction|forecast|outlook|trajectory)\b',
        r'\b(evolution|history|development|progress)\b',
        r'\b(implications|impact|consequences|effects)\b',
    ]
    
    # Compile patterns
    _complex_patterns = None
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self._cache: Dict[str, Tuple[TimeTravelResult, datetime]] = {}
        self._cache_ttl = timedelta(hours=24)
        
        # Compile complex patterns
        if TimeTravelService._complex_patterns is None:
            TimeTravelService._complex_patterns = [
                re.compile(p, re.IGNORECASE) for p in self.COMPLEX_PATTERNS
            ]
    
    def classify_question_complexity(self, question: str) -> Tuple[SnapshotComplexity, str]:
        """
        Classify the complexity of a question for model routing.
        
        CRITICAL: This classification is done ONCE and preserved across all time-point queries.
        This prevents re-routing that would lose the original complexity signal.
        
        Args:
            question: The user's question
            
        Returns:
            Tuple of (complexity_level, reasoning)
        """
        question_lower = question.lower()
        
        # Count complexity indicators
        complex_matches = []
        for pattern in self._complex_patterns:
            match = pattern.search(question_lower)
            if match:
                complex_matches.append(match.group())
        
        # Length-based heuristic
        word_count = len(question.split())
        
        # Determine complexity
        if len(complex_matches) >= 3 or (len(complex_matches) >= 2 and word_count > 15):
            return (
                SnapshotComplexity.COMPLEX,
                f"High complexity indicators found: {complex_matches[:3]}. Using best model for substantive analysis."
            )
        elif len(complex_matches) >= 1 or word_count > 10:
            return (
                SnapshotComplexity.MODERATE,
                f"Moderate complexity: {complex_matches[:2] if complex_matches else 'multi-word question'}. Using balanced model."
            )
        else:
            # For temporal queries, minimum is MODERATE to ensure quality
            return (
                SnapshotComplexity.MODERATE,
                "Temporal queries default to moderate complexity for quality temporal synthesis."
            )
    
    def get_model_for_complexity(self, complexity: SnapshotComplexity) -> str:
        """
        Get the appropriate model for a given complexity level.
        
        CRITICAL: This ensures all snapshots use the same quality model
        based on the original complexity classification.
        """
        return self.MODEL_ROUTING.get(complexity, "gpt-4o")
    
    def validate_temporal_routing(self, snapshots: List[TimeSnapshot]) -> Tuple[bool, str]:
        """
        Validate that temporal snapshots used appropriate routing.
        
        Checks:
        1. Not all snapshots from gpt-4o-mini (indicates routing bug)
        2. Answers are substantive (not shallow)
        3. Answers show diversity across time periods
        
        Returns:
            Tuple of (passed, reason)
        """
        if not snapshots:
            return (False, "No snapshots generated")
        
        # Check 1: Model diversity check for complex questions
        models_used = set(s.model_used for s in snapshots)
        all_mini = len(models_used) == 1 and "gpt-4o-mini" in models_used
        
        # Check 2: Depth check - answers should be substantive
        shallow_count = 0
        for snapshot in snapshots:
            if len(snapshot.answer) < 400:  # Temporal answers should be meaty
                shallow_count += 1
        
        if shallow_count > len(snapshots) // 2:
            return (False, f"Too many shallow answers ({shallow_count}/{len(snapshots)})")
        
        # Check 3: Diversity check - snapshots should show distinct differences
        if len(snapshots) >= 2:
            first_words = set(snapshots[0].answer.lower().split()[:50])
            last_words = set(snapshots[-1].answer.lower().split()[:50])
            
            if first_words and last_words:
                overlap = len(first_words & last_words) / len(first_words | last_words)
                if overlap > 0.9:
                    logger.warning(f"High answer similarity ({overlap:.1%}) - temporal evolution may be weak")
        
        return (True, "Routing validation passed")
        
    def classify_temporal_sensitivity(self, question: str) -> Tuple[TemporalSensitivityLevel, str]:
        """
        Classify the temporal sensitivity of a question.
        
        Returns:
            Tuple of (sensitivity_level, reasoning)
        """
        question_lower = question.lower()
        reasoning_parts = []
        
        # Check for timeless patterns first (these should skip time-travel)
        for pattern in _timeless_patterns:
            if pattern.search(question_lower):
                return (
                    TemporalSensitivityLevel.NONE,
                    "Question asks about timeless facts or concepts that don't change over time."
                )
        
        # Check for HIGH sensitivity patterns
        high_matches = []
        for pattern in _high_patterns:
            match = pattern.search(question_lower)
            if match:
                high_matches.append(match.group())
        
        if high_matches:
            reasoning_parts.append(f"High temporal indicators: {high_matches[:3]}")
            return (
                TemporalSensitivityLevel.HIGH,
                f"Question contains high temporal sensitivity indicators: {', '.join(high_matches[:3])}. Answer likely changes significantly over time."
            )
        
        # Check for MEDIUM sensitivity patterns
        medium_matches = []
        for pattern in _medium_patterns:
            match = pattern.search(question_lower)
            if match:
                medium_matches.append(match.group())
        
        if medium_matches:
            return (
                TemporalSensitivityLevel.MEDIUM,
                f"Question contains moderate temporal sensitivity indicators: {', '.join(medium_matches[:3])}. Answer may evolve over time."
            )
        
        # Check for explicit year references after model cutoff
        year_pattern = re.compile(r'\b(202[4-9]|203\d)\b')
        year_matches = year_pattern.findall(question)
        if year_matches:
            return (
                TemporalSensitivityLevel.HIGH,
                f"Question references years {year_matches} which are after model knowledge cutoff. Requires time-travel analysis."
            )
        
        # Default to LOW sensitivity
        return (
            TemporalSensitivityLevel.LOW,
            "No strong temporal indicators detected. Answer is relatively stable over time."
        )
    
    def identify_time_points(
        self,
        question: str,
        sensitivity: TemporalSensitivityLevel
    ) -> List[Tuple[datetime, str]]:
        """
        Identify optimal time points for snapshots based on the question.
        
        Returns:
            List of (datetime, label) tuples
        """
        today = datetime.now()
        current_year = today.year
        
        # Check for year references in question
        year_pattern = re.compile(r'\b(20\d{2})\b')
        mentioned_years = [int(y) for y in year_pattern.findall(question)]
        
        # Determine time point strategy based on question content
        question_lower = question.lower()
        
        # AI/Tech-related questions (use AI milestone dates)
        if any(kw in question_lower for kw in ['ai', 'gpt', 'llm', 'chatgpt', 'claude', 'gemini', 'model']):
            return [
                (datetime(2023, 1, 1), "Jan 2023 - Pre-GPT-4 Era"),
                (datetime(2023, 3, 14), "Mar 2023 - GPT-4 Release"),
                (datetime(2023, 11, 6), "Nov 2023 - GPT-4 Turbo & GPTs"),
                (datetime(2024, 5, 13), "May 2024 - GPT-4o Release"),
                (datetime(current_year, today.month, today.day), f"Today ({today.strftime('%b %d, %Y')})"),
            ]
        
        # Politics/Leadership questions
        if any(kw in question_lower for kw in ['president', 'election', 'government', 'leader', 'prime minister']):
            return [
                (datetime(2021, 1, 1), "Jan 2021 - Start of Biden Term"),
                (datetime(2023, 1, 1), "Jan 2023 - Mid-term Period"),
                (datetime(2024, 11, 5), "Nov 2024 - Election Day"),
                (datetime(2025, 1, 20), "Jan 2025 - New Term Start"),
                (datetime(current_year, today.month, today.day), f"Today ({today.strftime('%b %d, %Y')})"),
            ]
        
        # Sports/Championships (annual cycle)
        if any(kw in question_lower for kw in ['super bowl', 'world cup', 'championship', 'olympics', 'won', 'champion']):
            return [
                (datetime(2022, 1, 1), "2022 - Season Snapshot"),
                (datetime(2023, 1, 1), "2023 - Season Snapshot"),
                (datetime(2024, 1, 1), "2024 - Season Snapshot"),
                (datetime(2025, 1, 1), "2025 - Season Snapshot"),
                (datetime(current_year, today.month, today.day), f"Today ({today.strftime('%b %d, %Y')})"),
            ]
        
        # Market/Financial questions (quarterly snapshots)
        if any(kw in question_lower for kw in ['stock', 'market', 'crypto', 'bitcoin', 'price', 'trading']):
            return [
                (datetime(2023, 1, 1), "Q1 2023"),
                (datetime(2023, 7, 1), "Q3 2023"),
                (datetime(2024, 1, 1), "Q1 2024"),
                (datetime(2024, 7, 1), "Q3 2024"),
                (datetime(current_year, today.month, today.day), f"Today ({today.strftime('%b %d, %Y')})"),
            ]
        
        # Default time points for general temporal questions
        return [
            (datetime(2023, 1, 1), "Jan 2023 - Earlier Snapshot"),
            (datetime(2024, 1, 1), "Jan 2024 - Mid Snapshot"),
            (datetime(2025, 1, 1), "Jan 2025 - Recent Snapshot"),
            (datetime(current_year, today.month, today.day), f"Today ({today.strftime('%b %d, %Y')})"),
        ]
    
    async def generate_snapshot(
        self,
        question: str,
        date: datetime,
        date_label: str,
        previous_snapshot: Optional[TimeSnapshot] = None,
        model: str = "gpt-4o",
        complexity: SnapshotComplexity = SnapshotComplexity.MODERATE
    ) -> TimeSnapshot:
        """
        Generate an answer snapshot for a specific date.
        
        Args:
            question: The user's question
            date: The date to answer from
            date_label: Human-readable label for the date
            previous_snapshot: Previous snapshot for comparison (if any)
            model: Model to use for generation (based on preserved complexity)
            complexity: The complexity level (preserved from initial classification)
            
        Returns:
            TimeSnapshot with the answer
        """
        date_str = date.strftime("%B %d, %Y")
        
        # Enhanced system prompt signaling TEMPORAL SYNTHESIS task
        system_prompt = f"""You are answering questions as if the current date is {date_str}.

CRITICAL TEMPORAL SYNTHESIS RULES:
1. Answer ONLY using information that would have been available on {date_str}.
2. Do NOT reference any events, releases, announcements, or data after {date_str}.
3. If something major happens after {date_str} in real life, do NOT mention it.
4. Provide specific numbers, names, dates, and metrics where available.
5. Be COMPREHENSIVE and DETAILED - this is a temporal synthesis task requiring depth.

IMPORTANT: This answer is part of a TEMPORAL SYNTHESIS task showing answer evolution.
Provide detailed, substantive analysis that shows:
- The state of the field/topic as of {date_str}
- Specific models, products, developments, or events available then
- Context about what was significant at this time

Remember: From your perspective, today is {date_str}. You have NO knowledge of events after this date."""

        # Enhanced user prompt for temporal synthesis
        user_prompt = f"""Question: {question}

Answer this question as if you are responding on {date_str}. 

REQUIRED ELEMENTS FOR TEMPORAL SYNTHESIS:
1. A comprehensive answer based ONLY on knowledge available up to {date_str}
2. Specific data points, numbers, names, and dates from this time period
3. The state of affairs as of this exact date
4. Context about what was notable, new, or changing at this time

If the question asks about something that doesn't exist yet as of {date_str}, clearly state this.
If something was just announced or released near {date_str}, highlight that recency.

Provide a thorough, well-structured response with concrete details."""

        try:
            start_time = datetime.now()
            
            # Adjust max_tokens based on complexity
            max_tokens_map = {
                SnapshotComplexity.SIMPLE: 800,
                SnapshotComplexity.MODERATE: 1200,
                SnapshotComplexity.COMPLEX: 1500,
            }
            max_tokens = max_tokens_map.get(complexity, 1200)
            
            logger.info(f"Generating snapshot for {date_label} using model={model}, complexity={complexity.value}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.5,
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            answer = response.choices[0].message.content.strip()
            
            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            cost = ModelConfig.get_cost(model, input_tokens, output_tokens)
            
            # Extract key changes if we have a previous snapshot
            key_changes = []
            if previous_snapshot:
                key_changes = await self._extract_key_changes(
                    previous_snapshot.answer,
                    answer,
                    previous_snapshot.date_label,
                    date_label
                )
            
            # Extract data points from the answer
            data_points = self._extract_data_points(answer)
            
            return TimeSnapshot(
                date=date,
                date_label=date_label,
                answer=answer,
                key_changes=key_changes,
                data_points=data_points,
                model_used=model,
                tokens_used=total_tokens,
                cost_estimate=cost,
                response_time_seconds=response_time
            )
            
        except Exception as e:
            logger.error(f"Error generating snapshot for {date_str}: {e}")
            return TimeSnapshot(
                date=date,
                date_label=date_label,
                answer=f"Unable to generate snapshot for {date_str}: {str(e)}",
                key_changes=[],
                data_points=[],
                model_used=model,
                tokens_used=0,
                cost_estimate=0,
                response_time_seconds=0
            )
    
    async def _extract_key_changes(
        self,
        previous_answer: str,
        current_answer: str,
        previous_label: str,
        current_label: str
    ) -> List[str]:
        """Extract key changes between two snapshots."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are analyzing differences between two time-period answers. List 2-3 key changes concisely."
                    },
                    {
                        "role": "user",
                        "content": f"""Compare these two answers from different time periods:

PREVIOUS ({previous_label}):
{previous_answer[:500]}

CURRENT ({current_label}):
{current_answer[:500]}

List 2-3 key changes or differences as bullet points (one line each). If no significant changes, say "No major changes"."""
                    }
                ],
                max_tokens=200,
                temperature=0.3,
            )
            
            changes_text = response.choices[0].message.content.strip()
            
            # Parse bullet points
            changes = []
            for line in changes_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    changes.append(line.lstrip('-•* '))
                elif line and len(changes) < 3:
                    changes.append(line)
            
            return changes[:3]
            
        except Exception as e:
            logger.error(f"Error extracting key changes: {e}")
            return []
    
    def _extract_data_points(self, answer: str) -> List[str]:
        """Extract key data points from an answer."""
        data_points = []
        
        # Look for numbers with context
        number_patterns = [
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|trillion))?',  # Money
            r'\d+(?:\.\d+)?%',  # Percentages
            r'\d{4}',  # Years
            r'#\d+',  # Rankings
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, answer)
            for match in matches[:2]:  # Limit to 2 per pattern
                # Find the sentence containing this match
                sentences = answer.split('.')
                for sentence in sentences:
                    if match in sentence and len(sentence) < 150:
                        data_points.append(sentence.strip())
                        break
        
        return data_points[:3]  # Limit to 3 data points
    
    async def generate_evolution_narrative(
        self,
        question: str,
        snapshots: List[TimeSnapshot]
    ) -> Tuple[str, List[str], str, str]:
        """
        Generate the evolution narrative summarizing how answers changed.
        
        Returns:
            Tuple of (narrative, insights, change_velocity, future_outlook)
        """
        if len(snapshots) < 2:
            return ("Not enough snapshots for evolution analysis.", [], "none", "")
        
        # Build summary of all snapshots
        snapshot_summaries = []
        for i, snapshot in enumerate(snapshots):
            summary = f"**{snapshot.date_label}**: {snapshot.answer[:300]}..."
            if snapshot.key_changes:
                summary += f"\nChanges: {'; '.join(snapshot.key_changes)}"
            snapshot_summaries.append(summary)
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are analyzing how answers to a question evolved over time. 
Provide a comprehensive evolution summary with:
1. NARRATIVE: A flowing paragraph describing the evolution
2. INSIGHTS: 3 key patterns or observations (one line each, starting with "- ")
3. VELOCITY: Rate of change - one of: "fast", "moderate", "slow", "minimal"
4. OUTLOOK: Brief future trajectory prediction

Format your response exactly as:
NARRATIVE:
[Your narrative paragraph]

INSIGHTS:
- [Insight 1]
- [Insight 2]
- [Insight 3]

VELOCITY: [fast/moderate/slow/minimal]

OUTLOOK:
[Your outlook paragraph]"""
                    },
                    {
                        "role": "user",
                        "content": f"""Question: {question}

Timeline of answers:
{chr(10).join(snapshot_summaries)}

Analyze how the answer to this question evolved over time."""
                    }
                ],
                max_tokens=600,
                temperature=0.5,
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse the structured response
            narrative = ""
            insights = []
            velocity = "moderate"
            outlook = ""
            
            sections = response_text.split('\n\n')
            current_section = ""
            
            for section in sections:
                section = section.strip()
                if section.startswith('NARRATIVE:'):
                    narrative = section.replace('NARRATIVE:', '').strip()
                elif section.startswith('INSIGHTS:'):
                    insights_text = section.replace('INSIGHTS:', '').strip()
                    for line in insights_text.split('\n'):
                        line = line.strip()
                        if line.startswith('-'):
                            insights.append(line.lstrip('- '))
                elif section.startswith('VELOCITY:'):
                    velocity = section.replace('VELOCITY:', '').strip().lower()
                elif section.startswith('OUTLOOK:'):
                    outlook = section.replace('OUTLOOK:', '').strip()
            
            return (narrative, insights, velocity, outlook)
            
        except Exception as e:
            logger.error(f"Error generating evolution narrative: {e}")
            return (
                "Unable to generate evolution narrative due to an error.",
                ["Error analyzing evolution patterns"],
                "unknown",
                ""
            )
    
    def _check_answers_identical(self, snapshots: List[TimeSnapshot]) -> bool:
        """Check if all snapshot answers are essentially identical."""
        if len(snapshots) < 2:
            return True
        
        # Compare first and last answers for significant differences
        first = snapshots[0].answer.lower()
        last = snapshots[-1].answer.lower()
        
        # Simple similarity check - if very similar, consider identical
        # Count common words
        first_words = set(first.split())
        last_words = set(last.split())
        
        if not first_words or not last_words:
            return True
        
        intersection = first_words.intersection(last_words)
        union = first_words.union(last_words)
        
        similarity = len(intersection) / len(union) if union else 1.0
        
        # If more than 85% similar, consider identical
        return similarity > 0.85
    
    async def generate_time_travel_answer(
        self,
        question: str,
        force_time_travel: bool = False
    ) -> TimeTravelResult:
        """
        Main entry point for generating a time-travel answer.
        
        Args:
            question: The user's question
            force_time_travel: Force time-travel even for low sensitivity questions
            
        Returns:
            TimeTravelResult with complete time-travel analysis
        """
        start_time = datetime.now()
        
        # Check cache first
        cache_key = hashlib.md5(f"time_travel:{question}".encode()).hexdigest()
        if cache_key in self._cache:
            cached_result, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < self._cache_ttl:
                logger.info(f"Time-travel cache hit for question: {question[:50]}...")
                return cached_result
        
        # Step 1: Classify temporal sensitivity
        sensitivity, sensitivity_reasoning = self.classify_temporal_sensitivity(question)
        
        # Check if time-travel is enabled
        if not self.settings.time_travel_enabled and not force_time_travel:
            return TimeTravelResult(
                question=question,
                temporal_sensitivity=sensitivity,
                sensitivity_reasoning=sensitivity_reasoning,
                is_eligible=False,
                skip_reason="Time-travel feature is disabled in configuration."
            )
        
        # Step 2: Check if question is eligible for time-travel
        if sensitivity in [TemporalSensitivityLevel.LOW, TemporalSensitivityLevel.NONE] and not force_time_travel:
            return TimeTravelResult(
                question=question,
                temporal_sensitivity=sensitivity,
                sensitivity_reasoning=sensitivity_reasoning,
                is_eligible=False,
                skip_reason=f"Question has {sensitivity.value} temporal sensitivity. Time-travel not applicable for timeless questions."
            )
        
        # Step 3: CRITICAL FIX - Classify complexity ONCE before entering loop
        # This complexity level will be preserved for ALL time-point queries
        base_complexity, complexity_reasoning = self.classify_question_complexity(question)
        model_for_snapshots = self.get_model_for_complexity(base_complexity)
        
        logger.info(
            f"Time-travel complexity classification: {base_complexity.value} -> using {model_for_snapshots}. "
            f"Reasoning: {complexity_reasoning}"
        )
        
        # Step 4: Identify time points
        time_points = self.identify_time_points(question, sensitivity)
        
        # Limit to configured max snapshots
        max_snapshots = self.settings.time_travel_max_snapshots
        if len(time_points) > max_snapshots:
            # Keep first, last, and evenly distributed middle points
            step = len(time_points) // (max_snapshots - 1)
            time_points = [time_points[0]] + [time_points[i * step] for i in range(1, max_snapshots - 1)] + [time_points[-1]]
        
        # Step 5: Generate snapshots with PRESERVED complexity routing
        # CRITICAL: All snapshots use the same model based on original complexity
        snapshots = []
        previous_snapshot = None
        
        # Generate snapshots sequentially to allow comparison
        for date, label in time_points:
            snapshot = await self.generate_snapshot(
                question=question,
                date=date,
                date_label=label,
                previous_snapshot=previous_snapshot,
                model=model_for_snapshots,  # FIXED: Use complexity-based model, NOT hardcoded
                complexity=base_complexity   # Pass complexity for max_tokens adjustment
            )
            snapshots.append(snapshot)
            previous_snapshot = snapshot
            
            logger.debug(f"Generated snapshot for {label}: model={model_for_snapshots}, length={len(snapshot.answer)}")
        
        # Step 6: Validate routing quality
        routing_valid, validation_reason = self.validate_temporal_routing(snapshots)
        if not routing_valid:
            logger.warning(f"Temporal routing validation failed: {validation_reason}")
        
        # Step 7: Check if answers are identical (skip time-travel if so)
        if self._check_answers_identical(snapshots):
            return TimeTravelResult(
                question=question,
                temporal_sensitivity=TemporalSensitivityLevel.LOW,
                sensitivity_reasoning="Despite initial classification, answers are identical across all time periods.",
                is_eligible=False,
                skip_reason="Answers do not change significantly over time. Displaying standard response instead.",
                base_complexity=base_complexity,
                routing_validation_passed=routing_valid
            )
        
        # Step 8: Generate evolution narrative
        narrative, insights, velocity, outlook = await self.generate_evolution_narrative(
            question, snapshots
        )
        
        # Calculate totals
        total_cost = sum(s.cost_estimate for s in snapshots)
        total_time = (datetime.now() - start_time).total_seconds()
        
        result = TimeTravelResult(
            question=question,
            temporal_sensitivity=sensitivity,
            sensitivity_reasoning=sensitivity_reasoning,
            snapshots=snapshots,
            evolution_narrative=narrative,
            insights=insights,
            change_velocity=velocity,
            future_outlook=outlook,
            total_cost=total_cost,
            total_time_seconds=total_time,
            is_eligible=True,
            base_complexity=base_complexity,
            routing_validation_passed=routing_valid
        )
        
        # Cache the result
        self._cache[cache_key] = (result, datetime.now())
        
        logger.info(
            f"Time-travel answer generated: {len(snapshots)} snapshots, "
            f"${total_cost:.4f} cost, {total_time:.1f}s total time, "
            f"complexity={base_complexity.value}, model={model_for_snapshots}, "
            f"routing_valid={routing_valid}"
        )
        
        return result


# Global service instance
time_travel_service = TimeTravelService()
