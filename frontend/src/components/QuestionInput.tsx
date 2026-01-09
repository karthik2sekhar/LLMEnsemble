/**
 * QuestionInput Component
 * Large text input area for entering questions with character counter and keyboard shortcuts.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import clsx from 'clsx';

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  maxLength?: number;
  placeholder?: string;
  initialValue?: string;
}

export const QuestionInput: React.FC<QuestionInputProps> = ({
  onSubmit,
  isLoading,
  maxLength = 5000,
  placeholder = 'Ask a question to get responses from multiple AI models...',
  initialValue = '',
}) => {
  const [question, setQuestion] = useState(initialValue);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus textarea on mount
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  // Handle form submission
  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmedQuestion = question.trim();
    if (trimmedQuestion && !isLoading) {
      onSubmit(trimmedQuestion);
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Cmd/Ctrl + Enter to submit
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  const characterCount = question.length;
  const isOverLimit = characterCount > maxLength;
  const isValid = question.trim().length > 0 && !isOverLimit;

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          className={clsx(
            'w-full min-h-[150px] p-4 pr-12 rounded-xl border-2 resize-y',
            'bg-white dark:bg-gray-800',
            'text-gray-900 dark:text-gray-100',
            'placeholder-gray-400 dark:placeholder-gray-500',
            'transition-all duration-200',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            isOverLimit
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-200 dark:border-gray-700',
            isLoading && 'opacity-50 cursor-not-allowed'
          )}
          aria-label="Question input"
          aria-invalid={isOverLimit}
        />
        
        {/* Submit button inside textarea */}
        <button
          type="submit"
          disabled={!isValid || isLoading}
          className={clsx(
            'absolute bottom-4 right-4 p-2 rounded-lg',
            'transition-all duration-200',
            isValid && !isLoading
              ? 'bg-primary-600 hover:bg-primary-700 text-white cursor-pointer'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
          )}
          title="Submit (Ctrl+Enter)"
          aria-label="Submit question"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Character counter and hint */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          Press <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">Ctrl</kbd>
          {' + '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">Enter</kbd>
          {' to submit'}
        </span>
        <span
          className={clsx(
            'font-mono transition-colors',
            isOverLimit ? 'text-red-500 font-semibold' : 'text-gray-400 dark:text-gray-500'
          )}
        >
          {characterCount.toLocaleString()} / {maxLength.toLocaleString()}
        </span>
      </div>
    </form>
  );
};

export default QuestionInput;
