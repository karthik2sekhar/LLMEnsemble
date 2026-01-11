/**
 * Cost Visualization Component
 * Displays cost breakdown charts and projections
 */

import React from 'react';
import { CostBreakdown, RoutingStats } from '../services/api';

interface CostVisualizationProps {
  costBreakdown: CostBreakdown;
  routingStats?: RoutingStats;
}

export const CostVisualization: React.FC<CostVisualizationProps> = ({
  costBreakdown,
  routingStats,
}) => {
  const modelCosts = Object.entries(costBreakdown.model_costs);
  const totalModelCost = modelCosts.reduce((sum, [, cost]) => sum + cost, 0);
  
  // Calculate projections
  const dailyCost = costBreakdown.total_cost * 10; // Assume 10 queries per day
  const monthlyCost = dailyCost * 30;
  const monthlyEnsembleCost = costBreakdown.full_ensemble_cost * 10 * 30;
  const monthlySavings = monthlyEnsembleCost - monthlyCost;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 p-4 space-y-6">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Cost Analysis
      </h3>

      {/* Cost Comparison Bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
          <span>Smart Route</span>
          <span>Full Ensemble</span>
        </div>
        <div className="relative h-8 bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden">
          <div
            className="absolute left-0 top-0 h-full bg-gradient-to-r from-green-500 to-green-400 flex items-center justify-center"
            style={{ width: `${Math.min(100, (costBreakdown.total_cost / costBreakdown.full_ensemble_cost) * 100)}%` }}
          >
            <span className="text-xs font-medium text-white px-2">
              ${costBreakdown.total_cost.toFixed(4)}
            </span>
          </div>
          <div className="absolute right-2 top-0 h-full flex items-center">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              ${costBreakdown.full_ensemble_cost.toFixed(4)}
            </span>
          </div>
        </div>
        <div className="text-center mt-2">
          <span className="text-sm font-semibold text-green-600 dark:text-green-400">
            You saved {costBreakdown.savings_percentage.toFixed(1)}% (${costBreakdown.savings.toFixed(4)})
          </span>
        </div>
      </div>

      {/* Cost Distribution Pie-style Bars */}
      <div>
        <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          Cost Distribution
        </h4>
        <div className="space-y-3">
          {modelCosts.map(([model, cost]) => {
            const percentage = totalModelCost > 0 ? (cost / totalModelCost) * 100 : 0;
            const colors: Record<string, string> = {
              'gpt-4o-mini': 'bg-green-500',
              'gpt-4o': 'bg-blue-500',
              'gpt-4-turbo': 'bg-purple-500',
              'gpt-5.2': 'bg-pink-500',
            };
            return (
              <div key={model}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-600 dark:text-gray-400">{model}</span>
                  <span className="text-gray-900 dark:text-white font-medium">
                    ${cost.toFixed(4)} ({percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${colors[model] || 'bg-gray-500'} rounded-full transition-all duration-500`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
          {costBreakdown.synthesis_cost > 0 && (
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-600 dark:text-gray-400">Synthesis</span>
                <span className="text-gray-900 dark:text-white font-medium">
                  ${costBreakdown.synthesis_cost.toFixed(4)}
                </span>
              </div>
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-pink-500 rounded-full transition-all duration-500"
                  style={{ width: `${(costBreakdown.synthesis_cost / costBreakdown.total_cost) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Projections */}
      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
        <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          Cost Projections (10 queries/day)
        </h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Monthly with Smart Route</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              ${monthlyCost.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Monthly with Full Ensemble</div>
            <div className="text-xl font-bold text-gray-400 line-through">
              ${monthlyEnsembleCost.toFixed(2)}
            </div>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs text-green-600 dark:text-green-400">Projected Monthly Savings</div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            ${monthlySavings.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Session Stats */}
      {routingStats && routingStats.total_queries > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <h4 className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-3">
            Session Statistics
          </h4>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {routingStats.total_queries}
              </div>
              <div className="text-xs text-blue-600 dark:text-blue-400">Total Queries</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-700 dark:text-green-300">
                ${routingStats.total_savings.toFixed(4)}
              </div>
              <div className="text-xs text-green-600 dark:text-green-400">Total Saved</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
                {routingStats.average_savings_percentage.toFixed(1)}%
              </div>
              <div className="text-xs text-purple-600 dark:text-purple-400">Avg Savings</div>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-800">
            <div className="text-xs text-blue-600 dark:text-blue-400 mb-2">Query Distribution</div>
            <div className="flex gap-2">
              <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded text-xs">
                Simple: {routingStats.simple_queries}
              </span>
              <span className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded text-xs">
                Moderate: {routingStats.moderate_queries}
              </span>
              <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-xs">
                Complex: {routingStats.complex_queries}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CostVisualization;
