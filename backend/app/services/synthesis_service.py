"""
Synthesis Service for combining multiple LLM responses.
Uses an LLM to analyze and synthesize responses from multiple models.
"""

import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict
import openai
from openai import AsyncOpenAI

from ..config import get_settings, ModelConfig
from ..schemas import ModelResponse, SynthesisResult, TokenUsage
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SynthesisService:
    """Service for synthesizing multiple LLM responses."""
    
    # Synthesis prompt template
    SYNTHESIS_PROMPT = """You are a synthesis expert. I asked a question and received responses from different AI models. 
Each response offers a unique perspective based on the model's strengths.

**Question:** {question}

**Model Responses:**
{model_responses}

---

Please synthesize these responses into a single, coherent, and accurate answer that:

1. **Extracts the most valuable insights** from each model
2. **Identifies and resolves any contradictions** between responses
3. **Presents information in a clear, logical order**
4. **Highlights areas where models agreed** (indicating higher confidence)
5. **Notes any unique perspectives** that add value

## Guidelines:
- Format your answer in markdown with clear sections
- Keep the response concise but comprehensive (max 500 words)
- Use bullet points or numbered lists where appropriate
- If models disagreed on something, explain the different perspectives
- End with a brief "Model Contributions" section noting what each model uniquely contributed

Provide your synthesized answer:"""

    def __init__(self):
        """Initialize the synthesis service."""
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
            logger.info("Synthesis service client initialized")
        else:
            logger.warning("Synthesis service: API key not configured")
    
    def _format_model_responses(self, responses: List[ModelResponse]) -> str:
        """Format model responses for the synthesis prompt."""
        formatted_parts = []
        
        for i, response in enumerate(responses, 1):
            if response.success and response.response_text:
                formatted_parts.append(
                    f"### Model {i}: {response.model_name}\n"
                    f"*Response time: {response.response_time_seconds:.2f}s | "
                    f"Tokens: {response.tokens_used.total_tokens}*\n\n"
                    f"{response.response_text}\n"
                )
        
        return "\n---\n\n".join(formatted_parts)
    
    def _extract_model_contributions(
        self,
        responses: List[ModelResponse],
        synthesis_text: str
    ) -> Dict[str, str]:
        """Extract a summary of each model's contribution."""
        contributions = {}
        
        for response in responses:
            if response.success:
                # Generate a brief contribution note
                word_count = len(response.response_text.split())
                contributions[response.model_name] = (
                    f"Provided {word_count} words in {response.response_time_seconds:.2f}s"
                )
        
        return contributions
    
    async def synthesize(
        self,
        question: str,
        model_responses: List[ModelResponse],
        synthesis_model: Optional[str] = None,
        max_tokens: int = 1500,
    ) -> SynthesisResult:
        """
        Synthesize multiple model responses into a single coherent answer.
        
        Args:
            question: The original question
            model_responses: List of responses from different models
            synthesis_model: Model to use for synthesis
            max_tokens: Maximum tokens for synthesis response
            
        Returns:
            SynthesisResult with the synthesized answer
        """
        start_time = time.time()
        timestamp = datetime.utcnow()
        
        # Use configured synthesis model if not specified
        if not synthesis_model:
            synthesis_model = self.settings.synthesis_model
        
        # Filter to only successful responses
        successful_responses = [r for r in model_responses if r.success and r.response_text]
        
        if not successful_responses:
            logger.warning("No successful responses to synthesize")
            return SynthesisResult(
                synthesized_answer="Unable to synthesize: No successful model responses available.",
                synthesis_model=synthesis_model,
                tokens_used=TokenUsage(),
                cost_estimate=0.0,
                response_time_seconds=0.0,
                timestamp=timestamp,
            )
        
        # If only one response, return it directly with a note
        if len(successful_responses) == 1:
            response = successful_responses[0]
            return SynthesisResult(
                synthesized_answer=(
                    f"*Note: Only one model ({response.model_name}) provided a successful response.*\n\n"
                    f"{response.response_text}"
                ),
                synthesis_model=response.model_name,
                tokens_used=response.tokens_used,
                cost_estimate=response.cost_estimate,
                response_time_seconds=time.time() - start_time,
                timestamp=timestamp,
                model_contributions={response.model_name: "Sole contributor"},
            )
        
        # Format responses for the prompt
        formatted_responses = self._format_model_responses(successful_responses)
        
        # Build the synthesis prompt
        synthesis_prompt = self.SYNTHESIS_PROMPT.format(
            question=question,
            model_responses=formatted_responses
        )
        
        try:
            if not self.client:
                raise ValueError("OpenAI client not initialized. Check API key configuration.")
            
            logger.info(f"Synthesizing {len(successful_responses)} responses using {synthesis_model}")
            
            # Use max_completion_tokens for gpt-5.x models, max_tokens for others
            completion_params = {
                "model": synthesis_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert at synthesizing information from multiple sources. "
                            "Your goal is to create a comprehensive, accurate, and well-organized "
                            "summary that captures the best insights from all sources."
                        )
                    },
                    {
                        "role": "user",
                        "content": synthesis_prompt
                    }
                ],
                "temperature": 0.5,  # Lower temperature for more focused synthesis
            }
            
            if synthesis_model.startswith("gpt-5"):
                completion_params["max_completion_tokens"] = max_tokens
            else:
                completion_params["max_tokens"] = max_tokens
            
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**completion_params),
                timeout=self.settings.request_timeout
            )
            
            # Extract response data
            synthesis_text = response.choices[0].message.content or ""
            usage = response.usage
            
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )
            
            cost = ModelConfig.get_cost(
                synthesis_model,
                token_usage.prompt_tokens,
                token_usage.completion_tokens
            )
            
            response_time = time.time() - start_time
            
            # Extract model contributions
            contributions = self._extract_model_contributions(successful_responses, synthesis_text)
            
            logger.info(f"Synthesis complete in {response_time:.2f}s with {token_usage.total_tokens} tokens")
            
            return SynthesisResult(
                synthesized_answer=synthesis_text,
                synthesis_model=synthesis_model,
                tokens_used=token_usage,
                cost_estimate=round(cost, 6),
                response_time_seconds=round(response_time, 3),
                timestamp=timestamp,
                model_contributions=contributions,
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Synthesis timed out after {self.settings.request_timeout}s")
            return SynthesisResult(
                synthesized_answer="Synthesis failed: Request timed out. Please try again.",
                synthesis_model=synthesis_model,
                tokens_used=TokenUsage(),
                cost_estimate=0.0,
                response_time_seconds=time.time() - start_time,
                timestamp=timestamp,
            )
            
        except openai.APIError as e:
            logger.error(f"Synthesis API error: {e}")
            return SynthesisResult(
                synthesized_answer=f"Synthesis failed: API error - {str(e)}",
                synthesis_model=synthesis_model,
                tokens_used=TokenUsage(),
                cost_estimate=0.0,
                response_time_seconds=time.time() - start_time,
                timestamp=timestamp,
            )
            
        except Exception as e:
            logger.error(f"Synthesis unexpected error: {e}")
            return SynthesisResult(
                synthesized_answer=f"Synthesis failed: {str(e)}",
                synthesis_model=synthesis_model,
                tokens_used=TokenUsage(),
                cost_estimate=0.0,
                response_time_seconds=time.time() - start_time,
                timestamp=timestamp,
            )


# Global synthesis service instance
synthesis_service = SynthesisService()
