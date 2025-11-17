'use client';

import { AnalysisResult } from '@/lib/api';

interface MatchAnalysisProps {
  result: AnalysisResult;
}

export default function MatchAnalysis({ result }: MatchAnalysisProps) {
  const { match_analysis } = result;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-100 dark:bg-green-900/20';
    if (score >= 60) return 'bg-yellow-100 dark:bg-yellow-900/20';
    return 'bg-red-100 dark:bg-red-900/20';
  };

  return (
    <div className="space-y-6">
      {/* Overall Scores */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                Overall Match Score
              </p>
              <p className={`text-4xl font-bold mt-2 ${getScoreColor(match_analysis.overall_score)}`}>
                {match_analysis.overall_score.toFixed(0)}%
              </p>
            </div>
            <div className={`w-20 h-20 rounded-full ${getScoreBgColor(match_analysis.overall_score)} flex items-center justify-center`}>
              <svg
                className={`w-10 h-10 ${getScoreColor(match_analysis.overall_score)}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                ATS Friendliness
              </p>
              <p className={`text-4xl font-bold mt-2 ${getScoreColor(match_analysis.ats_score)}`}>
                {match_analysis.ats_score.toFixed(0)}%
              </p>
            </div>
            <div className={`w-20 h-20 rounded-full ${getScoreBgColor(match_analysis.ats_score)} flex items-center justify-center`}>
              <svg
                className={`w-10 h-10 ${getScoreColor(match_analysis.ats_score)}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Skills Breakdown */}
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Skills Analysis
        </h3>

        <div className="space-y-4">
          {/* Matched Skills */}
          {match_analysis.skills.matched.length > 0 && (
            <div>
              <div className="flex items-center mb-2">
                <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Matched Skills ({match_analysis.skills.matched.length})
                </h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {match_analysis.skills.matched.map((skill, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300 text-sm rounded-full"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Missing Skills */}
          {match_analysis.skills.missing.length > 0 && (
            <div>
              <div className="flex items-center mb-2">
                <span className="w-3 h-3 bg-red-500 rounded-full mr-2"></span>
                <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Missing Skills ({match_analysis.skills.missing.length})
                </h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {match_analysis.skills.missing.map((skill, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300 text-sm rounded-full"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Transferable Skills */}
          {match_analysis.skills.transferable.length > 0 && (
            <div>
              <div className="flex items-center mb-2">
                <span className="w-3 h-3 bg-blue-500 rounded-full mr-2"></span>
                <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Transferable Skills ({match_analysis.skills.transferable.length})
                </h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {match_analysis.skills.transferable.map((skill, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 text-sm rounded-full"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Similar Resumes */}
      {result.similar_resumes && result.similar_resumes.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Similar Successful Resumes
          </h3>
          <div className="space-y-3">
            {result.similar_resumes.map((resume, index) => (
              <div
                key={resume.id}
                className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/20 rounded-full flex items-center justify-center">
                    <span className="text-primary-600 dark:text-primary-400 font-medium">
                      #{index + 1}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">
                      {resume.metadata?.job_title || 'Resume'}
                    </p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {resume.metadata?.filename}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    Similarity
                  </p>
                  <p className="text-lg font-bold text-primary-600 dark:text-primary-400">
                    {(resume.similarity * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
