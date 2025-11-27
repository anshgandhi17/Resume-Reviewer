from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from app.core.config import settings
from typing import Dict, List
import json
import re


class LLMService:
    """Service for LLM-based resume analysis using Ollama."""

    def __init__(self):
        self.llm = Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model
        )

    def analyze_resume_match(
        self,
        resume_text: str,
        job_description: str,
        similar_resumes: List[Dict] = None
    ) -> Dict:
        """Analyze how well a resume matches a job description."""

        # Extract skills from job description
        jd_skills = self._extract_skills(job_description)

        # Extract skills from resume
        resume_skills = self._extract_skills(resume_text)

        # Calculate skill matches
        matched_skills = list(set(resume_skills) & set(jd_skills))
        missing_skills = list(set(jd_skills) - set(resume_skills))

        # Get overall compatibility analysis
        compatibility_prompt = PromptTemplate(
            input_variables=["resume", "job_description"],
            template="""You are an expert resume reviewer. Analyze how well this resume matches the job description.

Job Description:
{job_description}

Resume:
{resume}

Provide a detailed analysis including:
1. Overall compatibility score (0-100)
2. Key strengths that match the role
3. Major gaps or missing qualifications
4. ATS-friendliness score (0-100) based on keyword usage and formatting

Respond in JSON format:
{{
    "overall_score": <number>,
    "ats_score": <number>,
    "strengths": ["strength1", "strength2"],
    "gaps": ["gap1", "gap2"]
}}"""
        )

        chain = LLMChain(llm=self.llm, prompt=compatibility_prompt)
        analysis_text = chain.run(resume=resume_text, job_description=job_description)

        # Parse JSON from response
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                # Fallback if JSON parsing fails
                analysis = {
                    "overall_score": 70,
                    "ats_score": 65,
                    "strengths": [],
                    "gaps": []
                }
        except json.JSONDecodeError:
            analysis = {
                "overall_score": 70,
                "ats_score": 65,
                "strengths": [],
                "gaps": []
            }

        return {
            "overall_score": analysis.get("overall_score", 70),
            "ats_score": analysis.get("ats_score", 65),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "strengths": analysis.get("strengths", []),
            "gaps": analysis.get("gaps", [])
        }

    def generate_improvements(
        self,
        resume_text: str,
        job_description: str,
        analysis: Dict
    ) -> List[Dict]:
        """Generate specific improvement suggestions for the resume."""

        prompt = PromptTemplate(
            input_variables=["resume", "job_description", "missing_skills"],
            template="""You are a professional resume coach. Based on the job description and resume provided, suggest specific improvements.

Job Description:
{job_description}

Resume:
{resume}

Missing Skills: {missing_skills}

Provide 5-7 specific, actionable improvements. For each suggestion:
1. Identify the section to improve (e.g., Summary, Experience, Skills)
2. Provide the specific suggestion
3. Assign priority: high, medium, or low

Format as JSON array:
[
    {{
        "section": "section name",
        "suggestion": "specific improvement suggestion",
        "priority": "high/medium/low"
    }}
]"""
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)
        suggestions_text = chain.run(
            resume=resume_text,
            job_description=job_description,
            missing_skills=", ".join(analysis.get("missing_skills", []))
        )

        try:
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', suggestions_text, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
            else:
                suggestions = []
        except json.JSONDecodeError:
            suggestions = []

        return suggestions

    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical and professional skills from text."""
        # This is a simplified version - in production, use spaCy or custom NER
        common_tech_skills = [
            "python", "java", "javascript", "react", "node.js", "sql", "aws",
            "docker", "kubernetes", "git", "machine learning", "data analysis",
            "fastapi", "django", "flask", "mongodb", "postgresql", "redis",
            "typescript", "vue.js", "angular", "ci/cd", "jenkins", "terraform",
            "agile", "scrum", "project management", "leadership", "communication"
        ]

        text_lower = text.lower()
        found_skills = []

        for skill in common_tech_skills:
            if skill in text_lower:
                found_skills.append(skill)

        return found_skills

    def compare_requirements(
        self,
        resume_text: str,
        job_description: str
    ) -> List[Dict]:
        """Compare job requirements against resume content."""

        prompt = PromptTemplate(
            input_variables=["resume", "job_description"],
            template="""Compare the job requirements against the resume content.

Job Description:
{job_description}

Resume:
{resume}

For each major requirement in the job description, determine if it's:
- "matched": clearly present in resume
- "partial": somewhat addressed but not fully
- "missing": not mentioned in resume

Return as JSON array:
[
    {{
        "requirement": "requirement text",
        "status": "matched/partial/missing",
        "resume_evidence": "quote from resume if matched/partial, null if missing"
    }}
]"""
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)
        comparison_text = chain.run(resume=resume_text, job_description=job_description)

        try:
            json_match = re.search(r'\[.*\]', comparison_text, re.DOTALL)
            if json_match:
                comparisons = json.loads(json_match.group())
            else:
                comparisons = []
        except json.JSONDecodeError:
            comparisons = []

        return comparisons
