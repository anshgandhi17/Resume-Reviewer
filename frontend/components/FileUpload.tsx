'use client';

import { useState, useCallback, useEffect } from 'react';
import { api, AnalysisResult } from '@/lib/api';
import { ollamaService } from '@/lib/ollama';

interface FileUploadProps {
  onUploadSuccess: (result: AnalysisResult) => void;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [processingStep, setProcessingStep] = useState('');
  const [ollamaConnected, setOllamaConnected] = useState<boolean | null>(null);
  const [ollamaError, setOllamaError] = useState('');

  // Check Ollama connection on mount
  useEffect(() => {
    checkOllamaConnection();
  }, []);

  const checkOllamaConnection = async () => {
    try {
      const status = await ollamaService.checkConnection();
      setOllamaConnected(status.connected);
      if (!status.connected) {
        setOllamaError(status.error || 'Cannot connect to Ollama');
      } else {
        setOllamaError('');
      }
    } catch (err) {
      setOllamaConnected(false);
      setOllamaError('Cannot connect to Ollama at localhost:11434');
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
        setError('');
      } else {
        setError('Please upload a PDF file');
      }
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
        setError('');
      } else {
        setError('Please upload a PDF file');
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a resume file');
      return;
    }

    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    if (!ollamaConnected) {
      setError('Ollama is not running. Please start Ollama and refresh the page.');
      return;
    }

    setUploading(true);
    setError('');

    try {
      // Step 1: Process resume on backend (PDF extraction + vector search)
      setProcessingStep('Uploading and processing PDF...');
      const processedData = await api.processResume(file, jobDescription, jobTitle || undefined);

      // Step 2: Analyze with local Ollama
      setProcessingStep('Analyzing resume match (using local Ollama)...');
      const matchAnalysis = await ollamaService.analyzeResumeMatch(
        processedData.resume_text,
        processedData.job_description
      );

      // Step 3: Generate improvements
      setProcessingStep('Generating improvement suggestions...');
      const improvements = await ollamaService.generateImprovements(
        processedData.resume_text,
        processedData.job_description,
        matchAnalysis.missing_skills
      );

      // Step 4: Compare requirements
      setProcessingStep('Comparing requirements...');
      const comparisons = await ollamaService.compareRequirements(
        processedData.resume_text,
        processedData.job_description
      );

      // Build final result
      const result: AnalysisResult = {
        match_analysis: {
          overall_score: matchAnalysis.overall_score,
          skills: {
            matched: matchAnalysis.matched_skills,
            missing: matchAnalysis.missing_skills,
            transferable: []
          },
          experience_relevance: {},
          ats_score: matchAnalysis.ats_score
        },
        improvements: improvements,
        comparisons: comparisons,
        similar_resumes: processedData.similar_resumes
      };

      onUploadSuccess(result);
    } catch (err: any) {
      console.error('Analysis error:', err);
      setError(err.message || err.response?.data?.detail || 'Failed to analyze resume. Please try again.');
    } finally {
      setUploading(false);
      setProcessingStep('');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Upload */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Upload Resume (PDF)
          </label>
          <div
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/10'
                : 'border-slate-300 dark:border-slate-600'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="space-y-2">
              <svg
                className="mx-auto h-12 w-12 text-slate-400"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <div className="text-slate-600 dark:text-slate-400">
                {file ? (
                  <span className="font-medium text-primary-600 dark:text-primary-400">
                    {file.name}
                  </span>
                ) : (
                  <>
                    <span className="font-medium text-primary-600 dark:text-primary-400">
                      Click to upload
                    </span>{' '}
                    or drag and drop
                  </>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">PDF up to 10MB</p>
            </div>
          </div>
        </div>

        {/* Job Title */}
        <div>
          <label
            htmlFor="jobTitle"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
          >
            Job Title (Optional)
          </label>
          <input
            type="text"
            id="jobTitle"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="e.g., Senior Software Engineer"
            className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-slate-800 dark:text-white"
          />
        </div>

        {/* Job Description */}
        <div>
          <label
            htmlFor="jobDescription"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
          >
            Job Description *
          </label>
          <textarea
            id="jobDescription"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the full job description here..."
            rows={10}
            className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-slate-800 dark:text-white resize-none"
            required
          />
        </div>

        {/* Ollama Connection Status */}
        {ollamaConnected === null && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-600 dark:text-blue-400">Checking Ollama connection...</p>
          </div>
        )}

        {ollamaConnected === false && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">Ollama Not Connected</p>
                <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">{ollamaError}</p>
                <button
                  type="button"
                  onClick={checkOllamaConnection}
                  className="text-sm text-yellow-800 dark:text-yellow-300 underline mt-2 hover:text-yellow-900 dark:hover:text-yellow-200"
                >
                  Retry Connection
                </button>
              </div>
            </div>
          </div>
        )}

        {ollamaConnected === true && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-green-600 dark:text-green-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-sm text-green-700 dark:text-green-400">Ollama connected - Ready to analyze</p>
            </div>
          </div>
        )}

        {/* Processing Step */}
        {uploading && processingStep && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-700 dark:text-blue-400">{processingStep}</p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={uploading || !file || !jobDescription.trim() || !ollamaConnected}
          className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white font-medium py-3 px-6 rounded-lg transition-colors disabled:cursor-not-allowed"
        >
          {uploading ? (
            <span className="flex items-center justify-center">
              <svg
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Analyzing...
            </span>
          ) : (
            'Analyze Resume'
          )}
        </button>
      </form>
    </div>
  );
}
