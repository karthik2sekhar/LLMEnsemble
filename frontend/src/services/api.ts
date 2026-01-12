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

// ==================== Query Router Types ====================

export type ComplexityLevel = 'simple' | 'moderate' | 'complex';
export type QueryIntent = 'factual' | 'creative' | 'analytical' | 'procedural' | 'comparative';
export type QueryDomain = 'coding' | 'technical' | 'general' | 'creative' | 'research';
export type TemporalScope = 'evergreen' | 'historical' | 'current' | 'future';

export interface TemporalDetectionResult {
  is_temporal: boolean;
  temporal_scope: TemporalScope;
  requires_current_data: boolean;
  detected_keywords: string[];
  detected_years: number[];
  confidence: number;
  reasoning: string;
}

export interface QueryClassification {
  complexity: ComplexityLevel;
  intent: QueryIntent;
  domain: QueryDomain;
  requires_search: boolean;
  recommended_models: string[];
  reasoning: string;
  confidence: number;
  temporal_scope?: TemporalScope;
}

export interface RoutingDecision {
  models_to_use: string[];
  use_synthesis: boolean;
  synthesis_model: string | null;
  estimated_cost: number;
  estimated_time_seconds: number;
  routing_rationale: string;
  minimum_models_for_temporal?: number;
  add_web_search_recommendation?: boolean;
}

export interface CostBreakdown {
  model_costs: Record<string, number>;
  synthesis_cost: number;
  classification_cost: number;
  total_cost: number;
  full_ensemble_cost: number;
  savings: number;
  savings_percentage: number;
  search_cost?: number;
}

export interface ExecutionMetrics {
  classification_time_ms: number;
  model_execution_time_ms: Record<string, number>;
  synthesis_time_ms: number;
  total_time_ms: number;
  temporal_detection_time_ms?: number;
  search_time_ms?: number;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source?: string;
}

export interface SearchResults {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_provider: string;
}

export interface RouteAndAnswerRequest {
  question: string;
  max_tokens?: number;
  temperature?: number;
  override_models?: string[];
  force_synthesis?: boolean;
  enable_search?: boolean;
}

export interface RouteAndAnswerResponse {
  question: string;
  classification: QueryClassification;
  routing_decision: RoutingDecision;
  models_used: string[];
  individual_responses: ModelResponse[];
  final_answer: string;
  synthesis: SynthesisResult | null;
  cost_breakdown: CostBreakdown;
  execution_metrics: ExecutionMetrics;
  timestamp: string;
  fallback_used: boolean;
  fallback_reason: string | null;
  // Temporal/Search fields
  temporal_detection?: TemporalDetectionResult;
  was_search_used?: boolean;
  search_results?: SearchResults;
  routing_override_applied?: boolean;
  routing_override_reason?: string;
  ui_warning_message?: string;
}

// ==================== Time-Travel Types ====================

export type TemporalSensitivityLevel = 'high' | 'medium' | 'low' | 'none';

export interface TimeSnapshot {
  date: string;
  date_label: string;
  answer: string;
  key_changes: string[];
  data_points: string[];
  model_used: string;
  tokens_used: number;
  cost_estimate: number;
  response_time_seconds: number;
}

export interface TimeTravelRequest {
  question: string;
  force_time_travel?: boolean;
  max_snapshots?: number;
}

export interface TimeTravelResponse {
  question: string;
  temporal_sensitivity: TemporalSensitivityLevel;
  sensitivity_reasoning: string;
  is_eligible: boolean;
  skip_reason?: string;
  snapshots: TimeSnapshot[];
  evolution_narrative: string;
  insights: string[];
  change_velocity: string;
  future_outlook: string;
  total_cost: number;
  total_time_seconds: number;
  timestamp: string;
}

export interface TemporalSensitivityCheck {
  question: string;
  temporal_sensitivity: TemporalSensitivityLevel;
  reasoning: string;
  suggested_time_points: Array<{
    date: string;
    label: string;
  }>;
  time_travel_eligible: boolean;
  timestamp: string;
}

export interface RoutingStats {
  total_queries: number;
  simple_queries: number;
  moderate_queries: number;
  complex_queries: number;
  total_cost: number;
  total_savings: number;
  average_savings_percentage: number;
  model_usage_distribution: Record<string, number>;
  fallback_count: number;
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

  // ==================== Intelligent Router Methods ====================

  /**
   * Query with intelligent routing - classifies query and routes to optimal models
   */
  async routeAndAnswer(request: RouteAndAnswerRequest): Promise<RouteAndAnswerResponse> {
    const response = await apiClient.post<RouteAndAnswerResponse>('/api/route-and-answer', request);
    return response.data;
  },

  /**
   * Get routing statistics
   */
  async getRoutingStats(): Promise<RoutingStats> {
    const response = await apiClient.get<RoutingStats>('/api/routing-stats');
    return response.data;
  },

  /**
   * Clear classification cache
   */
  async clearClassificationCache(): Promise<{ message: string; timestamp: string }> {
    const response = await apiClient.post<{ message: string; timestamp: string }>('/api/clear-classification-cache');
    return response.data;
  },

  // ==================== Time-Travel Methods ====================

  /**
   * Generate time-travel answer showing how response evolved over time
   */
  async getTimeTravelAnswer(request: TimeTravelRequest): Promise<TimeTravelResponse> {
    const response = await apiClient.post<TimeTravelResponse>('/api/time-travel', request);
    return response.data;
  },

  /**
   * Check temporal sensitivity of a question without generating full time-travel
   */
  async checkTemporalSensitivity(question: string): Promise<TemporalSensitivityCheck> {
    const response = await apiClient.post<TemporalSensitivityCheck>(
      '/api/check-temporal-sensitivity',
      null,
      { params: { question } }
    );
    return response.data;
  },
};

export default api;
