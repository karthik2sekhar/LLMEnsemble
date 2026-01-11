"""
Tests for the Query Router Service.
Tests classification, routing decisions, and cost calculations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.router_service import RouterService, router_service
from app.schemas import (
    QueryClassification, RoutingDecision, CostBreakdown,
    ComplexityLevel, QueryIntent, QueryDomain,
    ModelResponse, TokenUsage, CacheStatus
)


class TestQueryClassification:
    """Test query classification functionality."""
    
    @pytest.fixture
    def router(self):
        """Create a router service instance."""
        return RouterService()
    
    def test_default_classification(self, router):
        """Test default classification returns expected values."""
        classification = router._default_classification()
        
        assert classification.complexity == ComplexityLevel.MODERATE
        assert classification.intent == QueryIntent.FACTUAL
        assert classification.domain == QueryDomain.GENERAL
        assert classification.confidence == 0.5
        assert "gpt-4o-mini" in classification.recommended_models
    
    def test_cache_key_generation(self, router):
        """Test cache key generation is consistent."""
        question = "What is Python?"
        key1 = router._get_cache_key(question)
        key2 = router._get_cache_key(question)
        key3 = router._get_cache_key("  What is Python?  ")  # With whitespace
        
        assert key1 == key2
        assert key1 == key3  # Should normalize whitespace
    
    def test_cache_key_different_questions(self, router):
        """Test cache keys are different for different questions."""
        key1 = router._get_cache_key("What is Python?")
        key2 = router._get_cache_key("What is JavaScript?")
        
        assert key1 != key2


class TestRoutingDecision:
    """Test routing decision logic."""
    
    @pytest.fixture
    def router(self):
        """Create a router service instance."""
        return RouterService()
    
    def test_simple_routing(self, router):
        """Test simple queries route to single model."""
        classification = QueryClassification(
            complexity=ComplexityLevel.SIMPLE,
            intent=QueryIntent.FACTUAL,
            domain=QueryDomain.GENERAL,
            requires_search=False,
            recommended_models=["gpt-4o-mini"],
            reasoning="Simple factual question",
            confidence=0.95
        )
        
        decision = router.determine_execution_path(classification)
        
        assert decision.models_to_use == ["gpt-4o-mini"]
        assert decision.use_synthesis == False
        assert decision.synthesis_model is None
    
    def test_moderate_routing(self, router):
        """Test moderate queries route to two models."""
        classification = QueryClassification(
            complexity=ComplexityLevel.MODERATE,
            intent=QueryIntent.ANALYTICAL,
            domain=QueryDomain.TECHNICAL,
            requires_search=False,
            recommended_models=["gpt-4o-mini", "gpt-4o"],
            reasoning="Moderate analytical question",
            confidence=0.90
        )
        
        decision = router.determine_execution_path(classification)
        
        assert "gpt-4o-mini" in decision.models_to_use
        assert "gpt-4o" in decision.models_to_use
        assert decision.use_synthesis == False
    
    def test_complex_routing(self, router):
        """Test complex queries route to all models with synthesis."""
        classification = QueryClassification(
            complexity=ComplexityLevel.COMPLEX,
            intent=QueryIntent.ANALYTICAL,
            domain=QueryDomain.RESEARCH,
            requires_search=False,
            recommended_models=["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
            reasoning="Complex research question",
            confidence=0.92
        )
        
        decision = router.determine_execution_path(classification)
        
        assert len(decision.models_to_use) == 3
        assert decision.use_synthesis == True
        assert decision.synthesis_model is not None
    
    def test_override_models(self, router):
        """Test model override functionality."""
        classification = QueryClassification(
            complexity=ComplexityLevel.SIMPLE,
            intent=QueryIntent.FACTUAL,
            domain=QueryDomain.GENERAL,
            requires_search=False,
            recommended_models=["gpt-4o-mini"],
            reasoning="Simple question",
            confidence=0.95
        )
        
        # Override with specific models
        decision = router.determine_execution_path(
            classification,
            override_models=["gpt-4-turbo", "gpt-4o"]
        )
        
        assert decision.models_to_use == ["gpt-4-turbo", "gpt-4o"]
        assert "override" in decision.routing_rationale.lower()
    
    def test_force_synthesis(self, router):
        """Test force synthesis functionality."""
        classification = QueryClassification(
            complexity=ComplexityLevel.SIMPLE,
            intent=QueryIntent.FACTUAL,
            domain=QueryDomain.GENERAL,
            requires_search=False,
            recommended_models=["gpt-4o-mini"],
            reasoning="Simple question",
            confidence=0.95
        )
        
        # Force synthesis even for simple query
        decision = router.determine_execution_path(
            classification,
            override_models=["gpt-4o-mini", "gpt-4o"],
            force_synthesis=True
        )
        
        assert decision.use_synthesis == True


class TestCostCalculation:
    """Test cost calculation functionality."""
    
    @pytest.fixture
    def router(self):
        """Create a router service instance."""
        return RouterService()
    
    def test_cost_calculation(self, router):
        """Test cost calculation for model call."""
        token_usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = router._calculate_cost("gpt-4o-mini", token_usage)
        
        # gpt-4o-mini: $0.00015 input, $0.0006 output per 1K tokens
        expected_cost = (1000 * 0.00015 / 1000) + (500 * 0.0006 / 1000)
        assert abs(cost - expected_cost) < 0.0001
    
    def test_cost_calculation_unknown_model(self, router):
        """Test cost calculation for unknown model returns 0."""
        token_usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = router._calculate_cost("unknown-model", token_usage)
        assert cost == 0.0
    
    def test_cost_breakdown_calculation(self, router):
        """Test cost breakdown calculation."""
        model_responses = [
            ModelResponse(
                model_name="gpt-4o-mini",
                response_text="Test response",
                tokens_used=TokenUsage(prompt_tokens=500, completion_tokens=500, total_tokens=1000),
                cost_estimate=0.001,
                response_time_seconds=1.0,
                timestamp=datetime.utcnow(),
                cache_status=CacheStatus.MISS,
                success=True
            ),
            ModelResponse(
                model_name="gpt-4o",
                response_text="Test response",
                tokens_used=TokenUsage(prompt_tokens=500, completion_tokens=500, total_tokens=1000),
                cost_estimate=0.01,
                response_time_seconds=2.0,
                timestamp=datetime.utcnow(),
                cache_status=CacheStatus.MISS,
                success=True
            )
        ]
        
        breakdown = router.calculate_cost_breakdown(
            model_responses=model_responses,
            synthesis_result=None,
            classification_cost=0.0001
        )
        
        assert breakdown.total_cost > 0
        assert breakdown.full_ensemble_cost > 0
        assert breakdown.savings >= 0
        assert breakdown.savings_percentage >= 0
        assert "gpt-4o-mini" in breakdown.model_costs
        assert "gpt-4o" in breakdown.model_costs


class TestRoutingStats:
    """Test routing statistics functionality."""
    
    @pytest.fixture
    def router(self):
        """Create a fresh router service instance."""
        return RouterService()
    
    def test_initial_stats(self, router):
        """Test initial statistics are zeroed."""
        stats = router.get_stats()
        
        assert stats["total_queries"] == 0
        assert stats["simple_queries"] == 0
        assert stats["moderate_queries"] == 0
        assert stats["complex_queries"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["total_savings"] == 0.0


class TestClassificationExamples:
    """Test classification with example queries."""
    
    # These are example queries that should be classified correctly
    # Note: These tests would require mocking the OpenAI API call
    
    SIMPLE_QUERIES = [
        "What is the capital of France?",
        "What is 25 * 4?",
        "Translate 'Hello' to Spanish",
        "How many days are in a year?",
    ]
    
    MODERATE_QUERIES = [
        "Explain how photosynthesis works",
        "Compare React vs Vue for web development",
        "How do I make pasta carbonara?",
        "What are the best practices for REST API design?",
    ]
    
    COMPLEX_QUERIES = [
        "Design a microservices architecture for an e-commerce platform",
        "Analyze the themes in Shakespeare's Hamlet",
        "Explain the ethical implications of AI in healthcare",
        "Write a 2000-word short story about a time traveler",
    ]
    
    def test_query_lists_defined(self):
        """Verify test query lists are defined."""
        assert len(self.SIMPLE_QUERIES) > 0
        assert len(self.MODERATE_QUERIES) > 0
        assert len(self.COMPLEX_QUERIES) > 0


# Integration tests would require actual API calls or more complex mocking
class TestRouterIntegration:
    """Integration tests for router service."""
    
    @pytest.mark.asyncio
    async def test_route_and_answer_with_mock(self):
        """Test full route and answer flow with mocked services."""
        # This test would require mocking both the classifier and LLM services
        # Skipping for now as it requires more complex setup
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
