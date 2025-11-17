'use client';

import { ComparisonHighlight } from '@/lib/api';

interface ComparisonViewProps {
  comparisons: ComparisonHighlight[];
}

export default function ComparisonView({ comparisons }: ComparisonViewProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'matched':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300">
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            Matched
          </span>
        );
      case 'partial':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-300">
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                clipRule="evenodd"
              />
            </svg>
            Partial
          </span>
        );
      case 'missing':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300">
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            Missing
          </span>
        );
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'matched':
        return 'border-l-green-500 bg-green-50 dark:bg-green-900/10';
      case 'partial':
        return 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/10';
      case 'missing':
        return 'border-l-red-500 bg-red-50 dark:bg-red-900/10';
      default:
        return 'border-l-slate-300 bg-slate-50 dark:bg-slate-700/50';
    }
  };

  // Group by status
  const grouped = {
    matched: comparisons.filter((c) => c.status === 'matched'),
    partial: comparisons.filter((c) => c.status === 'partial'),
    missing: comparisons.filter((c) => c.status === 'missing'),
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        Requirement Comparison
      </h3>

      {comparisons.length === 0 ? (
        <p className="text-slate-600 dark:text-slate-400">No comparison data available.</p>
      ) : (
        <div className="space-y-6">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-green-50 dark:bg-green-900/10 rounded-lg border border-green-200 dark:border-green-800">
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                {grouped.matched.length}
              </p>
              <p className="text-xs text-green-700 dark:text-green-300 mt-1">Matched</p>
            </div>
            <div className="text-center p-4 bg-yellow-50 dark:bg-yellow-900/10 rounded-lg border border-yellow-200 dark:border-yellow-800">
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                {grouped.partial.length}
              </p>
              <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">Partial</p>
            </div>
            <div className="text-center p-4 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-200 dark:border-red-800">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {grouped.missing.length}
              </p>
              <p className="text-xs text-red-700 dark:text-red-300 mt-1">Missing</p>
            </div>
          </div>

          {/* Requirements List */}
          <div className="space-y-3">
            {comparisons.map((comparison, index) => (
              <div
                key={index}
                className={`border-l-4 rounded-lg p-4 ${getStatusColor(comparison.status)}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="text-sm font-medium text-slate-900 dark:text-white flex-1">
                    {comparison.requirement}
                  </h4>
                  {getStatusBadge(comparison.status)}
                </div>

                {comparison.resume_evidence && (
                  <div className="mt-3 p-3 bg-white dark:bg-slate-700 rounded border border-slate-200 dark:border-slate-600">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                      Evidence from your resume:
                    </p>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {comparison.resume_evidence}
                    </p>
                  </div>
                )}

                {comparison.status === 'missing' && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-2 italic">
                    Consider adding information about this requirement to strengthen your application.
                  </p>
                )}

                {comparison.status === 'partial' && (
                  <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-2 italic">
                    Try to provide more specific details or examples for this requirement.
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
