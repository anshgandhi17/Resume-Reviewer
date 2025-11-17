import { Ollama } from 'ollama/browser';

export interface OllamaConfig {
  baseUrl?: string;
  model?: string;
}

export interface MatchAnalysis {
  overall_score: number;
  ats_score: number;
  matched_skills: string[];
  missing_skills: string[];
  strengths: string[];
  gaps: string[];
}

export interface ImprovementSuggestion {
  section: string;
  suggestion: string;
  priority: 'low' | 'medium' | 'high';
}

export interface ComparisonResult {
  requirement: string;
  status: 'matched' | 'partial' | 'missing';
  resume_evidence?: string;
}

class OllamaService {
  private ollama: Ollama;
  private model: string;

  constructor(config: OllamaConfig = {}) {
    const baseUrl = config.baseUrl || 'http://localhost:11434';
    this.model = config.model || 'llama2';

    this.ollama = new Ollama({ host: baseUrl });
  }

  /**
   * Check if Ollama is running and the model is available
   */
  async checkConnection(): Promise<{ connected: boolean; model?: string; error?: string }> {
    try {
      const models = await this.ollama.list();
      const modelExists = models.models.some((m: any) => m.name.includes(this.model));

      if (!modelExists) {
        return {
          connected: false,
          error: `Model '${this.model}' not found. Please run: ollama pull ${this.model}`
        };
      }

      return { connected: true, model: this.model };
    } catch (error: any) {
      return {
        connected: false,
        error: `Cannot connect to Ollama at localhost:11434. Please ensure Ollama is running.`
      };
    }
  }

  /**
   * Extract skills from text (basic implementation)
   */
  private extractSkills(text: string): string[] {
    const commonTechSkills = [
      'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws',
      'docker', 'kubernetes', 'git', 'machine learning', 'data analysis',
      'fastapi', 'django', 'flask', 'mongodb', 'postgresql', 'redis',
      'typescript', 'vue.js', 'angular', 'ci/cd', 'jenkins', 'terraform',
      'agile', 'scrum', 'project management', 'leadership', 'communication'
    ];

    const textLower = text.toLowerCase();
    const foundSkills: string[] = [];

    for (const skill of commonTechSkills) {
      if (textLower.includes(skill)) {
        foundSkills.push(skill);
      }
    }

    return foundSkills;
  }

  /**
   * Parse JSON from LLM response (handles cases where LLM adds extra text)
   */
  private parseJSON<T>(text: string, fallback: T): T {
    try {
      // Extract JSON from response
      const jsonMatch = text.match(/\{[\s\S]*\}|\[[\s\S]*\]/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
      return fallback;
    } catch {
      return fallback;
    }
  }

  /**
   * Analyze resume match against job description
   */
  async analyzeResumeMatch(
    resumeText: string,
    jobDescription: string
  ): Promise<MatchAnalysis> {
    // Extract skills
    const jdSkills = this.extractSkills(jobDescription);
    const resumeSkills = this.extractSkills(resumeText);
    const matchedSkills = resumeSkills.filter(s => jdSkills.includes(s));
    const missingSkills = jdSkills.filter(s => !resumeSkills.includes(s));

    // Get LLM analysis
    const prompt = `You are an expert resume reviewer. Analyze how well this resume matches the job description.

Job Description:
${jobDescription}

Resume:
${resumeText}

Provide a detailed analysis including:
1. Overall compatibility score (0-100)
2. Key strengths that match the role
3. Major gaps or missing qualifications
4. ATS-friendliness score (0-100) based on keyword usage and formatting

Respond in JSON format:
{
    "overall_score": <number>,
    "ats_score": <number>,
    "strengths": ["strength1", "strength2"],
    "gaps": ["gap1", "gap2"]
}`;

    try {
      const response = await this.ollama.generate({
        model: this.model,
        prompt: prompt,
        stream: false,
      });

      const analysis = this.parseJSON<{
        overall_score: number;
        ats_score: number;
        strengths: string[];
        gaps: string[];
      }>(response.response, {
        overall_score: 70,
        ats_score: 65,
        strengths: [],
        gaps: []
      });

      return {
        overall_score: analysis.overall_score,
        ats_score: analysis.ats_score,
        matched_skills: matchedSkills,
        missing_skills: missingSkills,
        strengths: analysis.strengths,
        gaps: analysis.gaps
      };
    } catch (error: any) {
      throw new Error(`Failed to analyze resume: ${error.message}`);
    }
  }

  /**
   * Generate improvement suggestions
   */
  async generateImprovements(
    resumeText: string,
    jobDescription: string,
    missingSkills: string[]
  ): Promise<ImprovementSuggestion[]> {
    const prompt = `You are a professional resume coach. Based on the job description and resume provided, suggest specific improvements.

Job Description:
${jobDescription}

Resume:
${resumeText}

Missing Skills: ${missingSkills.join(', ')}

Provide 5-7 specific, actionable improvements. For each suggestion:
1. Identify the section to improve (e.g., Summary, Experience, Skills)
2. Provide the specific suggestion
3. Assign priority: high, medium, or low

Format as JSON array:
[
    {
        "section": "section name",
        "suggestion": "specific improvement suggestion",
        "priority": "high/medium/low"
    }
]`;

    try {
      const response = await this.ollama.generate({
        model: this.model,
        prompt: prompt,
        stream: false,
      });

      return this.parseJSON<ImprovementSuggestion[]>(response.response, []);
    } catch (error: any) {
      throw new Error(`Failed to generate improvements: ${error.message}`);
    }
  }

  /**
   * Compare requirements against resume
   */
  async compareRequirements(
    resumeText: string,
    jobDescription: string
  ): Promise<ComparisonResult[]> {
    const prompt = `Compare the job requirements against the resume content.

Job Description:
${jobDescription}

Resume:
${resumeText}

For each major requirement in the job description, determine if it's:
- "matched": clearly present in resume
- "partial": somewhat addressed but not fully
- "missing": not mentioned in resume

Return as JSON array:
[
    {
        "requirement": "requirement text",
        "status": "matched/partial/missing",
        "resume_evidence": "quote from resume if matched/partial, null if missing"
    }
]`;

    try {
      const response = await this.ollama.generate({
        model: this.model,
        prompt: prompt,
        stream: false,
      });

      return this.parseJSON<ComparisonResult[]>(response.response, []);
    } catch (error: any) {
      throw new Error(`Failed to compare requirements: ${error.message}`);
    }
  }
}

// Export singleton instance
export const ollamaService = new OllamaService();

// Export class for custom configurations
export { OllamaService };
