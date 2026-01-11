/**
 * SearchResults Component
 * 
 * Displays web search results used to augment the AI response.
 * Shows sources, snippets, and links for transparency.
 */

import React, { useState } from 'react';
import { SearchResults as SearchResultsType } from '../services/api';

interface SearchResultsProps {
  searchResults?: SearchResultsType;
  className?: string;
}

export const SearchResults: React.FC<SearchResultsProps> = ({
  searchResults,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!searchResults || !searchResults.results || searchResults.results.length === 0) {
    return null;
  }

  return (
    <div
      className={`rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20 overflow-hidden ${className}`}
    >
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-indigo-100 dark:hover:bg-indigo-800/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">🔍</span>
          <span className="font-medium text-indigo-800 dark:text-indigo-200">
            Web Search Results
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-200 dark:bg-indigo-800 text-indigo-700 dark:text-indigo-300">
            {searchResults.results.length} sources
          </span>
          <span className="text-xs text-indigo-600 dark:text-indigo-400">
            via {searchResults.search_provider}
          </span>
        </div>
        <svg
          className={`w-5 h-5 text-indigo-600 dark:text-indigo-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          <p className="text-xs text-indigo-600 dark:text-indigo-400 italic">
            Search query: "{searchResults.query}"
          </p>
          
          {searchResults.results.map((result, idx) => (
            <div
              key={idx}
              className="p-3 rounded-md bg-white dark:bg-gray-800 border border-indigo-100 dark:border-indigo-900"
            >
              <div className="flex items-start justify-between gap-2">
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline line-clamp-1"
                >
                  {result.title}
                </a>
                <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 flex-shrink-0">
                  #{idx + 1}
                </span>
              </div>
              
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                {result.snippet}
              </p>
              
              <div className="mt-2 flex items-center gap-2 text-xs">
                {result.source && (
                  <span className="text-gray-500 dark:text-gray-500">
                    Source: {result.source}
                  </span>
                )}
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 dark:text-indigo-400 hover:underline truncate max-w-xs"
                >
                  {new URL(result.url).hostname}
                </a>
              </div>
            </div>
          ))}

          <p className="text-xs text-indigo-600 dark:text-indigo-400 text-center pt-2">
            These sources were used to provide current information beyond the model's knowledge cutoff.
          </p>
        </div>
      )}
    </div>
  );
};

export default SearchResults;
