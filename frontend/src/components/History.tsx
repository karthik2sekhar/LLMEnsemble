/**
 * History Component
 * Displays the history of previous questions with the ability to load or delete them.
 */

import React, { useState } from 'react';
import { History, Trash2, Clock, Coins, ChevronRight, X } from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import { HistoryItem } from '@/hooks/useEnsembleLLM';

interface HistoryPanelProps {
  history: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
  onDelete: (id: string) => void;
  onClear: () => void;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  history,
  onSelect,
  onDelete,
  onClear,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (history.length === 0) {
    return null;
  }

  const formatCost = (cost: number): string => {
    return `$${cost.toFixed(4)}`;
  };

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed right-4 bottom-4 z-40 flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full shadow-lg hover:shadow-xl transition-all"
      >
        <History className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          History ({history.length})
        </span>
      </button>

      {/* Slide-out panel */}
      <div
        className={clsx(
          'fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white dark:bg-gray-900 shadow-2xl transform transition-transform duration-300',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Panel header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Query History
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClear}
              className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              Clear all
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* History list */}
        <div className="overflow-y-auto h-[calc(100vh-73px)]">
          {history.map((item) => (
            <div
              key={item.id}
              className="group px-6 py-4 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                {/* Content */}
                <button
                  onClick={() => {
                    onSelect(item);
                    setIsOpen(false);
                  }}
                  className="flex-1 text-left"
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
                    {item.question}
                  </p>
                  <div className="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(item.timestamp), { addSuffix: true })}
                    </span>
                    <span className="flex items-center gap-1">
                      <Coins className="w-3 h-3" />
                      {formatCost(item.totalCost)}
                    </span>
                    <span className="text-gray-400">
                      {item.models.length} models
                    </span>
                  </div>
                </button>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => onDelete(item.id)}
                    className="p-2 opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                  <button
                    onClick={() => {
                      onSelect(item);
                      setIsOpen(false);
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    title="Load"
                  >
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 dark:bg-black/40 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
};

export default HistoryPanel;
