/**
 * API Service for communicating with the LLM Ensemble backend.
 * Handles all HTTP requests with proper error handling and types.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

// API Base URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  description: string;
  token_limit: number;
  cost_per_1k_input: number;
  cost_per_1k_output: number;
}

export interface ModelResponse {
  model_name: string;
  response_text: string;
  tokens_used: TokenUsage;
  cost_estimate: number;
  response_time_seconds: number;
  timestamp: string;
  cache_status: 'hit' | 'miss';
  error?: string;
  success: boolean;
}

export interface SynthesisResult {
  synthesized_answer: string;
  synthesis_model: string;
  tokens_used: TokenUsage;
  cost_estimate: number;
  response_time_seconds: number;
  timestamp: string;
  model_contributions?: Record<string, string>;
}

export interface EnsembleRequest {
  question: string;
  models?: string[];
  max_tokens?: number;
  temperature?: number;
}

export interface EnsembleResponse {
  question: string;
  model_responses: ModelResponse[];
  synthesis: SynthesisResult | null;
  total_cost: number;
  total_time_seconds: number;
  timestamp: string;
  cached: boolean;
}

export interface ModelsResponse {
  models: ModelInfo[];
  default_models: string[];
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  api_key_configured: boolean;
  cache_enabled: boolean;
}

export interface UsageStats {
  total_queries: number;
  total_cost: number;
  total_tokens: number;
  queries_by_model: Record<string, number>;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  errors: number;
  last_updated: string;
}

export interface ApiError {
  error: string;
  detail?: string;
  timestamp: string;
  retry_after_seconds?: number;
}

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 120000, // 2 minutes to allow for multiple model calls
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response) {
      // Server responded with error status
      const data = error.response.data;
      if (error.response.status === 429) {
        throw new Error(
          `Rate limit exceeded. Please try again in ${data.retry_after_seconds || 60} seconds.`
        );
      }
      throw new Error(data.detail || data.error || 'An error occurred');
    } else if (error.request) {
      // Request made but no response
      throw new Error('Unable to reach the server. Please check your connection.');
    } else {
      // Error setting up request
      throw new Error(error.message || 'An unexpected error occurred');
    }
  }
);

/**
 * API Service object containing all API methods
 */
export const api = {
  /**
   * Check API health status
   */
  async checkHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/api/health');
    return response.data;
  },

  /**
   * Get available models
   */
  async getModels(): Promise<ModelsResponse> {
    const response = await apiClient.get<ModelsResponse>('/api/models');
    return response.data;
  },

  /**
   * Query multiple LLMs and get synthesized response
   */
  async queryEnsemble(request: EnsembleRequest): Promise<EnsembleResponse> {
    const response = await apiClient.post<EnsembleResponse>('/api/ensemble', request);
    return response.data;
  },

  /**
   * Synthesize multiple model responses
   */
  async synthesize(
    question: string,
    modelResponses: ModelResponse[],
    synthesisModel?: string,
    maxTokens?: number
  ): Promise<SynthesisResult> {
    const response = await apiClient.post<SynthesisResult>('/api/synthesize', {
      question,
      model_responses: modelResponses,
      synthesis_model: synthesisModel,
      max_tokens: maxTokens,
    });
    return response.data;
  },

  /**
   * Get usage statistics
   */
  async getStats(): Promise<UsageStats> {
    const response = await apiClient.get<UsageStats>('/api/stats');
    return response.data;
  },
};

export default api;
