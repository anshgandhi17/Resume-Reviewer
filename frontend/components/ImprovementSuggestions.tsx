'use client';

import { ImprovementSuggestion } from '@/lib/api';

interface ImprovementSuggestionsProps {
  suggestions: ImprovementSuggestion[];
}

export default function ImprovementSuggestions({ suggestions }: ImprovementSuggestionsProps) {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300';
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-300';
      case 'low':
        return 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300';
      default:
        return 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-300';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        );
      case 'medium':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
        );
    }
  };

  // Group by priority
  const groupedSuggestions = {
    high: suggestions.filter((s) => s.priority === 'high'),
    medium: suggestions.filter((s) => s.priority === 'medium'),
    low: suggestions.filter((s) => s.priority === 'low'),
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        Improvement Suggestions
      </h3>

      {suggestions.length === 0 ? (
        <p className="text-slate-600 dark:text-slate-400">No suggestions available.</p>
      ) : (
        <div className="space-y-4">
          {['high', 'medium', 'low'].map((priority) => {
            const items = groupedSuggestions[priority as keyof typeof groupedSuggestions];
            if (items.length === 0) return null;

            return (
              <div key={priority}>
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 uppercase">
                  {priority} Priority ({items.length})
                </h4>
                <div className="space-y-3">
                  {items.map((suggestion, index) => (
                    <div
                      key={index}
                      className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start space-x-3">
                        <div className={`p-2 rounded-lg ${getPriorityColor(suggestion.priority)}`}>
                          {getPriorityIcon(suggestion.priority)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">
                              {suggestion.section}
                            </span>
                            <span
                              className={`text-xs font-medium px-2 py-1 rounded-full ${getPriorityColor(
                                suggestion.priority
                              )}`}
                            >
                              {suggestion.priority}
                            </span>
                          </div>
                          <p className="text-sm text-slate-900 dark:text-white leading-relaxed">
                            {suggestion.suggestion}
                          </p>
                          {suggestion.original && (
                            <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded border-l-4 border-slate-300 dark:border-slate-600">
                              <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                                Current:
                              </p>
                              <p className="text-sm text-slate-700 dark:text-slate-300 italic">
                                {suggestion.original}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
