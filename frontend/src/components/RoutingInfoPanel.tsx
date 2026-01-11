/**
 * Routing Info Panel Component
 * Displays query classification, routing decisions, costs, and savings
 */

import React, { useState } from 'react';
import {
  QueryClassification,
  RoutingDecision,
  CostBreakdown,
  ExecutionMetrics,
} from '../services/api';

interface RoutingInfoPanelProps {
  classification: QueryClassification;
  routingDecision: RoutingDecision;
  costBreakdown: CostBreakdown;
  executionMetrics: ExecutionMetrics;
  modelsUsed: string[];
  fallbackUsed: boolean;
  fallbackReason: string | null;
}

const complexityColors = {
  simple: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  moderate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  complex: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

const intentIcons: Record<string, string> = {
  factual: '📊',
  creative: '🎨',
  analytical: '🔍',
  procedural: '📋',
  comparative: '⚖️',
};

const domainIcons: Record<string, string> = {
  coding: '💻',
  technical: '⚙️',
  general: '🌐',
  creative: '✨',
  research: '📚',
};

export const RoutingInfoPanel: React.FC<RoutingInfoPanelProps> = ({
  classification,
  routingDecision,
  costBreakdown,
  executionMetrics,
  modelsUsed,
  fallbackUsed,
  fallbackReason,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showCostChart, setShowCostChart] = useState(false);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Routing Information
          </h3>
          {fallbackUsed && (
            <span className="text-xs px-2 py-1 bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200 rounded-full">
              Fallback Used
            </span>
          )}
        </div>
      </div>

      {/* Classification Summary */}
      <div className="p-4 space-y-4">
        {/* Query Classification */}
        <div>
          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Query Classification
          </h4>
          <div className="flex flex-wrap gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${complexityColors[classification.complexity]}`}>
              {classification.complexity.charAt(0).toUpperCase() + classification.complexity.slice(1)}
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {intentIcons[classification.intent] || '❓'} {classification.intent}
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
              {domainIcons[classification.domain] || '📁'} {classification.domain}
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
              {Math.round(classification.confidence * 100)}% confidence
            </span>
          </div>
        </div>

        {/* Models Used */}
        <div>
          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Models Used
          </h4>
          <div className="flex flex-wrap gap-2">
            {modelsUsed.map((model) => (
              <span
                key={model}
                className="px-3 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200"
              >
                {model}
              </span>
            ))}
            {routingDecision.use_synthesis && routingDecision.synthesis_model && (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200">
                + {routingDecision.synthesis_model} (synthesis)
              </span>
            )}
          </div>
        </div>

        {/* Cost & Savings */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400">Total Cost</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              ${costBreakdown.total_cost.toFixed(4)}
            </div>
          </div>
          <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-3">
            <div className="text-xs text-green-600 dark:text-green-400">Savings</div>
            <div className="text-lg font-semibold text-green-700 dark:text-green-300">
              ${costBreakdown.savings.toFixed(4)}
            </div>
          </div>
          <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-3">
            <div className="text-xs text-green-600 dark:text-green-400">Savings %</div>
            <div className="text-lg font-semibold text-green-700 dark:text-green-300">
              {costBreakdown.savings_percentage.toFixed(1)}%
            </div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400">Total Time</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {(executionMetrics.total_time_ms / 1000).toFixed(2)}s
            </div>
          </div>
        </div>

        {/* Routing Rationale */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
          <h4 className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-1">
            Routing Rationale
          </h4>
          <p className="text-sm text-blue-800 dark:text-blue-200">
            {routingDecision.routing_rationale}
          </p>
        </div>

        {/* Expandable Details */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
        >
          <svg
            className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {showDetails ? 'Hide' : 'Show'} Detailed Breakdown
        </button>

        {showDetails && (
          <div className="space-y-4 pt-2 border-t border-gray-200 dark:border-gray-700">
            {/* Classification Details */}
            <div>
              <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Classification Reasoning
              </h5>
              <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                {classification.reasoning}
              </p>
            </div>

            {/* Cost Breakdown by Model */}
            <div>
              <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Cost by Model
              </h5>
              <div className="space-y-2">
                {Object.entries(costBreakdown.model_costs).map(([model, cost]) => (
                  <div key={model} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">{model}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{
                            width: `${Math.min(100, (cost / costBreakdown.total_cost) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white w-20 text-right">
                        ${cost.toFixed(4)}
                      </span>
                    </div>
                  </div>
                ))}
                {costBreakdown.synthesis_cost > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Synthesis</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-pink-500 h-2 rounded-full"
                          style={{
                            width: `${Math.min(100, (costBreakdown.synthesis_cost / costBreakdown.total_cost) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white w-20 text-right">
                        ${costBreakdown.synthesis_cost.toFixed(4)}
                      </span>
                    </div>
                  </div>
                )}
                {costBreakdown.classification_cost > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Classification</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full"
                          style={{
                            width: `${Math.min(100, (costBreakdown.classification_cost / costBreakdown.total_cost) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white w-20 text-right">
                        ${costBreakdown.classification_cost.toFixed(4)}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Execution Time Breakdown */}
            <div>
              <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Execution Time Breakdown
              </h5>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Classification</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {executionMetrics.classification_time_ms.toFixed(0)}ms
                  </span>
                </div>
                {Object.entries(executionMetrics.model_execution_time_ms).map(([model, time]) => (
                  <div key={model} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">{model}</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {time.toFixed(0)}ms
                    </span>
                  </div>
                ))}
                {executionMetrics.synthesis_time_ms > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Synthesis</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {executionMetrics.synthesis_time_ms.toFixed(0)}ms
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Full Classification JSON */}
            <div>
              <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Full Classification JSON
              </h5>
              <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded-lg overflow-x-auto">
                {JSON.stringify(classification, null, 2)}
              </pre>
            </div>

            {/* Fallback Information */}
            {fallbackUsed && fallbackReason && (
              <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3">
                <h5 className="text-xs font-medium text-orange-600 dark:text-orange-400 uppercase tracking-wide mb-1">
                  Fallback Reason
                </h5>
                <p className="text-sm text-orange-800 dark:text-orange-200">{fallbackReason}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RoutingInfoPanel;
