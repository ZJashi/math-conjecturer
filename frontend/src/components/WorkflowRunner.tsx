import { useState, useCallback, useEffect } from 'react';
import { Play, Square, ArrowRight, SkipForward } from 'lucide-react';
import { useSSE, SSEEvent } from '../hooks/useSSE';
import { StepProgress, Step } from './StepProgress';
import { OutputDisplay } from './OutputDisplay';

const API_BASE = '';

const PHASE1_STEPS: Step[] = [
  { id: 'ingest', name: 'Download & Process Paper', status: 'pending' },
  { id: 'summarize', name: 'Generate Summary', status: 'pending' },
  { id: 'critic', name: 'Critic Evaluation', status: 'pending' },
  { id: 'revision', name: 'Revision (if needed)', status: 'pending' },
  { id: 'mechanism', name: 'Extract Mechanism', status: 'pending' },
];

const PHASE2_STEPS: Step[] = [
  { id: 'context_ingestion', name: 'Context Ingestion', status: 'pending' },
  { id: 'agenda_creator', name: 'Create Research Agenda', status: 'pending' },
  { id: 'brainstormer', name: 'Generate Proposal', status: 'pending' },
  { id: 'critics', name: 'Parallel Critics', status: 'pending' },
  { id: 'feedback', name: 'Consolidate Feedback', status: 'pending' },
  { id: 'report', name: 'Generate Report', status: 'pending' },
  { id: 'quality', name: 'Quality Assessment', status: 'pending' },
];

interface WorkflowState {
  jobId: string | null;
  phase: number;
  iteration: number;
  summary: string;
  critique: string;
  criticStatus: string;
  mechanism: string;
  finalReport: string;
  qualityScore?: number;
  qualityCategory?: string;
  qualityAssessment?: SSEEvent['quality_assessment'];
  pendingAction: {
    action: string;
    options: string[];
    message: string;
  } | null;
  isComplete: boolean;
  error: string | null;
}

export function WorkflowRunner() {
  const [arxivId, setArxivId] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [steps, setSteps] = useState<Step[]>(PHASE1_STEPS);
  const [state, setState] = useState<WorkflowState>({
    jobId: null,
    phase: 1,
    iteration: 1,
    summary: '',
    critique: '',
    criticStatus: '',
    mechanism: '',
    finalReport: '',
    pendingAction: null,
    isComplete: false,
    error: null,
  });

  const handleEvent = useCallback((event: SSEEvent) => {
    console.log('SSE Event:', event);

    switch (event.type) {
      case 'step_start':
        setSteps((prev) =>
          prev.map((s) =>
            s.id === event.step
              ? { ...s, status: 'running', message: event.message }
              : s
          )
        );
        break;

      case 'step_progress':
        setSteps((prev) =>
          prev.map((s) =>
            s.id === event.step ? { ...s, message: event.message } : s
          )
        );
        break;

      case 'step_complete':
        setSteps((prev) =>
          prev.map((s) =>
            s.id === event.step
              ? { ...s, status: 'complete', message: event.message }
              : s
          )
        );

        // Update state based on step output
        if (event.step === 'summarize' && event.output) {
          setState((prev) => ({ ...prev, summary: event.output! }));
        }
        if (event.step === 'critic' && event.output) {
          setState((prev) => ({ ...prev, critique: event.output! }));
        }
        if (event.step === 'mechanism' && event.output) {
          setState((prev) => ({ ...prev, mechanism: event.output! }));
        }
        break;

      case 'phase_complete':
        if (event.summary) {
          setState((prev) => ({ ...prev, summary: event.summary! }));
        }
        if (event.mechanism) {
          setState((prev) => ({ ...prev, mechanism: event.mechanism! }));
        }
        if (event.critique) {
          setState((prev) => ({ ...prev, critique: event.critique! }));
        }
        if (event.critic_status) {
          setState((prev) => ({ ...prev, criticStatus: event.critic_status! }));
        }
        if (event.iteration) {
          setState((prev) => ({ ...prev, iteration: event.iteration! }));
        }
        if (event.phase === 2) {
          setState((prev) => ({ ...prev, phase: 2 }));
          setSteps(PHASE2_STEPS);
        }
        break;

      case 'user_action_required':
        setState((prev) => ({
          ...prev,
          pendingAction: {
            action: event.action!,
            options: event.options!,
            message: event.message!,
          },
        }));
        break;

      case 'error':
        setState((prev) => ({ ...prev, error: event.error || 'Unknown error' }));
        setSteps((prev) =>
          prev.map((s) =>
            s.id === event.step ? { ...s, status: 'error' } : s
          )
        );
        setIsRunning(false);
        break;

      case 'complete':
        setState((prev) => ({
          ...prev,
          isComplete: true,
          finalReport: event.final_report || prev.finalReport,
          qualityScore: event.quality_score,
          qualityCategory: event.quality_category,
          qualityAssessment: event.quality_assessment,
        }));
        setIsRunning(false);
        break;
    }
  }, []);

  const { connect, disconnect, isConnected, clearEvents } = useSSE({
    onEvent: handleEvent,
    onComplete: () => setIsRunning(false),
    onError: (error) => {
      setState((prev) => ({ ...prev, error: error.message }));
      setIsRunning(false);
    },
  });

  const startWorkflow = async () => {
    if (!arxivId.trim()) return;

    // Reset state
    setState({
      jobId: null,
      phase: 1,
      iteration: 1,
      summary: '',
      critique: '',
      criticStatus: '',
      mechanism: '',
      finalReport: '',
      pendingAction: null,
      isComplete: false,
      error: null,
    });
    setSteps(PHASE1_STEPS.map((s) => ({ ...s, status: 'pending', message: undefined })));
    clearEvents();

    setIsRunning(true);

    try {
      const response = await fetch(`${API_BASE}/api/workflow/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arxiv_id: arxivId.trim() }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start workflow: ${response.statusText}`);
      }

      const data = await response.json();
      setState((prev) => ({ ...prev, jobId: data.job_id }));
      connect(`${API_BASE}${data.stream_url}`);
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
      setIsRunning(false);
    }
  };

  const sendAction = async (action: string) => {
    if (!state.jobId) return;

    setState((prev) => ({ ...prev, pendingAction: null }));

    try {
      await fetch(`${API_BASE}/api/workflow/${state.jobId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
    } catch (error) {
      console.error('Failed to send action:', error);
    }
  };

  const stopWorkflow = () => {
    disconnect();
    setIsRunning(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-gray-900">Math Conjecturer</h1>
          <p className="text-sm text-gray-500 mt-1">
            Analyze arXiv papers and generate research proposals
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Input Section */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label
                htmlFor="arxiv-id"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                arXiv Paper ID
              </label>
              <input
                id="arxiv-id"
                type="text"
                value={arxivId}
                onChange={(e) => setArxivId(e.target.value)}
                placeholder="e.g., 2301.12345"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                disabled={isRunning}
              />
            </div>
            {!isRunning ? (
              <button
                onClick={startWorkflow}
                disabled={!arxivId.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-4 h-4" />
                Start Analysis
              </button>
            ) : (
              <button
                onClick={stopWorkflow}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                <Square className="w-4 h-4" />
                Stop
              </button>
            )}
          </div>
        </div>

        {/* Error Display */}
        {state.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800 font-medium">Error</p>
            <p className="text-red-600">{state.error}</p>
          </div>
        )}

        {/* User Action Required */}
        {state.pendingAction && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
            <p className="text-amber-800 font-medium mb-2">Action Required</p>
            <p className="text-amber-700 mb-4">{state.pendingAction.message}</p>
            <div className="flex gap-3">
              {state.pendingAction.action === 'refinement_decision' && (
                <>
                  <button
                    onClick={() => sendAction('continue')}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    <ArrowRight className="w-4 h-4" />
                    Continue Refinement
                  </button>
                  <button
                    onClick={() => sendAction('stop')}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                  >
                    <SkipForward className="w-4 h-4" />
                    Accept Current
                  </button>
                </>
              )}
              {state.pendingAction.action === 'phase2_decision' && (
                <>
                  <button
                    onClick={() => sendAction('start_phase2')}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                  >
                    <Play className="w-4 h-4" />
                    Start Phase 2
                  </button>
                  <button
                    onClick={() => sendAction('skip_phase2')}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                  >
                    <SkipForward className="w-4 h-4" />
                    Skip Phase 2
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Progress */}
          <div className="lg:col-span-1">
            <StepProgress steps={steps} currentPhase={state.phase} />

            {/* Connection Status */}
            <div className="mt-4 text-sm text-gray-500">
              {isConnected ? (
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  Connected
                </span>
              ) : isRunning ? (
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
                  Connecting...
                </span>
              ) : null}
            </div>
          </div>

          {/* Right Column: Output */}
          <div className="lg:col-span-2">
            {(state.summary || state.critique || state.mechanism || state.finalReport) ? (
              <OutputDisplay
                summary={state.summary}
                critique={state.critique}
                criticStatus={state.criticStatus}
                mechanism={state.mechanism}
                finalReport={state.finalReport}
                qualityScore={state.qualityScore}
                qualityCategory={state.qualityCategory}
                qualityAssessment={state.qualityAssessment}
                phase={state.phase}
                iteration={state.iteration}
              />
            ) : (
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                <p>Enter an arXiv paper ID and click "Start Analysis" to begin.</p>
                <p className="text-sm mt-2">
                  Example: <code className="bg-gray-100 px-2 py-1 rounded">2301.12345</code>
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Completion Message */}
        {state.isComplete && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800 font-medium">Workflow Complete!</p>
            <p className="text-green-600">
              Files have been saved to <code>papers/{arxivId}/</code>
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
