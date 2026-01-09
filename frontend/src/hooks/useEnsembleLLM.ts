/**
 * Custom hook for managing LLM ensemble queries.
 * Handles state management, API calls, and localStorage history.
 */

import { useState, useCallback, useEffect } from 'react';
import api, {
  EnsembleResponse,
  ModelInfo,
  EnsembleRequest,
} from '@/services/api';

// History item type
export interface HistoryItem {
  id: string;
  question: string;
  timestamp: string;
  models: string[];
  totalCost: number;
  totalTime: number;
  response?: EnsembleResponse;
}

// Hook return type
interface UseEnsembleLLMReturn {
  // State
  isLoading: boolean;
  error: string | null;
  response: EnsembleResponse | null;
  models: ModelInfo[];
  selectedModels: string[];
  history: HistoryItem[];
  
  // Actions
  setSelectedModels: (models: string[]) => void;
  queryModels: (question: string, options?: Partial<EnsembleRequest>) => Promise<void>;
  clearResponse: () => void;
  clearError: () => void;
  loadFromHistory: (item: HistoryItem) => void;
  deleteFromHistory: (id: string) => void;
  clearHistory: () => void;
  refreshModels: () => Promise<void>;
}

// Local storage key
const HISTORY_KEY = 'llm-ensemble-history';
const MAX_HISTORY_ITEMS = 50;

/**
 * Custom hook for LLM ensemble functionality
 */
export function useEnsembleLLM(): UseEnsembleLLMReturn {
  // State
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<EnsembleResponse | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(HISTORY_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setHistory(Array.isArray(parsed) ? parsed : []);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  }, []);

  // Save history to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch (err) {
      console.error('Failed to save history:', err);
    }
  }, [history]);

  // Load models on mount
  useEffect(() => {
    refreshModels();
  }, []);

  // Refresh available models
  const refreshModels = useCallback(async () => {
    try {
      const data = await api.getModels();
      setModels(data.models);
      // Set default selected models if none selected
      if (selectedModels.length === 0) {
        setSelectedModels(data.default_models);
      }
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  }, [selectedModels.length]);

  // Query the ensemble
  const queryModels = useCallback(
    async (question: string, options?: Partial<EnsembleRequest>) => {
      setIsLoading(true);
      setError(null);
      setResponse(null);

      try {
        const result = await api.queryEnsemble({
          question,
          models: selectedModels.length > 0 ? selectedModels : undefined,
          ...options,
        });

        setResponse(result);

        // Add to history
        const historyItem: HistoryItem = {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          question,
          timestamp: new Date().toISOString(),
          models: selectedModels,
          totalCost: result.total_cost,
          totalTime: result.total_time_seconds,
          response: result,
        };

        setHistory((prev) => {
          const newHistory = [historyItem, ...prev];
          // Limit history size
          return newHistory.slice(0, MAX_HISTORY_ITEMS);
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : 'An error occurred';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [selectedModels]
  );

  // Clear current response
  const clearResponse = useCallback(() => {
    setResponse(null);
    setError(null);
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Load a response from history
  const loadFromHistory = useCallback((item: HistoryItem) => {
    if (item.response) {
      setResponse(item.response);
      setError(null);
    }
  }, []);

  // Delete an item from history
  const deleteFromHistory = useCallback((id: string) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
  }, []);

  // Clear all history
  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  return {
    isLoading,
    error,
    response,
    models,
    selectedModels,
    history,
    setSelectedModels,
    queryModels,
    clearResponse,
    clearError,
    loadFromHistory,
    deleteFromHistory,
    clearHistory,
    refreshModels,
  };
}

export default useEnsembleLLM;
