'use client';

import { useState } from 'react';
import FileUpload from '@/components/FileUpload';
import MatchAnalysis from '@/components/MatchAnalysis';
import ImprovementSuggestions from '@/components/ImprovementSuggestions';
import ComparisonView from '@/components/ComparisonView';
import RankedProjects from '@/components/RankedProjects';
import { AnalysisResult, ProjectRankingResponse } from '@/lib/api';

export default function Home() {
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [selectedResultIndex, setSelectedResultIndex] = useState(0);
  const [projectRanking, setProjectRanking] = useState<ProjectRankingResponse | null>(null);
  const [showProjects, setShowProjects] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [jobTitle, setJobTitle] = useState('Software Engineer');

  const handleUploadSuccess = (
    analysisResults: AnalysisResult[],
    projectRanking?: ProjectRankingResponse,
    files?: File[],
    jobTitleInput?: string
  ) => {
    setResults(analysisResults);
    setSelectedResultIndex(0);
    if (projectRanking) {
      setProjectRanking(projectRanking);
    }
    if (files) {
      setUploadedFiles(files);
    }
    if (jobTitleInput) {
      setJobTitle(jobTitleInput);
    }
  };

  const handleReset = () => {
    setResults([]);
    setSelectedResultIndex(0);
    setProjectRanking(null);
    setShowProjects(false);
  };

  const toggleView = () => {
    setShowProjects(!showProjects);
  };

  const currentResult = results.length > 0 ? results[selectedResultIndex] : null;

  return (
    <div className="container mx-auto px-4 py-8">
      {results.length === 0 && <FileUpload onUploadSuccess={handleUploadSuccess} />}

      {results.length > 0 && currentResult && (
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header with View Toggle and Reset Button */}
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
              Analysis Results
            </h2>
            <div className="flex gap-3">
              {/* View Toggle (only show if we have project rankings) */}
              {projectRanking && results.length > 1 && (
                <div className="flex bg-slate-200 dark:bg-slate-700 rounded-lg p-1">
                  <button
                    onClick={() => setShowProjects(false)}
                    className={`px-4 py-2 rounded-md transition-colors ${
                      !showProjects
                        ? 'bg-white dark:bg-slate-800 text-primary-600 dark:text-primary-400 shadow-sm'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    Individual Resumes
                  </button>
                  <button
                    onClick={() => setShowProjects(true)}
                    className={`px-4 py-2 rounded-md transition-colors ${
                      showProjects
                        ? 'bg-white dark:bg-slate-800 text-primary-600 dark:text-primary-400 shadow-sm'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    Best Projects
                  </button>
                </div>
              )}
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
              >
                Analyze More Resumes
              </button>
            </div>
          </div>

          {/* Conditional Rendering: Individual Resumes or Best Projects */}
          {!showProjects ? (
            <>
              {/* Resume Selector (if multiple resumes) */}
              {results.length > 1 && (
                <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                    Select Resume ({results.length} total)
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {results.map((result, index) => (
                      <button
                        key={index}
                        onClick={() => setSelectedResultIndex(index)}
                        className={`p-4 rounded-lg border-2 transition-all ${
                          selectedResultIndex === index
                            ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-slate-200 dark:border-slate-700 hover:border-primary-400'
                        }`}
                      >
                        <div className="text-sm font-medium text-slate-900 dark:text-white truncate">
                          {result.filename || `Resume ${index + 1}`}
                        </div>
                        <div className="mt-2 text-xs text-slate-600 dark:text-slate-400">
                          Score: {result.match_analysis.overall_score}%
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Current Resume Filename */}
              {currentResult.filename && (
                <div className="text-center">
                  <h3 className="text-xl font-semibold text-slate-900 dark:text-white">
                    {currentResult.filename}
                  </h3>
                </div>
              )}

              {/* Match Analysis Dashboard */}
              <MatchAnalysis result={currentResult} />

              {/* Two-column layout for Improvements and Comparison */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <ImprovementSuggestions suggestions={currentResult.improvements || []} />
                <ComparisonView comparisons={currentResult.comparisons || []} />
              </div>
            </>
          ) : (
            /* Best Projects View */
            projectRanking && (
              <RankedProjects
                projects={projectRanking.top_projects}
                experiences={projectRanking.top_experiences || []}
                totalResumes={projectRanking.total_resumes}
                totalProjectsFound={projectRanking.total_projects_found}
                totalExperiencesFound={projectRanking.total_experiences_found || 0}
                sourceFiles={uploadedFiles}
                jobTitle={jobTitle}
              />
            )
          )}
        </div>
      )}
    </div>
  );
}
