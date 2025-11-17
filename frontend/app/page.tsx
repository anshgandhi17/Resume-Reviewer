'use client';

import { useState } from 'react';
import FileUpload from '@/components/FileUpload';
import MatchAnalysis from '@/components/MatchAnalysis';
import ImprovementSuggestions from '@/components/ImprovementSuggestions';
import ComparisonView from '@/components/ComparisonView';
import { AnalysisResult } from '@/lib/api';

export default function Home() {
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const handleUploadSuccess = (analysisResult: AnalysisResult) => {
    setResult(analysisResult);
  };

  const handleReset = () => {
    setResult(null);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {!result && <FileUpload onUploadSuccess={handleUploadSuccess} />}

      {result && (
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header with Reset Button */}
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
              Analysis Results
            </h2>
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
            >
              Analyze Another Resume
            </button>
          </div>

          {/* Match Analysis Dashboard */}
          <MatchAnalysis result={result} />

          {/* Two-column layout for Improvements and Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <ImprovementSuggestions suggestions={result.improvements || []} />
            <ComparisonView comparisons={result.comparisons || []} />
          </div>
        </div>
      )}
    </div>
  );
}
