"""
Unit tests for the LLM Ensemble backend.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.config import Settings, ModelConfig, get_settings
from app.schemas import (
    EnsembleRequest,
    ModelResponse,
    TokenUsage,
    CacheStatus,
)
from app.utils.cache import CacheManager, RateLimiter
from app.services.llm_service import LLMService
from app.services.synthesis_service import SynthesisService


class TestModelConfig:
    """Tests for ModelConfig class."""
    
    def test_get_cost_known_model(self):
        """Test cost calculation for known models."""
        cost = ModelConfig.get_cost("gpt-4o-mini", input_tokens=1000, output_tokens=500)
        expected = (1000 * 0.00015 / 1000) + (500 * 0.0006 / 1000)
        assert cost == expected
    
    def test_get_cost_unknown_model(self):
        """Test cost calculation for unknown models returns 0."""
        cost = ModelConfig.get_cost("unknown-model", input_tokens=1000, output_tokens=500)
        assert cost == 0.0
    
    def test_get_available_models(self):
        """Test getting available models list."""
        models = ModelConfig.get_available_models()
        assert len(models) == 3
        model_ids = [m["id"] for m in models]
        assert "gpt-4-turbo" in model_ids
        assert "gpt-4o" in model_ids
        assert "gpt-4o-mini" in model_ids


class TestSettings:
    """Tests for Settings configuration."""
    
    def test_default_settings(self):
        """Test default settings values."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings()
            assert settings.port == 8000
            assert settings.debug == False
            assert settings.cache_enabled == True
            assert settings.max_question_length == 5000
    
    def test_cors_origins_list(self):
        """Test CORS origins parsing."""
        with patch.dict("os.environ", {"CORS_ORIGINS": "http://a.com,http://b.com"}):
            settings = Settings()
            origins = settings.cors_origins_list
            assert len(origins) == 2
            assert "http://a.com" in origins
    
    def test_validate_api_key_empty(self):
        """Test API key validation with empty key."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            settings = Settings()
            assert settings.validate_api_key() == False
    
    def test_validate_api_key_present(self):
        """Test API key validation with valid key."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            settings = Settings()
            assert settings.validate_api_key() == True


class TestEnsembleRequest:
    """Tests for EnsembleRequest validation."""
    
    def test_valid_request(self):
        """Test valid request creation."""
        request = EnsembleRequest(question="What is AI?")
        assert request.question == "What is AI?"
        assert request.models is None
        assert request.max_tokens == 2000
    
    def test_question_whitespace_stripped(self):
        """Test that question whitespace is stripped."""
        request = EnsembleRequest(question="  What is AI?  ")
        assert request.question == "What is AI?"
    
    def test_empty_question_rejected(self):
        """Test that empty questions are rejected."""
        with pytest.raises(ValueError):
            EnsembleRequest(question="")
    
    def test_whitespace_only_question_rejected(self):
        """Test that whitespace-only questions are rejected."""
        with pytest.raises(ValueError):
            EnsembleRequest(question="   ")
    
    def test_question_max_length(self):
        """Test question max length validation."""
        with pytest.raises(ValueError):
            EnsembleRequest(question="a" * 5001)


class TestCacheManager:
    """Tests for CacheManager."""
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = CacheManager(default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_get_missing_key(self):
        """Test getting a missing key returns None."""
        cache = CacheManager()
        assert cache.get("nonexistent") is None
    
    def test_expired_entry(self):
        """Test that expired entries return None."""
        cache = CacheManager(default_ttl=0)  # Immediate expiry
        cache.set("key1", "value1")
        # Entry expires immediately
        import time
        time.sleep(0.01)
        assert cache.get("key1") is None
    
    def test_generate_key(self):
        """Test cache key generation."""
        cache = CacheManager()
        key1 = cache.generate_key("model1", "question1", 100)
        key2 = cache.generate_key("model1", "question1", 100)
        key3 = cache.generate_key("model1", "question2", 100)
        
        assert key1 == key2  # Same inputs = same key
        assert key1 != key3  # Different inputs = different key
    
    def test_delete(self):
        """Test deleting a cache entry."""
        cache = CacheManager()
        cache.set("key1", "value1")
        assert cache.delete("key1") == True
        assert cache.get("key1") is None
        assert cache.delete("key1") == False  # Already deleted
    
    def test_clear(self):
        """Test clearing the cache."""
        cache = CacheManager()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_allows_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed("client1") == True
    
    def test_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("client1") == True
        assert limiter.is_allowed("client1") == True
        assert limiter.is_allowed("client1") == False
    
    def test_separate_clients(self):
        """Test that different clients have separate limits."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("client1") == True
        assert limiter.is_allowed("client2") == True
        assert limiter.is_allowed("client1") == False
    
    def test_get_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.get_remaining("client1") == 5
        limiter.is_allowed("client1")
        assert limiter.get_remaining("client1") == 4
    
    def test_reset(self):
        """Test resetting a client's rate limit."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.is_allowed("client1")
        assert limiter.is_allowed("client1") == False
        limiter.reset("client1")
        assert limiter.is_allowed("client1") == True


class TestModelResponse:
    """Tests for ModelResponse schema."""
    
    def test_create_success_response(self):
        """Test creating a successful model response."""
        response = ModelResponse(
            model_name="gpt-4o",
            response_text="Test response",
            tokens_used=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            cost_estimate=0.001,
            response_time_seconds=1.5,
            timestamp=datetime.utcnow(),
            cache_status=CacheStatus.MISS,
            success=True,
        )
        assert response.model_name == "gpt-4o"
        assert response.success == True
        assert response.error is None
    
    def test_create_error_response(self):
        """Test creating an error model response."""
        response = ModelResponse(
            model_name="gpt-4o",
            response_text="",
            tokens_used=TokenUsage(),
            cost_estimate=0.0,
            response_time_seconds=0.5,
            timestamp=datetime.utcnow(),
            cache_status=CacheStatus.MISS,
            success=False,
            error="API timeout",
        )
        assert response.success == False
        assert response.error == "API timeout"


# Async tests
@pytest.mark.asyncio
class TestLLMServiceAsync:
    """Async tests for LLM Service."""
    
    async def test_call_model_without_client(self):
        """Test calling model when client is not initialized."""
        service = LLMService()
        service.client = None  # Simulate no API key
        
        response = await service.call_model("gpt-4o", "Test question")
        
        assert response.success == False
        assert "not initialized" in response.error.lower()
    
    @patch("app.services.llm_service.AsyncOpenAI")
    async def test_call_models_parallel(self, mock_openai):
        """Test parallel model calls."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        service = LLMService()
        service.client = mock_client
        
        responses = await service.call_models_parallel(
            models=["gpt-4o", "gpt-4o-mini"],
            question="Test question",
            use_cache=False,
        )
        
        assert len(responses) == 2


# Run tests with: pytest tests/test_main.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
