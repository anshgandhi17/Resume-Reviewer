'use client';

import { useState } from 'react';
import { RankedProject, api } from '@/lib/api';

interface RankedProjectsProps {
  projects: RankedProject[];
  experiences: RankedProject[];
  totalResumes: number;
  totalProjectsFound: number;
  totalExperiencesFound: number;
  sourceFiles: File[];
  jobTitle?: string;
}

export default function RankedProjects({
  projects,
  experiences,
  totalResumes,
  totalProjectsFound,
  totalExperiencesFound,
  sourceFiles,
  jobTitle = 'Software Engineer'
}: RankedProjectsProps) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  const handleGenerateResume = async (topKProjects: number = 3, topKExperiences: number = 3) => {
    if (!sourceFiles || sourceFiles.length === 0) {
      setError('No source resumes available');
      return;
    }

    setGenerating(true);
    setError('');

    try {
      // Use the first resume as the source for contact info
      const sourceResume = sourceFiles[0];

      // Generate resume
      const pdfBlob = await api.generateResume(
        projects,
        experiences || [],
        sourceResume,
        undefined, // Let backend extract name from resume
        jobTitle,
        topKProjects,
        topKExperiences
      );

      // Download the file
      const url = window.URL.createObjectURL(pdfBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'optimized_resume.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error('Resume generation error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to generate resume');
    } finally {
      setGenerating(false);
    }
  };

  if (!projects || projects.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          No Projects Found
        </h3>
        <p className="text-slate-600 dark:text-slate-400">
          No projects were extracted from the uploaded resumes.
        </p>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
    if (score >= 60) return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20';
    if (score >= 40) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
    return 'text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/20';
  };

  return (
    <div className="space-y-6">
      {/* Header with Generate Button */}
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
              Best Matching Projects & Experiences
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              Analyzed {totalProjectsFound} projects and {totalExperiencesFound} work experiences from {totalResumes} resumes.
            </p>
            <p className="text-slate-600 dark:text-slate-400 text-sm">
              Showing top {projects.length} projects and {experiences?.length || 0} experiences.
            </p>
          </div>

          {/* Generate Resume Button */}
          <button
            onClick={() => handleGenerateResume(5)}
            disabled={generating}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2 disabled:cursor-not-allowed"
          >
            {generating ? (
              <>
                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating...
              </>
            ) : (
              <>
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download Resume PDF
              </>
            )}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Projects List */}
      <div className="space-y-4">
        {projects.map((project, index) => (
          <div
            key={index}
            className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
          >
            {/* Project Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl font-bold text-slate-400 dark:text-slate-600">
                    #{index + 1}
                  </span>
                  <h3 className="text-xl font-semibold text-slate-900 dark:text-white">
                    {project.title}
                  </h3>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  From: {project.source_resume_id}
                </p>
              </div>

              {/* Relevance Score */}
              <div className={`px-4 py-2 rounded-lg ${getScoreColor(project.relevance_score)}`}>
                <div className="text-sm font-medium">Relevance</div>
                <div className="text-2xl font-bold">{Math.round(project.relevance_score)}%</div>
              </div>
            </div>

            {/* Description */}
            {project.description && (
              <p className="text-slate-700 dark:text-slate-300 mb-4">
                {project.description}
              </p>
            )}

            {/* Technologies */}
            {project.technologies && project.technologies.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                  Technologies Used:
                </h4>
                <div className="flex flex-wrap gap-2">
                  {project.technologies.map((tech, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full text-sm font-medium"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Key Achievements */}
            {project.bullets && project.bullets.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                  Key Achievements:
                </h4>
                <ul className="space-y-2">
                  {project.bullets.map((bullet, i) => (
                    <li key={i} className="flex items-start">
                      <span className="text-primary-600 dark:text-primary-400 mr-2">•</span>
                      <span className="text-slate-700 dark:text-slate-300">{bullet}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Matched Skills */}
            {project.matched_skills && project.matched_skills.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                  Matched Job Requirements:
                </h4>
                <div className="flex flex-wrap gap-2">
                  {project.matched_skills.map((skill, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-sm"
                    >
                      ✓ {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Reasoning */}
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                Why This Project Matches:
              </h4>
              <p className="text-slate-600 dark:text-slate-400 italic">
                "{project.reasoning}"
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Work Experiences List */}
      {experiences && experiences.length > 0 && (
        <>
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-4">
            <h3 className="text-xl font-bold text-slate-900 dark:text-white">
              Top Work Experiences
            </h3>
          </div>
          <div className="space-y-4">
            {experiences.map((experience, index) => (
              <div
                key={index}
                className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
              >
                {/* Experience Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl font-bold text-slate-400 dark:text-slate-600">
                        #{index + 1}
                      </span>
                      <h3 className="text-xl font-semibold text-slate-900 dark:text-white">
                        {experience.title}
                      </h3>
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      From: {experience.source_resume_id}
                    </p>
                  </div>

                  {/* Relevance Score */}
                  <div className={`px-4 py-2 rounded-lg ${getScoreColor(experience.relevance_score)}`}>
                    <div className="text-sm font-medium">Relevance</div>
                    <div className="text-2xl font-bold">{Math.round(experience.relevance_score)}%</div>
                  </div>
                </div>

                {/* Description (Date + Location) */}
                {experience.description && (
                  <p className="text-slate-700 dark:text-slate-300 mb-4">
                    {experience.description}
                  </p>
                )}

                {/* Technologies */}
                {experience.technologies && experience.technologies.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                      Technologies Used:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {experience.technologies.map((tech, i) => (
                        <span
                          key={i}
                          className="px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full text-sm font-medium"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Achievements */}
                {experience.bullets && experience.bullets.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                      Key Achievements:
                    </h4>
                    <ul className="space-y-2">
                      {experience.bullets.map((bullet, i) => (
                        <li key={i} className="flex items-start">
                          <span className="text-primary-600 dark:text-primary-400 mr-2">•</span>
                          <span className="text-slate-700 dark:text-slate-300">{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Matched Skills */}
                {experience.matched_skills && experience.matched_skills.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                      Matched Job Requirements:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {experience.matched_skills.map((skill, i) => (
                        <span
                          key={i}
                          className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-sm"
                        >
                          ✓ {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Reasoning */}
                <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                    Why This Experience Matches:
                  </h4>
                  <p className="text-slate-600 dark:text-slate-400 italic">
                    "{experience.reasoning}"
                  </p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
