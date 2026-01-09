"""
LLM Service for interacting with OpenAI models.
Handles parallel API calls, retries, and error handling.
"""

import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
import openai
from openai import AsyncOpenAI

from ..config import get_settings, ModelConfig
from ..schemas import ModelResponse, TokenUsage, CacheStatus
from ..utils.cache import cache_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for managing LLM API calls."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.settings = get_settings()
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client."""
        if self.settings.validate_api_key():
            self.client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                organization=self.settings.openai_org_id,
                timeout=self.settings.request_timeout,
            )
            logger.info("OpenAI client initialized successfully")
        else:
            logger.warning("OpenAI API key not configured")
    
    async def call_model(
        self,
        model: str,
        question: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        use_cache: bool = True,
    ) -> ModelResponse:
        """
        Call a single LLM model with retry logic.
        
        Args:
            model: The model ID to use
            question: The question to ask
            max_tokens: Maximum tokens for the response
            temperature: Temperature for generation
            use_cache: Whether to use caching
            
        Returns:
            ModelResponse object with the result
        """
        start_time = time.time()
        timestamp = datetime.utcnow()
        
        # Check cache first
        if use_cache and self.settings.cache_enabled:
            cache_key = cache_manager.generate_key(model, question, max_tokens, temperature)
            cached_response = cache_manager.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for model {model}")
                # Update timestamp and cache status for cached response
                cached_response.timestamp = timestamp
                cached_response.cache_status = CacheStatus.HIT
                cached_response.response_time_seconds = time.time() - start_time
                return cached_response
        
        # Make API call with retries
        last_error = None
        for attempt in range(self.settings.max_retries):
            try:
                if not self.client:
                    raise ValueError("OpenAI client not initialized. Check API key configuration.")
                
                logger.info(f"Calling model {model} (attempt {attempt + 1}/{self.settings.max_retries})")
                
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful, accurate, and thorough assistant. Provide clear, well-structured responses."
                            },
                            {
                                "role": "user",
                                "content": question
                            }
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    ),
                    timeout=self.settings.request_timeout
                )
                
                # Extract response data
                response_text = response.choices[0].message.content or ""
                usage = response.usage
                
                token_usage = TokenUsage(
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                )
                
                cost = ModelConfig.get_cost(
                    model,
                    token_usage.prompt_tokens,
                    token_usage.completion_tokens
                )
                
                response_time = time.time() - start_time
                
                model_response = ModelResponse(
                    model_name=model,
                    response_text=response_text,
                    tokens_used=token_usage,
                    cost_estimate=round(cost, 6),
                    response_time_seconds=round(response_time, 3),
                    timestamp=timestamp,
                    cache_status=CacheStatus.MISS,
                    success=True,
                )
                
                # Store in cache
                if use_cache and self.settings.cache_enabled:
                    cache_manager.set(cache_key, model_response)
                
                logger.info(f"Model {model} responded in {response_time:.2f}s with {token_usage.total_tokens} tokens")
                return model_response
                
            except asyncio.TimeoutError:
                last_error = f"Request timed out after {self.settings.request_timeout} seconds"
                logger.warning(f"Model {model} timeout on attempt {attempt + 1}")
                
            except openai.RateLimitError as e:
                last_error = f"Rate limit exceeded: {str(e)}"
                logger.warning(f"Rate limit hit for model {model}")
                # Wait before retry on rate limit
                await asyncio.sleep(2 ** attempt)
                
            except openai.APIError as e:
                last_error = f"API error: {str(e)}"
                logger.error(f"API error for model {model}: {e}")
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error calling model {model}: {e}")
            
            # Wait before retry
            if attempt < self.settings.max_retries - 1:
                await asyncio.sleep(1)
        
        # All retries failed
        response_time = time.time() - start_time
        return ModelResponse(
            model_name=model,
            response_text="",
            tokens_used=TokenUsage(),
            cost_estimate=0.0,
            response_time_seconds=round(response_time, 3),
            timestamp=timestamp,
            cache_status=CacheStatus.MISS,
            error=last_error,
            success=False,
        )
    
    async def call_models_parallel(
        self,
        models: List[str],
        question: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        use_cache: bool = True,
    ) -> List[ModelResponse]:
        """
        Call multiple models in parallel.
        
        Args:
            models: List of model IDs to call
            question: The question to ask all models
            max_tokens: Maximum tokens per response
            temperature: Temperature for generation
            use_cache: Whether to use caching
            
        Returns:
            List of ModelResponse objects
        """
        logger.info(f"Calling {len(models)} models in parallel: {models}")
        
        # Create tasks for parallel execution
        tasks = [
            self.call_model(model, question, max_tokens, temperature, use_cache)
            for model in models
        ]
        
        # Execute all tasks concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                # Convert exception to error response
                results.append(ModelResponse(
                    model_name=models[i],
                    response_text="",
                    tokens_used=TokenUsage(),
                    cost_estimate=0.0,
                    response_time_seconds=0.0,
                    timestamp=datetime.utcnow(),
                    cache_status=CacheStatus.MISS,
                    error=str(response),
                    success=False,
                ))
            else:
                results.append(response)
        
        successful = sum(1 for r in results if r.success)
        logger.info(f"Parallel calls complete: {successful}/{len(models)} successful")
        
        return results
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        return ModelConfig.get_available_models()


# Global LLM service instance
llm_service = LLMService()
