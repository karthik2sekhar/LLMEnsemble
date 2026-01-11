/**
 * Smart Route Result Component
 * Displays the result from intelligent routing with classification and cost info
 * Now includes temporal awareness warnings and search results display
 */

import React from 'react';
import { RouteAndAnswerResponse, ModelResponse } from '../services/api';
import { RoutingInfoPanel } from './RoutingInfoPanel';
import { CostVisualization } from './CostVisualization';
import { TemporalWarning } from './TemporalWarning';
import { SearchResults } from './SearchResults';
import ReactMarkdown from 'react-markdown';

interface SmartRouteResultProps {
  result: RouteAndAnswerResponse;
  showIndividualResponses?: boolean;
}

export const SmartRouteResult: React.FC<SmartRouteResultProps> = ({
  result,
  showIndividualResponses = false,
}) => {
  const [showResponses, setShowResponses] = React.useState(showIndividualResponses);
  const [activeTab, setActiveTab] = React.useState<'answer' | 'individual' | 'costs'>('answer');

  const successfulResponses = result.individual_responses.filter((r) => r.success);
  const hasMultipleResponses = successfulResponses.length > 1;

  return (
    <div className="space-y-4">
      {/* Temporal Warning Banner - shown for temporal queries */}
      <TemporalWarning
        temporalDetection={result.temporal_detection}
        warningMessage={result.ui_warning_message}
        wasSearchUsed={result.was_search_used}
      />

      {/* Search Results - shown when web search was used */}
      {result.was_search_used && result.search_results && (
        <SearchResults searchResults={result.search_results} />
      )}

      {/* Routing Info Panel */}
      <RoutingInfoPanel
        classification={result.classification}
        routingDecision={result.routing_decision}
        costBreakdown={result.cost_breakdown}
        executionMetrics={result.execution_metrics}
        modelsUsed={result.models_used}
        fallbackUsed={result.fallback_used}
        fallbackReason={result.fallback_reason}
      />

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('answer')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'answer'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          Final Answer
        </button>
        {hasMultipleResponses && (
          <button
            onClick={() => setActiveTab('individual')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'individual'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            Individual Responses ({successfulResponses.length})
          </button>
        )}
        <button
          onClick={() => setActiveTab('costs')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'costs'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          Cost Analysis
        </button>
      </div>

      {/* Tab Content */}
      <div className="min-h-[300px]">
        {/* Final Answer Tab */}
        {activeTab === 'answer' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {result.synthesis ? 'Synthesized Answer' : 'Answer'}
              </h3>
              {result.synthesis && (
                <span className="text-xs px-2 py-1 bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200 rounded-full">
                  via {result.synthesis.synthesis_model}
                </span>
              )}
              {!result.synthesis && successfulResponses.length === 1 && (
                <span className="text-xs px-2 py-1 bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200 rounded-full">
                  via {successfulResponses[0].model_name}
                </span>
              )}
            </div>
            <div className="prose dark:prose-invert max-w-none">
              <ReactMarkdown>{result.final_answer}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Individual Responses Tab */}
        {activeTab === 'individual' && hasMultipleResponses && (
          <div className="space-y-4">
            {successfulResponses.map((response, index) => (
              <div
                key={response.model_name}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-1 bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200 rounded text-sm font-medium">
                      {response.model_name}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {response.response_time_seconds.toFixed(2)}s
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {response.tokens_used.total_tokens} tokens
                    </span>
                    <span className="text-xs text-green-600 dark:text-green-400">
                      ${response.cost_estimate.toFixed(4)}
                    </span>
                  </div>
                  {response.cache_status === 'hit' && (
                    <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                      Cached
                    </span>
                  )}
                </div>
                <div className="prose dark:prose-invert max-w-none text-sm">
                  <ReactMarkdown>{response.response_text}</ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Costs Tab */}
        {activeTab === 'costs' && (
          <CostVisualization costBreakdown={result.cost_breakdown} />
        )}
      </div>
    </div>
  );
};

export default SmartRouteResult;
