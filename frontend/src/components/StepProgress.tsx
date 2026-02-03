import { CheckCircle, Circle, Loader2, AlertCircle } from 'lucide-react';

export interface Step {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  message?: string;
}

interface StepProgressProps {
  steps: Step[];
  currentPhase: number;
}

export function StepProgress({ steps, currentPhase }: StepProgressProps) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">
        Phase {currentPhase} Progress
      </h3>
      <div className="space-y-3">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-3">
            <div className="flex-shrink-0 mt-0.5">
              {step.status === 'pending' && (
                <Circle className="w-5 h-5 text-gray-300" />
              )}
              {step.status === 'running' && (
                <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
              )}
              {step.status === 'complete' && (
                <CheckCircle className="w-5 h-5 text-green-500" />
              )}
              {step.status === 'error' && (
                <AlertCircle className="w-5 h-5 text-red-500" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p
                className={`font-medium ${
                  step.status === 'running'
                    ? 'text-blue-600'
                    : step.status === 'complete'
                    ? 'text-green-600'
                    : step.status === 'error'
                    ? 'text-red-600'
                    : 'text-gray-400'
                }`}
              >
                {step.name}
              </p>
              {step.message && (
                <p className="text-sm text-gray-500 truncate">{step.message}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
