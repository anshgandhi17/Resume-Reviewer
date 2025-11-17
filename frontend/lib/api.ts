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

  async healthCheck() {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  },
};
