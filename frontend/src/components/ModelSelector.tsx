/**
 * ModelSelector Component
 * Checkbox-based model selection with tooltips showing model capabilities.
 */

import React from 'react';
import { Info, Check } from 'lucide-react';
import clsx from 'clsx';
import { ModelInfo } from '@/services/api';

interface ModelSelectorProps {
  models: ModelInfo[];
  selectedModels: string[];
  onSelectionChange: (models: string[]) => void;
  disabled?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  models,
  selectedModels,
  onSelectionChange,
  disabled = false,
}) => {
  const handleToggle = (modelId: string) => {
    if (disabled) return;
    
    if (selectedModels.includes(modelId)) {
      // Don't allow deselecting all models
      if (selectedModels.length > 1) {
        onSelectionChange(selectedModels.filter((id) => id !== modelId));
      }
    } else {
      onSelectionChange([...selectedModels, modelId]);
    }
  };

  const selectAll = () => {
    if (!disabled) {
      onSelectionChange(models.map((m) => m.id));
    }
  };

  const formatCost = (cost: number): string => {
    if (cost < 0.001) {
      return `$${(cost * 1000).toFixed(3)}/1M`;
    }
    return `$${cost.toFixed(4)}/1K`;
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Select Models
        </h3>
        <button
          onClick={selectAll}
          disabled={disabled}
          className={clsx(
            'text-xs text-primary-600 dark:text-primary-400 hover:underline',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          Select all
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {models.map((model) => {
          const isSelected = selectedModels.includes(model.id);
          
          return (
            <div
              key={model.id}
              onClick={() => handleToggle(model.id)}
              className={clsx(
                'relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-200',
                isSelected
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
              role="checkbox"
              aria-checked={isSelected}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleToggle(model.id);
                }
              }}
            >
              {/* Checkbox indicator */}
              <div
                className={clsx(
                  'absolute top-3 right-3 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all',
                  isSelected
                    ? 'bg-primary-500 border-primary-500'
                    : 'border-gray-300 dark:border-gray-600'
                )}
              >
                {isSelected && <Check className="w-3 h-3 text-white" />}
              </div>

              {/* Model info */}
              <div className="pr-8">
                <h4 className="font-medium text-gray-900 dark:text-gray-100">
                  {model.name}
                </h4>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                  {model.description}
                </p>
                
                {/* Cost info */}
                <div className="mt-2 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                  <span className="flex items-center gap-1" title="Input cost per 1K tokens">
                    <span className="text-green-600 dark:text-green-400">↓</span>
                    {formatCost(model.cost_per_1k_input)}
                  </span>
                  <span className="flex items-center gap-1" title="Output cost per 1K tokens">
                    <span className="text-blue-600 dark:text-blue-400">↑</span>
                    {formatCost(model.cost_per_1k_output)}
                  </span>
                </div>
              </div>

              {/* Tooltip trigger */}
              <div className="absolute bottom-3 right-3 group">
                <Info className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
                <div className="absolute bottom-full right-0 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                  <p>{model.description}</p>
                  <p className="mt-1 text-gray-400">
                    Token limit: {model.token_limit.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selection summary */}
      <p className="text-xs text-gray-500 dark:text-gray-400">
        {selectedModels.length} of {models.length} models selected
      </p>
    </div>
  );
};

export default ModelSelector;
