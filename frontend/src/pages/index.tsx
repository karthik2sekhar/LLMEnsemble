/**
 * LLM Ensemble - Main Application Page
 * 
 * A web application that queries multiple LLM models in parallel
 * and synthesizes their responses into a unified answer.
 * Now with intelligent query routing for cost optimization.
 */

import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { Zap, Info, AlertCircle, DollarSign, Clock, BarChart3, Settings } from 'lucide-react';
import clsx from 'clsx';

import {
  QuestionInput,
  ModelSelector,
  ResponseCard,
  SynthesisResult,
  LoadingState,
  HistoryPanel,
  ThemeToggle,
  RouteModeToggle,
  SmartRouteResult,
} from '@/components';
import type { RouteMode } from '@/components';
import { useEnsembleLLM } from '@/hooks/useEnsembleLLM';
import api, { HealthResponse, RouteAndAnswerResponse, RoutingStats } from '@/services/api';

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
  
  // Routing state
  const [routeMode, setRouteMode] = useState<RouteMode>('smart');
  const [smartRouteResponse, setSmartRouteResponse] = useState<RouteAndAnswerResponse | null>(null);
  const [routingStats, setRoutingStats] = useState<RoutingStats | null>(null);
  const [isSmartLoading, setIsSmartLoading] = useState(false);
  const [smartError, setSmartError] = useState<string | null>(null);

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
    
    // Load routing stats
    const loadRoutingStats = async () => {
      try {
        const stats = await api.getRoutingStats();
        setRoutingStats(stats);
      } catch (err) {
        // Stats not critical, ignore errors
      }
    };
    loadRoutingStats();
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

  // Show success toast when smart route response is received
  useEffect(() => {
    if (smartRouteResponse) {
      const savings = smartRouteResponse.cost_breakdown.savings_percentage;
      toast.success(
        `Smart route: ${smartRouteResponse.models_used.length} model(s), saved ${savings.toFixed(1)}%`
      );
      // Refresh routing stats
      api.getRoutingStats().then(setRoutingStats).catch(() => {});
    }
  }, [smartRouteResponse]);

  // Handle question submission
  const handleSubmit = async (question: string) => {
    if (routeMode === 'smart') {
      await handleSmartRoute(question);
    } else {
      await queryModels(question);
    }
  };

  // Handle smart route query
  const handleSmartRoute = async (question: string) => {
    setIsSmartLoading(true);
    setSmartError(null);
    setSmartRouteResponse(null);
    
    try {
      const result = await api.routeAndAnswer({
        question,
        max_tokens: 2000,
        temperature: 0.7,
      });
      setSmartRouteResponse(result);
    } catch (err: any) {
      const errorMessage = err.message || 'Smart routing failed';
      setSmartError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsSmartLoading(false);
    }
  };

  // Clear smart route response
  const clearSmartResponse = () => {
    setSmartRouteResponse(null);
    setSmartError(null);
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
  
  // Determine current loading state
  const currentLoading = routeMode === 'smart' ? isSmartLoading : isLoading;
  const currentError = routeMode === 'smart' ? smartError : error;
  const hasResponse = routeMode === 'smart' ? !!smartRouteResponse : !!response;

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
        {/* Route Mode Toggle */}
        <section className="mb-6">
          <RouteModeToggle
            mode={routeMode}
            onModeChange={(mode) => {
              setRouteMode(mode);
              // Clear responses when switching modes
              if (mode === 'smart') {
                clearResponse();
              } else {
                clearSmartResponse();
              }
            }}
            disabled={currentLoading}
          />
        </section>

        {/* Question input section */}
        <section className="mb-8">
          <QuestionInput onSubmit={handleSubmit} isLoading={currentLoading} />
        </section>

        {/* Model selector - only show in ensemble mode */}
        {routeMode === 'ensemble' && (
          <section className="mb-8">
            <ModelSelector
              models={models}
              selectedModels={selectedModels}
              onSelectionChange={setSelectedModels}
              disabled={currentLoading}
            />
          </section>
        )}

        {/* Smart route info for first-time users */}
        {routeMode === 'smart' && !smartRouteResponse && !isSmartLoading && (
          <div className="mb-8 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl">
            <div className="flex items-start gap-3">
              <Zap className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-green-900 dark:text-green-100">
                  Smart Route Mode
                </h3>
                <p className="mt-1 text-sm text-green-700 dark:text-green-300">
                  Your question will be automatically classified and routed to the optimal 
                  model(s) based on complexity, intent, and domain. Simple questions use 
                  fewer models to save costs, while complex questions use all models with synthesis.
                </p>
                {routingStats && routingStats.total_queries > 0 && (
                  <p className="mt-2 text-xs text-green-600 dark:text-green-400">
                    Session stats: {routingStats.total_queries} queries, 
                    ${routingStats.total_savings.toFixed(4)} saved ({routingStats.average_savings_percentage.toFixed(1)}% avg)
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Info banner for ensemble mode first-time users */}
        {routeMode === 'ensemble' && !response && !isLoading && history.length === 0 && (
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
        {currentLoading && (
          <LoadingState 
            models={routeMode === 'smart' ? ['Classifying query...'] : selectedModels} 
          />
        )}

        {/* Smart Route Results */}
        {routeMode === 'smart' && smartRouteResponse && !isSmartLoading && (
          <div className="space-y-8 animate-fade-in">
            <SmartRouteResult result={smartRouteResponse} />
            
            {/* Clear button */}
            <div className="text-center">
              <button
                onClick={clearSmartResponse}
                className="px-6 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                Clear results and ask another question
              </button>
            </div>
          </div>
        )}

        {/* Ensemble Results section */}
        {routeMode === 'ensemble' && response && !isLoading && (
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
        {currentError && !currentLoading && !hasResponse && (
          <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-red-900 dark:text-red-100">
                  Something went wrong
                </h3>
                <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                  {currentError}
                </p>
                <button
                  onClick={() => routeMode === 'smart' ? clearSmartResponse() : clearResponse()}
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
            LLM Ensemble v1.1.0 • Intelligent Query Routing • Query multiple AI models simultaneously
          </p>
        </div>
      </footer>
    </div>
  );
}
