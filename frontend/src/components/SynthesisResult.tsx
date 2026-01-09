/**
 * SynthesisResult Component
 * Displays the synthesized answer prominently with copy functionality.
 */

import React, { useState } from 'react';
import { Copy, Check, Sparkles, Clock, Coins, Hash, Code2, FileText } from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import { SynthesisResult as SynthesisResultType } from '@/services/api';

interface SynthesisResultProps {
  synthesis: SynthesisResultType;
  question: string;
}

export const SynthesisResult: React.FC<SynthesisResultProps> = ({
  synthesis,
  question,
}) => {
  const [copied, setCopied] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(synthesis.synthesized_answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

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

  return (
    <div className="rounded-2xl border-2 border-primary-200 dark:border-primary-800 bg-gradient-to-br from-primary-50 to-white dark:from-primary-900/20 dark:to-gray-900 overflow-hidden animate-slide-up">
      {/* Header */}
      <div className="px-6 py-4 bg-primary-100/50 dark:bg-primary-900/30 border-b border-primary-200 dark:border-primary-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Synthesized Answer
            </h2>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Toggle raw JSON */}
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors',
                showRawJson
                  ? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
              )}
              title={showRawJson ? 'Show formatted' : 'Show raw JSON'}
            >
              {showRawJson ? (
                <>
                  <FileText className="w-4 h-4" />
                  Formatted
                </>
              ) : (
                <>
                  <Code2 className="w-4 h-4" />
                  JSON
                </>
              )}
            </button>

            {/* Copy button */}
            <button
              onClick={handleCopy}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all',
                copied
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                  : 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-900/50'
              )}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy
                </>
              )}
            </button>
          </div>
        </div>

        {/* Question reference */}
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          <span className="font-medium">Question:</span> {question}
        </p>
      </div>

      {/* Content */}
      <div className="p-6">
        {showRawJson ? (
          <pre className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-x-auto text-sm font-mono text-gray-800 dark:text-gray-200">
            {JSON.stringify(synthesis, null, 2)}
          </pre>
        ) : (
          <div className="markdown-content prose prose-primary dark:prose-invert max-w-none">
            <ReactMarkdown>{synthesis.synthesized_answer}</ReactMarkdown>
          </div>
        )}

        {/* Model contributions */}
        {synthesis.model_contributions && Object.keys(synthesis.model_contributions).length > 0 && (
          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Model Contributions
            </h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(synthesis.model_contributions).map(([model, contribution]) => (
                <div
                  key={model}
                  className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm"
                >
                  <span className="font-medium text-gray-700 dark:text-gray-300">{model}:</span>{' '}
                  <span className="text-gray-500 dark:text-gray-400">{contribution}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer stats */}
      <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1.5">
            <span className="font-medium">Synthesis Model:</span>
            {synthesis.synthesis_model}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="w-4 h-4" />
            {formatTime(synthesis.response_time_seconds)}
          </span>
          <span className="flex items-center gap-1.5">
            <Hash className="w-4 h-4" />
            {synthesis.tokens_used.total_tokens.toLocaleString()} tokens
          </span>
          <span className="flex items-center gap-1.5">
            <Coins className="w-4 h-4" />
            {formatCost(synthesis.cost_estimate)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SynthesisResult;
