/**
 * TemporalWarning Component
 * 
 * Displays a warning banner when queries involve temporal information
 * that may be beyond the AI models' knowledge cutoff date.
 */

import React from 'react';
import { TemporalDetectionResult, TemporalScope } from '../services/api';

interface TemporalWarningProps {
  temporalDetection?: TemporalDetectionResult;
  warningMessage?: string;
  wasSearchUsed?: boolean;
  className?: string;
}

const scopeColors: Record<TemporalScope, { bg: string; border: string; text: string; icon: string }> = {
  evergreen: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-200 dark:border-green-800',
    text: 'text-green-800 dark:text-green-200',
    icon: '✓',
  },
  historical: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    text: 'text-blue-800 dark:text-blue-200',
    icon: '📚',
  },
  current: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    border: 'border-amber-200 dark:border-amber-800',
    text: 'text-amber-800 dark:text-amber-200',
    icon: '⚠️',
  },
  future: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-800',
    text: 'text-red-800 dark:text-red-200',
    icon: '🔮',
  },
};

const scopeDescriptions: Record<TemporalScope, string> = {
  evergreen: 'This information is timeless and well within model knowledge.',
  historical: 'This query refers to historical events within model knowledge.',
  current: 'This query asks about recent/current information that may be beyond model knowledge (Oct 2023).',
  future: 'This query asks about future events - models cannot predict the future.',
};

export const TemporalWarning: React.FC<TemporalWarningProps> = ({
  temporalDetection,
  warningMessage,
  wasSearchUsed,
  className = '',
}) => {
  // Don't show if no temporal detection or if query is evergreen
  if (!temporalDetection || !temporalDetection.is_temporal) {
    return null;
  }

  const scope = temporalDetection.temporal_scope;
  const colors = scopeColors[scope];
  const description = scopeDescriptions[scope];

  return (
    <div
      className={`rounded-lg border p-4 mb-4 ${colors.bg} ${colors.border} ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <span className="text-xl flex-shrink-0" aria-hidden="true">
          {colors.icon}
        </span>
        <div className="flex-1 min-w-0">
          <h4 className={`font-semibold text-sm ${colors.text}`}>
            Temporal Query Detected
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-white/50 dark:bg-black/20">
              {scope.charAt(0).toUpperCase() + scope.slice(1)}
            </span>
          </h4>
          
          {warningMessage ? (
            <p className={`mt-1 text-sm ${colors.text} opacity-90`}>
              {warningMessage}
            </p>
          ) : (
            <p className={`mt-1 text-sm ${colors.text} opacity-90`}>
              {description}
            </p>
          )}

          {/* Show detected indicators */}
          <div className="mt-2 flex flex-wrap gap-2">
            {temporalDetection.detected_keywords.length > 0 && (
              <div className="text-xs">
                <span className={`font-medium ${colors.text}`}>Keywords: </span>
                {temporalDetection.detected_keywords.map((kw, idx) => (
                  <span
                    key={idx}
                    className={`inline-block px-1.5 py-0.5 rounded ${colors.text} bg-white/30 dark:bg-black/20 mr-1`}
                  >
                    {kw}
                  </span>
                ))}
              </div>
            )}
            {temporalDetection.detected_years.length > 0 && (
              <div className="text-xs">
                <span className={`font-medium ${colors.text}`}>Years: </span>
                {temporalDetection.detected_years.map((year, idx) => (
                  <span
                    key={idx}
                    className={`inline-block px-1.5 py-0.5 rounded ${colors.text} bg-white/30 dark:bg-black/20 mr-1`}
                  >
                    {year}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Search status */}
          {temporalDetection.requires_current_data && (
            <div className={`mt-2 text-xs ${colors.text} opacity-80 flex items-center gap-1`}>
              {wasSearchUsed ? (
                <>
                  <span className="text-green-600 dark:text-green-400">✓</span>
                  Web search was used to supplement model knowledge
                </>
              ) : (
                <>
                  <span className="text-yellow-600 dark:text-yellow-400">!</span>
                  Web search unavailable - results based on training data only
                </>
              )}
            </div>
          )}

          {/* Confidence indicator */}
          <div className="mt-2 flex items-center gap-2">
            <span className={`text-xs ${colors.text} opacity-70`}>
              Detection confidence:
            </span>
            <div className="flex-1 max-w-24 h-1.5 bg-white/30 dark:bg-black/30 rounded-full overflow-hidden">
              <div
                className={`h-full ${scope === 'evergreen' ? 'bg-green-500' : scope === 'current' ? 'bg-amber-500' : scope === 'future' ? 'bg-red-500' : 'bg-blue-500'}`}
                style={{ width: `${temporalDetection.confidence * 100}%` }}
              />
            </div>
            <span className={`text-xs font-mono ${colors.text}`}>
              {(temporalDetection.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemporalWarning;
