/**
 * StreamingTimeTravelTimeline Component
 * 
 * A streaming-aware timeline that shows results progressively as they
 * arrive from the SSE stream. First result appears in ~8s instead of
 * waiting ~35s for all data.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Clock, 
  TrendingUp, 
  Lightbulb, 
  ChevronDown, 
  ChevronUp, 
  Calendar, 
  ArrowRight, 
  Sparkles,
  Loader2,
  CheckCircle,
  AlertCircle,
  XCircle
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { 
  StreamingTimeTravelResult, 
  Snapshot, 
  KeyChange,
  TimingBreakdown 
} from '../hooks/useTimeTravelStream';

// ============== Types ==============

interface StreamingTimeTravelTimelineProps {
  /** Current streaming result state */
  result: StreamingTimeTravelResult;
  /** Whether stream is still active */
  isStreaming: boolean;
  /** Progress percentage (0-100) */
  progress: number;
  /** Original question */
  question?: string;
  /** Show full answers instead of truncated */
  showFullAnswers?: boolean;
  /** Called when user cancels stream */
  onCancel?: () => void;
}

// ============== Sub-Components ==============

const ProgressBar: React.FC<{ progress: number; isStreaming: boolean }> = ({ 
  progress, 
  isStreaming 
}) => (
  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
    <div 
      className={`h-full rounded-full transition-all duration-500 ${
        isStreaming 
          ? 'bg-gradient-to-r from-purple-500 via-blue-500 to-purple-500 animate-pulse' 
          : progress === 100 
            ? 'bg-green-500' 
            : 'bg-blue-500'
      }`}
      style={{ width: `${progress}%` }}
    />
  </div>
);

const StatusBadge: React.FC<{ 
  isStreaming: boolean; 
  isComplete: boolean;
  error: string | null;
}> = ({ isStreaming, isComplete, error }) => {
  if (error) {
    return (
      <span className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
        <XCircle className="w-4 h-4" />
        Error
      </span>
    );
  }
  
  if (isStreaming) {
    return (
      <span className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
        <Loader2 className="w-4 h-4 animate-spin" />
        Streaming...
      </span>
    );
  }
  
  if (isComplete) {
    return (
      <span className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
        <CheckCircle className="w-4 h-4" />
        Complete
      </span>
    );
  }
  
  return (
    <span className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400">
      Ready
    </span>
  );
};

const SnapshotSkeleton: React.FC<{ index: number }> = ({ index }) => (
  <div className="relative pl-12 animate-pulse">
    <div className="absolute left-0 w-10 h-10 rounded-full bg-gray-300 dark:bg-gray-600" />
    <div className="bg-gray-100 dark:bg-gray-700/50 rounded-xl border border-gray-200 dark:border-gray-600 p-4">
      <div className="flex items-center gap-3 mb-3">
        <div className="h-4 w-24 bg-gray-300 dark:bg-gray-600 rounded" />
        <div className="h-4 w-16 bg-gray-200 dark:bg-gray-500 rounded" />
      </div>
      <div className="space-y-2">
        <div className="h-3 w-full bg-gray-200 dark:bg-gray-500 rounded" />
        <div className="h-3 w-3/4 bg-gray-200 dark:bg-gray-500 rounded" />
        <div className="h-3 w-1/2 bg-gray-200 dark:bg-gray-500 rounded" />
      </div>
    </div>
  </div>
);

const SnapshotCard: React.FC<{
  snapshot: Snapshot;
  index: number;
  isLast: boolean;
  isNew: boolean;
  showFullAnswers: boolean;
}> = ({ snapshot, index, isLast, isNew, showFullAnswers }) => {
  const [isExpanded, setIsExpanded] = useState(isLast || isNew);

  // Auto-expand new snapshots
  useEffect(() => {
    if (isNew) setIsExpanded(true);
  }, [isNew]);

  return (
    <div className={`relative pl-12 transition-all duration-500 ${isNew ? 'animate-slideIn' : ''}`}>
      {/* Timeline dot */}
      <div className={`absolute left-0 w-10 h-10 rounded-full flex items-center justify-center z-10 transition-all duration-300 ${
        isLast 
          ? 'bg-green-500 text-white scale-110' 
          : 'bg-white dark:bg-gray-800 border-2 border-blue-500 text-blue-500'
      } ${isNew ? 'ring-4 ring-blue-300 dark:ring-blue-700' : ''}`}>
        {isLast ? (
          <Sparkles className="w-5 h-5" />
        ) : (
          <span className="text-sm font-bold">{index + 1}</span>
        )}
      </div>

      {/* Snapshot card */}
      <div className={`bg-gray-50 dark:bg-gray-700/50 rounded-xl border ${
        isNew 
          ? 'border-blue-400 dark:border-blue-600 shadow-lg shadow-blue-100 dark:shadow-blue-900/30'
          : isLast 
            ? 'border-green-200 dark:border-green-800' 
            : 'border-gray-200 dark:border-gray-600'
      } overflow-hidden`}>
        {/* Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-600/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              📅 {snapshot.date_label || snapshot.time_period || snapshot.year || 'Unknown Period'}
            </span>
            {isLast && (
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                Current
              </span>
            )}
            {isNew && (
              <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 rounded-full animate-pulse">
                Just received
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {snapshot.confidence && (
              <span className="text-xs text-gray-500">
                {Math.round(snapshot.confidence * 100)}% confidence
              </span>
            )}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </button>

        {/* Expanded content */}
        {isExpanded && (
          <div className="px-4 pb-4 space-y-4 animate-fadeIn">
            {/* Answer */}
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>
                {showFullAnswers 
                  ? (snapshot.answer || 'No answer available')
                  : ((snapshot.answer || '').slice(0, 800) + ((snapshot.answer || '').length > 800 ? '...' : ''))}
              </ReactMarkdown>
            </div>

            {/* Sources */}
            {snapshot.sources && snapshot.sources.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {snapshot.sources.map((source, i) => (
                  <span key={i} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                    📊 {source}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ============== Main Component ==============

export const StreamingTimeTravelTimeline: React.FC<StreamingTimeTravelTimelineProps> = ({
  result,
  isStreaming,
  progress,
  question,
  showFullAnswers = true,
  onCancel,
}) => {
  const [showNarrative, setShowNarrative] = useState(true);
  const [showInsights, setShowInsights] = useState(true);
  const [showTiming, setShowTiming] = useState(false);
  const [seenSnapshots, setSeenSnapshots] = useState<Set<number>>(new Set());

  // Safe access to snapshots array and sort chronologically by date
  const rawSnapshots = result?.snapshots ?? [];
  const snapshots = [...rawSnapshots].sort((a, b) => {
    const dateA = a.date ? new Date(a.date).getTime() : 0;
    const dateB = b.date ? new Date(b.date).getTime() : 0;
    return dateA - dateB;
  });
  const keyChanges = result?.keyChanges ?? [];
  const insights = result?.insights ?? [];
  const timing = result?.timing ?? [];

  // Track which snapshots are new
  useEffect(() => {
    const timer = setTimeout(() => {
      setSeenSnapshots(new Set(snapshots.map((_, i) => i)));
    }, 2000);
    return () => clearTimeout(timer);
  }, [snapshots.length]);

  // Expected total snapshots (estimate from classification or default 4)
  const expectedSnapshots = result?.classification?.num_snapshots ?? 4;
  const pendingSnapshots = Math.max(0, expectedSnapshots - snapshots.length);

  // Time calculation
  const elapsedSeconds = result.totalTimeMs / 1000;

  return (
    <div className="space-y-6">
      {/* Header with progress */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl p-6 border border-purple-200 dark:border-purple-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              isStreaming 
                ? 'bg-blue-100 dark:bg-blue-900/30 animate-pulse' 
                : 'bg-purple-100 dark:bg-purple-900/30'
            }`}>
              {isStreaming ? (
                <Loader2 className="w-6 h-6 text-blue-600 dark:text-blue-400 animate-spin" />
              ) : (
                <Clock className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              )}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Time-Travel Answers
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {isStreaming 
                  ? `Receiving results... ${snapshots.length}/${expectedSnapshots} snapshots`
                  : 'See how the answer evolved over time'
                }
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <StatusBadge 
              isStreaming={isStreaming} 
              isComplete={result.isComplete}
              error={result.error}
            />
            {isStreaming && onCancel && (
              <button
                onClick={onCancel}
                className="px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-4">
          <ProgressBar progress={progress} isStreaming={isStreaming} />
          <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
            <span>
              {isStreaming ? 'Streaming results...' : result.isComplete ? 'Complete' : 'Ready'}
            </span>
            <span>{progress}%</span>
          </div>
        </div>
        
        {question && (
          <p className="text-sm text-gray-700 dark:text-gray-300">
            <span className="font-medium">Question:</span> {question}
          </p>
        )}

        {/* Classification info */}
        {result.classification && (
          <div className="mt-3 flex flex-wrap gap-2">
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
              result.classification.is_temporal 
                ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
                : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
            }`}>
              {result.classification.is_temporal ? '⏰ Temporal Question' : 'Static Question'}
            </span>
            {result.classification.temporal_scope && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                📊 {result.classification.temporal_scope}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Error display */}
      {result.error && (
        <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-4 border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <h4 className="font-medium text-red-800 dark:text-red-400">Error</h4>
              <p className="text-sm text-red-600 dark:text-red-300">{result.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Timeline View */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-500" />
            Timeline View
          </h3>
          <div className="text-sm text-gray-500">
            {snapshots.length}/{expectedSnapshots} snapshots
            {isStreaming && <Loader2 className="inline w-4 h-4 ml-2 animate-spin" />}
          </div>
        </div>

        <div className="p-6">
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-500 via-purple-500 to-pink-500" />

            {/* Received snapshots */}
            <div className="space-y-6">
              {snapshots.map((snapshot, index) => (
                <SnapshotCard
                  key={`${snapshot.date_label || snapshot.time_period || index}`}
                  snapshot={snapshot}
                  index={index}
                  isLast={index === snapshots.length - 1 && !isStreaming}
                  isNew={!seenSnapshots.has(index)}
                  showFullAnswers={showFullAnswers}
                />
              ))}

              {/* Skeleton placeholders for pending snapshots */}
              {isStreaming && pendingSnapshots > 0 && (
                <>
                  {Array.from({ length: Math.min(pendingSnapshots, 2) }).map((_, i) => (
                    <SnapshotSkeleton key={`skeleton-${i}`} index={snapshots.length + i} />
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Key Changes */}
      {keyChanges.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-xl p-4 border border-yellow-200 dark:border-yellow-800">
          <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-400 mb-3 flex items-center gap-2">
            <ArrowRight className="w-4 h-4" />
            Key Changes Identified
          </h4>
          <ul className="space-y-2">
            {keyChanges.map((change, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-yellow-700 dark:text-yellow-300">
                <span className={`flex-shrink-0 px-1.5 py-0.5 text-xs rounded ${
                  change.significance === 'high' 
                    ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    : change.significance === 'medium'
                      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                }`}>
                  {change.period}
                </span>
                {change.change}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Narrative */}
      {result.narrative && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button
            onClick={() => setShowNarrative(!showNarrative)}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-500" />
              🔄 Evolution Summary
            </h3>
            {showNarrative ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {showNarrative && (
            <div className="px-6 pb-6">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <p className="text-gray-700 dark:text-gray-300">{result.narrative}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Insights */}
      {insights.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button
            onClick={() => setShowInsights(!showInsights)}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-500" />
              💡 Key Insights ({insights.length})
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
                {insights.map((insight, index) => (
                  <li key={index} className="flex items-start gap-3 animate-fadeIn">
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

      {/* Timing breakdown */}
      {timing.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button
            onClick={() => setShowTiming(!showTiming)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
          >
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
              ⏱️ Timing Breakdown
            </span>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">
                Total: {elapsedSeconds.toFixed(1)}s
              </span>
              {showTiming ? (
                <ChevronUp className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              )}
            </div>
          </button>
          
          {showTiming && (
            <div className="px-4 pb-4 space-y-2">
              {timing.map((stage, index) => (
                <div key={index} className="flex items-center gap-3">
                  <div className="w-32 text-xs text-gray-500 truncate">{stage.stage}</div>
                  <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${stage.percentage}%` }}
                    />
                  </div>
                  <div className="w-16 text-right text-xs text-gray-500">
                    {(stage.duration_ms / 1000).toFixed(1)}s
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Status summary */}
      {!isStreaming && result?.isComplete && (
        <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-4 border border-green-200 dark:border-green-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Stream complete</span>
            </div>
            <span className="text-sm text-green-600 dark:text-green-300">
              {snapshots.length} snapshots • {elapsedSeconds.toFixed(1)}s total
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

// Add CSS animations to globals.css
// @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
// @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
// .animate-slideIn { animation: slideIn 0.3s ease-out; }
// .animate-fadeIn { animation: fadeIn 0.3s ease-out; }

export default StreamingTimeTravelTimeline;
