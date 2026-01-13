/**
 * useTimeTravelStream - React hook for streaming time-travel results
 * 
 * Uses Server-Sent Events (SSE) to progressively receive time-travel
 * results as they complete, showing first result in ~8s instead of
 * waiting ~35s for all results.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

// ============== Types ==============

export type StreamEventType = 
  | 'start'
  | 'classification'
  | 'snapshot'
  | 'key_changes'
  | 'narrative'
  | 'insight'
  | 'timing'
  | 'complete'
  | 'error'
  | 'heartbeat';

export interface StreamEvent {
  type: StreamEventType;
  data: unknown;
  timestamp_ms?: number;
}

export interface Snapshot {
  time_period?: string;
  date_label?: string;
  year?: string;
  date?: string;
  answer: string;
  confidence?: number;
  sources?: string[];
  model?: string;
  tokens?: number;
  cost?: number;
  duration_ms?: number;
  success?: boolean;
}

export interface KeyChange {
  period: string;
  change: string;
  significance: 'high' | 'medium' | 'low';
}

export interface TimingBreakdown {
  stage: string;
  duration_ms: number;
  percentage: number;
}

export interface ClassificationResult {
  is_temporal: boolean;
  requires_time_travel: boolean;
  temporal_scope?: string;
  complexity?: string;
  model?: string;
  num_snapshots?: number;
  time_points?: string[];
  duration_ms?: number;
}

export interface StreamingTimeTravelResult {
  // Progressive data
  snapshots: Snapshot[];
  narrative: string | null;
  keyChanges: KeyChange[];
  insights: string[];
  timing: TimingBreakdown[];
  
  // Metadata
  classification: ClassificationResult | null;
  totalTimeMs: number;
  isComplete: boolean;
  error: string | null;
}

export interface UseTimeTravelStreamOptions {
  apiBaseUrl?: string;
  onSnapshot?: (snapshot: Snapshot) => void;
  onNarrative?: (narrative: string) => void;
  onComplete?: (result: StreamingTimeTravelResult) => void;
  onError?: (error: string) => void;
}

export interface UseTimeTravelStreamReturn {
  // State
  result: StreamingTimeTravelResult;
  isStreaming: boolean;
  progress: number; // 0-100
  
  // Actions
  startStream: (question: string, force?: boolean) => Promise<void>;
  cancelStream: () => void;
  reset: () => void;
}

// ============== Initial State ==============

const initialResult: StreamingTimeTravelResult = {
  snapshots: [],
  narrative: null,
  keyChanges: [],
  insights: [],
  timing: [],
  classification: null,
  totalTimeMs: 0,
  isComplete: false,
  error: null,
};

// ============== Hook Implementation ==============

export function useTimeTravelStream(
  options: UseTimeTravelStreamOptions = {}
): UseTimeTravelStreamReturn {
  const {
    apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    onSnapshot,
    onNarrative,
    onComplete,
    onError,
  } = options;

  const [result, setResult] = useState<StreamingTimeTravelResult>(initialResult);
  const [isStreaming, setIsStreaming] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const startTimeRef = useRef<number>(0);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const reset = useCallback(() => {
    setResult(initialResult);
    setProgress(0);
    setIsStreaming(false);
  }, []);

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const processEvent = useCallback((event: StreamEvent) => {
    // The backend sends data flattened into the event, not nested under 'data'
    // So event might be: {type: "snapshot", index: 1, snapshot: {...}}
    // Not: {type: "snapshot", data: {index: 1, snapshot: {...}}}
    const eventData = (event as any);
    
    switch (event.type) {
      case 'start':
        setProgress(5);
        break;
        
      case 'classification':
        setResult(prev => ({
          ...prev,
          classification: eventData as ClassificationResult,
        }));
        setProgress(10);
        break;
        
      case 'snapshot': {
        const snapshotData = eventData as {
          index: number;
          total: number;
          snapshot: Snapshot;
        };
        
        setResult(prev => ({
          ...prev,
          snapshots: [...prev.snapshots, snapshotData.snapshot],
        }));
        
        // Progress: snapshots are 10-70%
        const snapshotProgress = 10 + (snapshotData.index / snapshotData.total) * 60;
        setProgress(Math.round(snapshotProgress));
        
        onSnapshot?.(snapshotData.snapshot);
        break;
      }
        
      case 'key_changes': {
        const changes = eventData as { changes: KeyChange[] };
        setResult(prev => ({
          ...prev,
          keyChanges: changes.changes || [],
        }));
        setProgress(75);
        break;
      }
        
      case 'narrative': {
        const narrativeData = eventData as { narrative: string; text?: string; insights?: string[] };
        let narrativeText = narrativeData.narrative || narrativeData.text || '';
        
        // If narrative looks like JSON, try to parse it
        if (typeof narrativeText === 'string' && narrativeText.trim().startsWith('{')) {
          try {
            const parsed = JSON.parse(narrativeText);
            narrativeText = parsed.narrative || narrativeText;
            // Also extract insights if present
            if (parsed.insights && Array.isArray(parsed.insights)) {
              setResult(prev => ({
                ...prev,
                narrative: narrativeText,
                insights: parsed.insights.map((i: any) => typeof i === 'string' ? i : i.text || String(i)),
              }));
              setProgress(85);
              onNarrative?.(narrativeText);
              break;
            }
          } catch {
            // Not JSON, use as-is
          }
        }
        
        setResult(prev => ({
          ...prev,
          narrative: narrativeText,
        }));
        setProgress(85);
        onNarrative?.(narrativeText);
        break;
      }
        
      case 'insight': {
        const insightData = eventData as { index: number; insight: string; total: number };
        setResult(prev => ({
          ...prev,
          insights: [...prev.insights, insightData.insight],
        }));
        break;
      }
        
      case 'timing': {
        const timingData = eventData as {
          total_ms: number;
          breakdown: TimingBreakdown[];
        };
        setResult(prev => ({
          ...prev,
          timing: timingData.breakdown,
          totalTimeMs: timingData.total_ms,
        }));
        setProgress(95);
        break;
      }
        
      case 'complete': {
        const completeData = eventData as { success: boolean };
        setResult(prev => ({
          ...prev,
          isComplete: completeData.success ?? true,
        }));
        setProgress(100);
        break;
      }
        
      case 'error': {
        const errorMsg = eventData.error || 'Unknown error';
        setResult(prev => ({
          ...prev,
          error: errorMsg,
        }));
        onError?.(errorMsg);
        break;
      }
        
      case 'heartbeat':
        // Keep-alive, no state update needed
        break;
    }
  }, [onSnapshot, onNarrative, onError]);

  const startStream = useCallback(async (
    question: string,
    force: boolean = false
  ): Promise<void> => {
    // Cancel any existing stream
    cancelStream();
    reset();
    
    setIsStreaming(true);
    startTimeRef.current = Date.now();
    abortControllerRef.current = new AbortController();
    
    try {
      const response = await fetch(`${apiBaseUrl}/api/time-travel-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          question,
          force_time_travel: force,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        
        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6); // Remove 'data: ' prefix
            if (data.trim()) {
              try {
                const event = JSON.parse(data) as StreamEvent;
                processEvent(event);
              } catch (parseError) {
                console.warn('Failed to parse SSE event:', data, parseError);
              }
            }
          }
        }
      }

      // Calculate final time
      const totalTime = Date.now() - startTimeRef.current;
      setResult(prev => ({
        ...prev,
        totalTimeMs: prev.totalTimeMs || totalTime,
        isComplete: true,
      }));
      
      // Call onComplete with final result
      setResult(prev => {
        onComplete?.(prev);
        return prev;
      });

    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          console.log('Stream cancelled by user');
        } else {
          console.error('Stream error:', error);
          setResult(prev => ({
            ...prev,
            error: error.message,
          }));
          onError?.(error.message);
        }
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, [apiBaseUrl, cancelStream, reset, processEvent, onComplete, onError]);

  return {
    result,
    isStreaming,
    progress,
    startStream,
    cancelStream,
    reset,
  };
}

export default useTimeTravelStream;
