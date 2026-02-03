import { useCallback, useRef, useState } from 'react';

export type SSEEventType =
  | 'step_start'
  | 'step_progress'
  | 'step_complete'
  | 'user_action_required'
  | 'phase_complete'
  | 'error'
  | 'complete';

export interface SSEEvent {
  type: SSEEventType;
  step?: string;
  message?: string;
  output?: string;
  error?: string;
  action?: string;
  options?: string[];
  phase?: number;
  summary?: string;
  mechanism?: string;
  critique?: string;
  critic_status?: string;
  iteration?: number;
  final_report?: string;
  quality_score?: number;
  quality_category?: string;
  quality_assessment?: {
    clarity_score?: number;
    feasibility_score?: number;
    novelty_score?: number;
    rigor_score?: number;
    overall_score?: number;
    justification?: string;
    verdict?: string;
  };
}

interface UseSSEOptions {
  onEvent?: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

export function useSSE(options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback((url: string) => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);
        options.onEvent?.(data);

        if (data.type === 'complete') {
          eventSource.close();
          setIsConnected(false);
          options.onComplete?.();
        }
      } catch (e) {
        console.error('Failed to parse SSE event:', e);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      setIsConnected(false);
      options.onError?.(new Error('SSE connection error'));
      eventSource.close();
    };

    return eventSource;
  }, [options]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    connect,
    disconnect,
    isConnected,
    events,
    clearEvents,
  };
}
