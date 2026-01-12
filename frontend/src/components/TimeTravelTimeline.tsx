/**
 * Time-Travel Timeline Component
 * 
 * Displays a visual timeline of how an answer evolved across different
 * time periods, showing snapshots, key changes, and evolution insights.
 */

import React, { useState } from 'react';
import { Clock, TrendingUp, Lightbulb, ChevronDown, ChevronUp, Calendar, ArrowRight, Sparkles, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

// Types matching backend schemas
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
  // Routing fix: expose complexity classification for transparency
  base_complexity?: string;
  routing_validation_passed?: boolean;
}

interface TimeTravelTimelineProps {
  result: TimeTravelResponse;
  showFullAnswers?: boolean;
}

// Sensitivity badge colors
const sensitivityColors: Record<TemporalSensitivityLevel, string> = {
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  none: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400',
};

// Velocity indicator colors
const velocityColors: Record<string, string> = {
  fast: 'text-red-500',
  moderate: 'text-yellow-500',
  slow: 'text-blue-500',
  minimal: 'text-gray-500',
  none: 'text-gray-400',
};

// Complexity badge colors for routing transparency
const complexityColors: Record<string, string> = {
  complex: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  moderate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  simple: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
};

export const TimeTravelTimeline: React.FC<TimeTravelTimelineProps> = ({
  result,
  showFullAnswers = false,
}) => {
  const [expandedSnapshots, setExpandedSnapshots] = useState<Set<number>>(
    new Set([result.snapshots.length - 1]) // Expand only the most recent by default
  );
  const [showEvolution, setShowEvolution] = useState(true);
  const [showInsights, setShowInsights] = useState(true);

  // If not eligible for time-travel, show a message
  if (!result.is_eligible) {
    return (
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <AlertCircle className="w-5 h-5 text-gray-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Time-Travel Not Applicable
          </h3>
        </div>
        <p className="text-gray-600 dark:text-gray-400 mb-2">{result.skip_reason}</p>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${sensitivityColors[result.temporal_sensitivity]}`}>
            {result.temporal_sensitivity.toUpperCase()} Sensitivity
          </span>
          <span className="text-xs text-gray-500">{result.sensitivity_reasoning}</span>
        </div>
      </div>
    );
  }

  const toggleSnapshot = (index: number) => {
    const newExpanded = new Set(expandedSnapshots);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSnapshots(newExpanded);
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with sensitivity info */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl p-6 border border-purple-200 dark:border-purple-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Clock className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Time-Travel Answers
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                See how the answer evolved over time
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1.5 text-sm font-medium rounded-full ${sensitivityColors[result.temporal_sensitivity]}`}>
              ⭐ {result.temporal_sensitivity.toUpperCase()} Sensitivity
            </span>
            {result.base_complexity && (
              <span className={`px-3 py-1.5 text-sm font-medium rounded-full ${complexityColors[result.base_complexity] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'}`}>
                🧠 {result.base_complexity.toUpperCase()} Complexity
              </span>
            )}
          </div>
        </div>
        
        <p className="text-sm text-gray-700 dark:text-gray-300">
          <span className="font-medium">Question:</span> {result.question}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          {result.sensitivity_reasoning}
        </p>
      </div>

      {/* Timeline View */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-500" />
            Timeline View
          </h3>
          <div className="text-sm text-gray-500">
            {result.snapshots.length} snapshots
          </div>
        </div>

        <div className="p-6">
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-500 via-purple-500 to-pink-500" />

            {/* Snapshots */}
            <div className="space-y-6">
              {result.snapshots.map((snapshot, index) => {
                const isExpanded = expandedSnapshots.has(index);
                const isLast = index === result.snapshots.length - 1;
                
                return (
                  <div key={index} className="relative pl-12">
                    {/* Timeline dot */}
                    <div className={`absolute left-0 w-10 h-10 rounded-full flex items-center justify-center z-10 ${
                      isLast 
                        ? 'bg-green-500 text-white' 
                        : 'bg-white dark:bg-gray-800 border-2 border-blue-500 text-blue-500'
                    }`}>
                      {isLast ? (
                        <Sparkles className="w-5 h-5" />
                      ) : (
                        <span className="text-sm font-bold">{index + 1}</span>
                      )}
                    </div>

                    {/* Snapshot card */}
                    <div className={`bg-gray-50 dark:bg-gray-700/50 rounded-xl border ${
                      isLast 
                        ? 'border-green-200 dark:border-green-800' 
                        : 'border-gray-200 dark:border-gray-600'
                    } overflow-hidden`}>
                      {/* Snapshot header */}
                      <button
                        onClick={() => toggleSnapshot(index)}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-600/50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            📅 {snapshot.date_label}
                          </span>
                          {isLast && (
                            <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                              Current
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">
                            {snapshot.model_used} • ${snapshot.cost_estimate.toFixed(4)}
                          </span>
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          )}
                        </div>
                      </button>

                      {/* Expanded content */}
                      {isExpanded && (
                        <div className="px-4 pb-4 space-y-4">
                          {/* Key changes from previous */}
                          {snapshot.key_changes.length > 0 && (
                            <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 border border-yellow-200 dark:border-yellow-800">
                              <div className="flex items-center gap-2 mb-2">
                                <ArrowRight className="w-4 h-4 text-yellow-600" />
                                <span className="text-sm font-medium text-yellow-800 dark:text-yellow-400">
                                  Changes from Previous Period
                                </span>
                              </div>
                              <ul className="space-y-1">
                                {snapshot.key_changes.map((change, i) => (
                                  <li key={i} className="text-sm text-yellow-700 dark:text-yellow-300 flex items-start gap-2">
                                    <span className="text-yellow-500">⚡</span>
                                    {change}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Answer */}
                          <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown>
                              {showFullAnswers || isExpanded 
                                ? snapshot.answer 
                                : snapshot.answer.slice(0, 500) + (snapshot.answer.length > 500 ? '...' : '')}
                            </ReactMarkdown>
                          </div>

                          {/* Data points */}
                          {snapshot.data_points.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                              {snapshot.data_points.map((point, i) => (
                                <span key={i} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                                  📊 {point.slice(0, 50)}...
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Evolution Summary */}
      {result.evolution_narrative && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button
            onClick={() => setShowEvolution(!showEvolution)}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-500" />
              🔄 Evolution Summary
            </h3>
            {showEvolution ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {showEvolution && (
            <div className="px-6 pb-6 space-y-4">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <p className="text-gray-700 dark:text-gray-300">{result.evolution_narrative}</p>
              </div>

              {/* Change velocity */}
              <div className="flex items-center gap-4 py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span className="text-sm text-gray-600 dark:text-gray-400">Rate of Change:</span>
                <span className={`font-medium ${velocityColors[result.change_velocity] || velocityColors.moderate}`}>
                  {result.change_velocity === 'fast' && '🚀 Fast'}
                  {result.change_velocity === 'moderate' && '➡️ Moderate'}
                  {result.change_velocity === 'slow' && '🐢 Slow'}
                  {result.change_velocity === 'minimal' && '🔒 Minimal'}
                </span>
              </div>

              {/* Future outlook */}
              {result.future_outlook && (
                <div className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-lg p-4 border border-indigo-200 dark:border-indigo-800">
                  <h4 className="text-sm font-medium text-indigo-800 dark:text-indigo-400 mb-2">
                    🔮 Future Outlook
                  </h4>
                  <p className="text-sm text-indigo-700 dark:text-indigo-300">
                    {result.future_outlook}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Insights */}
      {result.insights.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button
            onClick={() => setShowInsights(!showInsights)}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-500" />
              💡 Key Insights
            </h3>
            {showInsights ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {showInsights && (
            <div className="px-6 pb-6">
              <ul className="space-y-3">
                {result.insights.map((insight, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center text-sm font-medium text-yellow-800 dark:text-yellow-400">
                      {index + 1}
                    </span>
                    <span className="text-sm text-gray-700 dark:text-gray-300">{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Cost summary */}
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <span className="text-gray-600 dark:text-gray-400">
              Total Cost: <span className="font-medium text-gray-900 dark:text-white">${result.total_cost.toFixed(4)}</span>
            </span>
            <span className="text-gray-600 dark:text-gray-400">
              Time: <span className="font-medium text-gray-900 dark:text-white">{result.total_time_seconds.toFixed(1)}s</span>
            </span>
          </div>
          <span className="text-xs text-gray-500">
            {result.snapshots.length} snapshots generated
          </span>
        </div>
      </div>
    </div>
  );
};

export default TimeTravelTimeline;
