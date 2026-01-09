/**
 * ResponseCard Component
 * Expandable accordion card showing individual model responses.
 */

import React, { useState } from 'react';
import { ChevronDown, Clock, Coins, Hash, CheckCircle, XCircle, Database } from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import { ModelResponse } from '@/services/api';

interface ResponseCardProps {
  response: ModelResponse;
  index: number;
  defaultExpanded?: boolean;
}

export const ResponseCard: React.FC<ResponseCardProps> = ({
  response,
  index,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const formatCost = (cost: number): string => {
    if (cost < 0.0001) {
      return `$${(cost * 10000).toFixed(4)}/10K`;
    }
    return `$${cost.toFixed(6)}`;
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 1) {
      return `${(seconds * 1000).toFixed(0)}ms`;
    }
    return `${seconds.toFixed(2)}s`;
  };

  // Determine status styling
  const isSuccess = response.success;
  const isCached = response.cache_status === 'hit';

  return (
    <div
      className={clsx(
        'rounded-xl border-2 overflow-hidden transition-all duration-200',
        isSuccess
          ? 'border-gray-200 dark:border-gray-700'
          : 'border-red-200 dark:border-red-900'
      )}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={clsx(
          'w-full px-4 py-3 flex items-center justify-between',
          'bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800',
          'transition-colors duration-200'
        )}
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-3">
          {/* Status indicator */}
          {isSuccess ? (
            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          )}
          
          {/* Model name */}
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {response.model_name}
          </span>

          {/* Cached badge */}
          {isCached && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded-full">
              <Database className="w-3 h-3" />
              Cached
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Quick stats */}
          <div className="hidden sm:flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1" title="Response time">
              <Clock className="w-4 h-4" />
              {formatTime(response.response_time_seconds)}
            </span>
            <span className="flex items-center gap-1" title="Tokens used">
              <Hash className="w-4 h-4" />
              {response.tokens_used.total_tokens.toLocaleString()}
            </span>
            <span className="flex items-center gap-1" title="Estimated cost">
              <Coins className="w-4 h-4" />
              {formatCost(response.cost_estimate)}
            </span>
          </div>

          {/* Expand/collapse icon */}
          <ChevronDown
            className={clsx(
              'w-5 h-5 text-gray-400 transition-transform duration-200',
              isExpanded && 'rotate-180'
            )}
          />
        </div>
      </button>

      {/* Expandable content */}
      <div
        className={clsx(
          'overflow-hidden transition-all duration-300',
          isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          {/* Mobile stats */}
          <div className="sm:hidden flex items-center gap-4 mb-4 text-sm text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              {formatTime(response.response_time_seconds)}
            </span>
            <span className="flex items-center gap-1">
              <Hash className="w-4 h-4" />
              {response.tokens_used.total_tokens.toLocaleString()}
            </span>
            <span className="flex items-center gap-1">
              <Coins className="w-4 h-4" />
              {formatCost(response.cost_estimate)}
            </span>
          </div>

          {/* Response content or error */}
          {isSuccess ? (
            <div className="markdown-content prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{response.response_text}</ReactMarkdown>
            </div>
          ) : (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <p className="text-red-600 dark:text-red-400 font-medium">
                Error from {response.model_name}
              </p>
              <p className="mt-1 text-sm text-red-500 dark:text-red-300">
                {response.error || 'An unknown error occurred'}
              </p>
            </div>
          )}

          {/* Token breakdown */}
          {isSuccess && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                Token Usage
              </h4>
              <div className="flex gap-6 text-sm">
                <div>
                  <span className="text-gray-400">Input:</span>{' '}
                  <span className="font-mono text-gray-600 dark:text-gray-300">
                    {response.tokens_used.prompt_tokens.toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Output:</span>{' '}
                  <span className="font-mono text-gray-600 dark:text-gray-300">
                    {response.tokens_used.completion_tokens.toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Total:</span>{' '}
                  <span className="font-mono font-medium text-gray-900 dark:text-gray-100">
                    {response.tokens_used.total_tokens.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResponseCard;
