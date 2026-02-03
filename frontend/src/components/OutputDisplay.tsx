import ReactMarkdown from 'react-markdown';
import { FileText, Code, Award } from 'lucide-react';

interface OutputDisplayProps {
  summary?: string;
  critique?: string;
  criticStatus?: string;
  mechanism?: string;
  finalReport?: string;
  qualityScore?: number;
  qualityCategory?: string;
  qualityAssessment?: {
    clarity_score?: number;
    feasibility_score?: number;
    novelty_score?: number;
    rigor_score?: number;
    overall_score?: number;
    justification?: string;
    verdict?: string;
  };
  phase: number;
  iteration?: number;
}

export function OutputDisplay({
  summary,
  critique,
  criticStatus,
  mechanism,
  finalReport,
  qualityScore,
  qualityCategory,
  qualityAssessment,
  phase,
  iteration,
}: OutputDisplayProps) {
  return (
    <div className="space-y-6">
      {/* Summary Section */}
      {summary && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="bg-blue-50 px-4 py-3 border-b border-blue-100 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-blue-900">
              Summary {iteration && iteration > 1 ? `(Iteration ${iteration})` : ''}
            </h3>
          </div>
          <div className="p-4 prose prose-sm max-w-none">
            <ReactMarkdown>{summary}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Critique Section */}
      {critique && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div
            className={`px-4 py-3 border-b flex items-center justify-between ${
              criticStatus === 'PASS'
                ? 'bg-green-50 border-green-100'
                : 'bg-yellow-50 border-yellow-100'
            }`}
          >
            <div className="flex items-center gap-2">
              <Award
                className={`w-5 h-5 ${
                  criticStatus === 'PASS' ? 'text-green-600' : 'text-yellow-600'
                }`}
              />
              <h3
                className={`font-semibold ${
                  criticStatus === 'PASS' ? 'text-green-900' : 'text-yellow-900'
                }`}
              >
                Critic Evaluation
              </h3>
            </div>
            <span
              className={`px-2 py-1 rounded text-sm font-medium ${
                criticStatus === 'PASS'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {criticStatus}
            </span>
          </div>
          <div className="p-4 prose prose-sm max-w-none">
            <ReactMarkdown>{critique}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Mechanism Section */}
      {mechanism && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="bg-purple-50 px-4 py-3 border-b border-purple-100 flex items-center gap-2">
            <Code className="w-5 h-5 text-purple-600" />
            <h3 className="font-semibold text-purple-900">Mechanism Graph (XML)</h3>
          </div>
          <div className="p-4">
            <pre className="xml-output whitespace-pre-wrap">{mechanism}</pre>
          </div>
        </div>
      )}

      {/* Final Report (Phase 2) */}
      {finalReport && phase === 2 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="bg-indigo-50 px-4 py-3 border-b border-indigo-100 flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-600" />
            <h3 className="font-semibold text-indigo-900">Final Research Proposal</h3>
          </div>
          <div className="p-4 prose prose-sm max-w-none">
            <ReactMarkdown>{finalReport}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Quality Assessment */}
      {qualityScore !== undefined && qualityAssessment && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="bg-amber-50 px-4 py-3 border-b border-amber-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-600" />
              <h3 className="font-semibold text-amber-900">Quality Assessment</h3>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-3 py-1 rounded-full text-sm font-bold ${
                  qualityCategory === 'excellent'
                    ? 'bg-green-100 text-green-800'
                    : qualityCategory === 'good'
                    ? 'bg-blue-100 text-blue-800'
                    : qualityCategory === 'acceptable'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                {qualityScore.toFixed(1)}/100
              </span>
              <span className="text-sm font-medium text-gray-600 capitalize">
                {qualityCategory}
              </span>
            </div>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              {[
                { label: 'Clarity', value: qualityAssessment.clarity_score },
                { label: 'Feasibility', value: qualityAssessment.feasibility_score },
                { label: 'Novelty', value: qualityAssessment.novelty_score },
                { label: 'Rigor', value: qualityAssessment.rigor_score },
              ].map((item) => (
                <div
                  key={item.label}
                  className="bg-gray-50 rounded-lg p-3 text-center"
                >
                  <div className="text-2xl font-bold text-gray-900">
                    {item.value}/10
                  </div>
                  <div className="text-sm text-gray-500">{item.label}</div>
                </div>
              ))}
            </div>
            {qualityAssessment.justification && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 font-medium mb-1">
                  Justification
                </p>
                <p className="text-gray-700">{qualityAssessment.justification}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
