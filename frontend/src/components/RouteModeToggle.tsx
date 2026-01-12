/**
 * Route Mode Toggle Component
 * Allows users to switch between Smart Route (cost-optimized), Full Ensemble (quality-optimized),
 * and Time-Travel (temporal evolution view)
 */

import React from 'react';

export type RouteMode = 'smart' | 'ensemble' | 'time-travel';

interface RouteModeToggleProps {
  mode: RouteMode;
  onModeChange: (mode: RouteMode) => void;
  disabled?: boolean;
}

export const RouteModeToggle: React.FC<RouteModeToggleProps> = ({
  mode,
  onModeChange,
  disabled = false,
}) => {
  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Routing Mode:
      </span>
      
      <div className="flex flex-wrap bg-gray-200 dark:bg-gray-700 rounded-lg p-1 gap-1">
        <button
          onClick={() => onModeChange('smart')}
          disabled={disabled}
          className={`
            px-4 py-2 text-sm font-medium rounded-md transition-all duration-200
            ${mode === 'smart'
              ? 'bg-green-500 text-white shadow-md'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Smart Route
          </div>
        </button>
        
        <button
          onClick={() => onModeChange('ensemble')}
          disabled={disabled}
          className={`
            px-4 py-2 text-sm font-medium rounded-md transition-all duration-200
            ${mode === 'ensemble'
              ? 'bg-blue-500 text-white shadow-md'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Full Ensemble
          </div>
        </button>

        <button
          onClick={() => onModeChange('time-travel')}
          disabled={disabled}
          className={`
            px-4 py-2 text-sm font-medium rounded-md transition-all duration-200
            ${mode === 'time-travel'
              ? 'bg-purple-500 text-white shadow-md'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Time-Travel
          </div>
        </button>
      </div>
      
      <div className="text-xs text-gray-500 dark:text-gray-400 sm:ml-2">
        {mode === 'smart' && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full"></span>
            Cost-optimized routing based on query complexity
          </span>
        )}
        {mode === 'ensemble' && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 bg-blue-500 rounded-full"></span>
            Query all models with synthesis for best quality
          </span>
        )}
        {mode === 'time-travel' && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 bg-purple-500 rounded-full"></span>
            See how answers evolved over time
          </span>
        )}
      </div>
    </div>
  );
};

export default RouteModeToggle;
