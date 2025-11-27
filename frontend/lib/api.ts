import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface UploadResponse {
  status: 'completed';
  result: AnalysisResult;
}

export interface AnalysisResult {
  match_analysis: {
    overall_score: number;
    skills: {
      matched: string[];
      missing: string[];
      transferable: string[];
    };
    experience_relevance: Record<string, number>;
    ats_score: number;
  };
  improvements: ImprovementSuggestion[];
  comparisons: ComparisonHighlight[];
  similar_resumes: SimilarResume[];
  filename?: string;
}

export interface ImprovementSuggestion {
  section: string;
  original?: string;
  suggestion: string;
  priority: 'low' | 'medium' | 'high';
}

export interface ComparisonHighlight {
  requirement: string;
  status: 'matched' | 'partial' | 'missing';
  resume_evidence?: string;
}

export interface SimilarResume {
  id: string;
  similarity: number;
  metadata: Record<string, any>;
}

export interface ProcessResumeResponse {
  status: 'success';
  resume_text: string;
  job_description: string;
  similar_resumes: SimilarResume[];
}

export interface BatchUploadResponse {
  status: string;
  message: string;
  summary: {
    total_files: number;
    successful: number;
    failed: number;
    total_chunks: number;
    total_time: number;
    avg_time_per_file: number;
    chunks_per_file_avg: number;
  };
  results: Array<{
    resume_id: string;
    original_filename: string;
    status: 'success' | 'error';
    chunk_count?: number;
    processing_time?: number;
    error?: string;
  }>;
}

export interface ResumeWithText {
  file: File;
  resumeText: string;
  resumeId: string;
}

export interface RankedProject {
  title: string;
  description: string;
  technologies: string[];
  bullets: string[];
  source_resume_id: string;
  relevance_score: number;
  reasoning: string;
  matched_skills: string[];
  raw_text: string;
}

export interface ProjectRankingResponse {
  status: string;
  total_resumes: number;
  total_projects_found: number;
  total_experiences_found: number;
  top_projects: RankedProject[];
  top_experiences: RankedProject[]; // Same structure as projects
  summary: string;
}

export const api = {
  async uploadResume(file: File, jobDescription: string, jobTitle?: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('resume', file);
    formData.append('job_description', jobDescription);
    if (jobTitle) {
      formData.append('job_title', jobTitle);
    }

    const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Process resume for client-side LLM analysis (hosted backend + local Ollama)
   */
  async processResume(file: File, jobDescription: string, jobTitle?: string): Promise<ProcessResumeResponse> {
    const formData = new FormData();
    formData.append('resume', file);
    formData.append('job_description', jobDescription);
    if (jobTitle) {
      formData.append('job_title', jobTitle);
    }

    const response = await axios.post(`${API_BASE_URL}/process-resume`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Batch upload multiple resumes for processing
   */
  async batchUploadResumes(files: File[]): Promise<BatchUploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axios.post(`${API_BASE_URL}/upload/batch`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Process a single resume and return text (used after batch upload)
   */
  async extractResumeText(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('resume', file);
    formData.append('job_description', 'placeholder'); // Required by endpoint but not used

    const response = await axios.post(`${API_BASE_URL}/process-resume`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data.resume_text;
  },

  /**
   * Rank projects from multiple resumes by relevance to job description
   */
  async rankProjects(
    files: File[],
    jobDescription: string,
    topK: number = 10,
    rankingMethod: 'llm' | 'vector' = 'llm'
  ): Promise<ProjectRankingResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('job_description', jobDescription);
    formData.append('top_k', topK.toString());
    formData.append('ranking_method', rankingMethod);

    const response = await axios.post(`${API_BASE_URL}/rank-projects`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Generate optimized resume PDF with best matching projects and experiences
   */
  async generateResume(
    rankedProjects: RankedProject[],
    rankedExperiences: RankedProject[],
    sourceResume: File,
    candidateName?: string,
    jobTitle: string = 'Software Engineer',
    topKProjects: number = 3,
    topKExperiences: number = 3
  ): Promise<Blob> {
    const formData = new FormData();

    // Add the projects and experiences as JSON
    formData.append('ranked_projects', JSON.stringify(rankedProjects));
    formData.append('ranked_experiences', JSON.stringify(rankedExperiences));

    // Add source resume for contact info extraction
    formData.append('source_resume', sourceResume);

    // Add optional parameters
    if (candidateName) {
      formData.append('candidate_name', candidateName);
    }
    formData.append('job_title', jobTitle);
    formData.append('top_k_projects', topKProjects.toString());
    formData.append('top_k_experiences', topKExperiences.toString());

    const response = await axios.post(`${API_BASE_URL}/generate-resume`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob', // Important for file download
    });

    return response.data;
  },

  async healthCheck() {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  },
};
