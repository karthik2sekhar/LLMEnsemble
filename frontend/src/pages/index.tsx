/**
 * LLM Ensemble - Main Application Page
 * 
 * A web application that queries multiple LLM models in parallel
 * and synthesizes their responses into a unified answer.
 */

import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { Zap, Info, AlertCircle, DollarSign, Clock, BarChart3 } from 'lucide-react';
import clsx from 'clsx';

import {
  QuestionInput,
  ModelSelector,
  ResponseCard,
  SynthesisResult,
  LoadingState,
  HistoryPanel,
  ThemeToggle,
} from '@/components';
import { useEnsembleLLM } from '@/hooks/useEnsembleLLM';
import api, { HealthResponse } from '@/services/api';

export default function Home() {
  // Use the custom hook for ensemble functionality
  const {
    isLoading,
    error,
    response,
    models,
    selectedModels,
    history,
    setSelectedModels,
    queryModels,
    clearResponse,
    loadFromHistory,
    deleteFromHistory,
    clearHistory,
  } = useEnsembleLLM();

  // Local state
  const [healthStatus, setHealthStatus] = useState<HealthResponse | null>(null);
  const [showStats, setShowStats] = useState(false);

  // Check API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await api.checkHealth();
        setHealthStatus(health);
        if (!health.api_key_configured) {
          toast.error('OpenAI API key not configured on server');
        }
      } catch (err) {
        toast.error('Unable to connect to backend server');
      }
    };
    checkHealth();
  }, []);

  // Show error toast when error state changes
  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error]);

  // Show success toast when response is received
  useEffect(() => {
    if (response) {
      toast.success(
        `Received responses from ${response.model_responses.filter(r => r.success).length} models`
      );
    }
  }, [response]);

  // Handle question submission
  const handleSubmit = async (question: string) => {
    await queryModels(question);
  };

  // Calculate summary stats
  const getSummaryStats = () => {
    if (!response) return null;
    
    const successCount = response.model_responses.filter(r => r.success).length;
    const totalTokens = response.model_responses.reduce(
      (sum, r) => sum + r.tokens_used.total_tokens,
      0
    ) + (response.synthesis?.tokens_used.total_tokens || 0);
    
    return {
      successCount,
      totalCount: response.model_responses.length,
      totalTokens,
      totalCost: response.total_cost,
      totalTime: response.total_time_seconds,
      cached: response.cached,
    };
  };

  const stats = getSummaryStats();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-xl">
                <Zap className="w-6 h-6 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  LLM Ensemble
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
                  Multi-model AI responses
                </p>
              </div>
            </div>

            {/* Right side controls */}
            <div className="flex items-center gap-4">
              {/* Health indicator */}
              {healthStatus && (
                <div
                  className={clsx(
                    'hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs',
                    healthStatus.api_key_configured
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                      : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                  )}
                >
                  <span
                    className={clsx(
                      'w-2 h-2 rounded-full',
                      healthStatus.api_key_configured ? 'bg-green-500' : 'bg-red-500'
                    )}
                  />
                  {healthStatus.api_key_configured ? 'Connected' : 'API Key Missing'}
                </div>
              )}
              
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Question input section */}
        <section className="mb-8">
          <QuestionInput onSubmit={handleSubmit} isLoading={isLoading} />
        </section>

        {/* Model selector */}
        <section className="mb-8">
          <ModelSelector
            models={models}
            selectedModels={selectedModels}
            onSelectionChange={setSelectedModels}
            disabled={isLoading}
          />
        </section>

        {/* Info banner for first-time users */}
        {!response && !isLoading && history.length === 0 && (
          <div className="mb-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-900 dark:text-blue-100">
                  How it works
                </h3>
                <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                  Enter a question above and select which AI models you want to use. 
                  The system will query all selected models in parallel and synthesize 
                  their responses into a unified, comprehensive answer.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Loading state */}
        {isLoading && <LoadingState models={selectedModels} />}

        {/* Results section */}
        {response && !isLoading && (
          <div className="space-y-8 animate-fade-in">
            {/* Summary stats */}
            {stats && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                    <BarChart3 className="w-4 h-4" />
                    <span className="text-xs uppercase tracking-wider">Models</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.successCount}/{stats.totalCount}
                  </p>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                    <Clock className="w-4 h-4" />
                    <span className="text-xs uppercase tracking-wider">Time</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.totalTime.toFixed(1)}s
                  </p>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                    <span className="text-xs">#</span>
                    <span className="text-xs uppercase tracking-wider">Tokens</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stats.totalTokens.toLocaleString()}
                  </p>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                    <DollarSign className="w-4 h-4" />
                    <span className="text-xs uppercase tracking-wider">Cost</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    ${stats.totalCost.toFixed(4)}
                  </p>
                </div>
              </div>
            )}

            {/* Synthesized answer */}
            {response.synthesis && (
              <SynthesisResult
                synthesis={response.synthesis}
                question={response.question}
              />
            )}

            {/* Individual model responses */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Individual Model Responses
              </h3>
              <div className="space-y-4">
                {response.model_responses.map((modelResponse, index) => (
                  <ResponseCard
                    key={modelResponse.model_name}
                    response={modelResponse}
                    index={index}
                    defaultExpanded={index === 0}
                  />
                ))}
              </div>
            </div>

            {/* Clear button */}
            <div className="text-center">
              <button
                onClick={clearResponse}
                className="px-6 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                Clear results and ask another question
              </button>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && !response && (
          <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-red-900 dark:text-red-100">
                  Something went wrong
                </h3>
                <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                  {error}
                </p>
                <button
                  onClick={clearResponse}
                  className="mt-3 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* History panel */}
      <HistoryPanel
        history={history}
        onSelect={loadFromHistory}
        onDelete={deleteFromHistory}
        onClear={clearHistory}
      />

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 py-6 mt-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            LLM Ensemble v1.0.0 • Query multiple AI models simultaneously
          </p>
        </div>
      </footer>
    </div>
  );
}
