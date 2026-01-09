/**
 * LoadingState Component
 * Shows loading skeleton and progress indicators while waiting for responses.
 */

import React from 'react';
import { Loader2, Sparkles } from 'lucide-react';
import clsx from 'clsx';

interface LoadingStateProps {
  models: string[];
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  models,
  message = 'Getting responses from AI models...',
}) => {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Main loading indicator */}
      <div className="text-center py-8">
        <div className="inline-flex items-center gap-3 px-6 py-3 bg-primary-50 dark:bg-primary-900/20 rounded-full">
          <Loader2 className="w-5 h-5 text-primary-600 dark:text-primary-400 animate-spin" />
          <span className="text-primary-700 dark:text-primary-300 font-medium">
            {message}
          </span>
        </div>
      </div>

      {/* Synthesis placeholder */}
      <div className="rounded-2xl border-2 border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-gray-400 dark:text-gray-500" />
            <div className="h-5 w-40 skeleton rounded"></div>
          </div>
        </div>
        <div className="p-6 space-y-3">
          <div className="h-4 skeleton rounded w-full"></div>
          <div className="h-4 skeleton rounded w-5/6"></div>
          <div className="h-4 skeleton rounded w-4/6"></div>
          <div className="h-4 skeleton rounded w-full"></div>
          <div className="h-4 skeleton rounded w-3/4"></div>
        </div>
      </div>

      {/* Model response placeholders */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
          Individual Model Responses
        </h3>
        
        {models.map((model, index) => (
          <div
            key={model}
            className="rounded-xl border-2 border-gray-200 dark:border-gray-700 overflow-hidden"
            style={{ animationDelay: `${index * 150}ms` }}
          >
            <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full skeleton"></div>
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {model}
                </span>
                <span className="flex items-center gap-1.5 text-xs text-gray-400">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Processing...
                </span>
              </div>
            </div>
            <div className="p-4 space-y-2">
              <div className="h-3 skeleton rounded w-full"></div>
              <div className="h-3 skeleton rounded w-5/6"></div>
              <div className="h-3 skeleton rounded w-4/6"></div>
            </div>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="relative">
        <div className="h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-primary-500 progress-bar rounded-full"></div>
        </div>
        <p className="mt-2 text-xs text-center text-gray-400 dark:text-gray-500">
          This may take up to 30 seconds per model
        </p>
      </div>
    </div>
  );
};

/**
 * LoadingSkeleton Component
 * Simple skeleton loader for various UI elements.
 */
export const LoadingSkeleton: React.FC<{
  className?: string;
  lines?: number;
}> = ({ className, lines = 3 }) => {
  return (
    <div className={clsx('space-y-3', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 skeleton rounded"
          style={{ width: `${100 - i * 15}%` }}
        ></div>
      ))}
    </div>
  );
};

export default LoadingState;
