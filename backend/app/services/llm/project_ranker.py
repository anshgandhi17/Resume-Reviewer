"""
LLM-based project ranking service.
Ranks projects by relevance to a job description.
"""

from typing import List, Dict
from langchain_community.llms import Ollama
from ..parsing.project_extractor import Project
from ..parsing.job_description_parser import JobDescriptionParser, ParsedJobDescription
from ...core.config import settings
import json
import logging

logger = logging.getLogger(__name__)


class ProjectRanker:
    """Rank projects by relevance to job description using LLM."""

    def __init__(self, model_name: str = None):
        """
        Initialize the project ranker.

        Args:
            model_name: Ollama model to use (defaults to settings.ollama_model)
        """
        self.model_name = model_name or settings.ollama_model
        self.llm = Ollama(
            base_url=settings.ollama_base_url,
            model=self.model_name,
            temperature=0.3  # Lower temperature for more consistent scoring
        )
        self.job_parser = JobDescriptionParser()

    def rank_projects(
        self,
        projects: List[Project],
        job_description: str,
        top_k: int = None
    ) -> List[Dict]:
        """
        Rank projects by relevance to job description.

        Args:
            projects: List of Project objects to rank
            job_description: Job description text
            top_k: Return only top K projects (None = all)

        Returns:
            List of dicts with project info and relevance scores, sorted by score
        """
        if not projects:
            return []

        # Use ThreadPoolExecutor for parallel scoring
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from app.utils.concurrency import ResourceMonitor

        # Dynamically determine optimal worker count based on system resources
        recommended_workers = ResourceMonitor.get_recommended_workers()
        max_workers = min(recommended_workers, len(projects))

        # Check if we should use sequential processing
        if ResourceMonitor.should_use_sequential_processing():
            logger.warning("System resources constrained, using sequential processing")
            max_workers = 1

        ranked_projects = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scoring tasks
            future_to_project = {
                executor.submit(self._score_project, project, job_description): project
                for project in projects
            }

            # Collect results as they complete
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    score = future.result()

                    ranked_projects.append({
                        'title': project.title,
                        'description': project.description,
                        'technologies': project.technologies,
                        'bullets': project.bullets,
                        'source_resume_id': project.source_resume_id,
                        'relevance_score': score['relevance_score'],
                        'reasoning': score['reasoning'],
                        'matched_skills': score.get('matched_skills', []),
                        'raw_text': project.raw_text
                    })
                except Exception as e:
                    logger.error(f"Error scoring project '{project.title}': {str(e)}")
                    # Add with 0 score on error
                    ranked_projects.append({
                        'title': project.title,
                        'description': project.description,
                        'technologies': project.technologies,
                        'bullets': project.bullets,
                        'source_resume_id': project.source_resume_id,
                        'relevance_score': 0.0,
                        'reasoning': f'Error during scoring: {str(e)}',
                        'matched_skills': [],
                        'raw_text': project.raw_text
                    })

        # Sort by relevance score (descending)
        ranked_projects.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Return top K if specified
        if top_k:
            return ranked_projects[:top_k]

        return ranked_projects

    def _score_project(self, project: Project, job_description: str) -> Dict:
        """
        Score a single project against the job description.

        Args:
            project: Project object
            job_description: Job description text

        Returns:
            Dict with relevance_score (0-100), reasoning, and matched_skills
        """
        # Parse job description to extract structured requirements
        parsed_jd = self.job_parser.parse(job_description)

        # Build project summary
        project_summary = f"""
Project Title: {project.title}

Description: {project.description}

Technologies: {', '.join(project.technologies) if project.technologies else 'None specified'}

Key Achievements:
{chr(10).join('• ' + bullet for bullet in project.bullets)}
        """.strip()

        # Build structured job requirements summary
        required_skills_text = ""
        if parsed_jd.required_skills:
            required_skills_text = "REQUIRED SKILLS (High Priority):\n" + "\n".join(
                f"• {req.text}" for req in parsed_jd.required_skills[:10]  # Top 10 required
            )

        preferred_skills_text = ""
        if parsed_jd.preferred_skills:
            preferred_skills_text = "\n\nPREFERRED SKILLS (Lower Priority):\n" + "\n".join(
                f"• {req.text}" for req in parsed_jd.preferred_skills[:5]  # Top 5 preferred
            )

        experience_text = ""
        if parsed_jd.years_experience_required:
            experience_text = f"\n\nEXPERIENCE REQUIRED: {parsed_jd.years_experience_required}+ years"

        education_text = ""
        if parsed_jd.education_requirements:
            education_text = f"\n\nEDUCATION: {', '.join(parsed_jd.education_requirements)}"

        # Create enhanced scoring prompt with structured requirements
        prompt = f"""You are an expert technical recruiter. Score how relevant this project is to the job requirements.

JOB REQUIREMENTS:
{required_skills_text}{preferred_skills_text}{experience_text}{education_text}

PROJECT:
{project_summary}

SCORING INSTRUCTIONS:
- REQUIRED skills should heavily influence the score (weight: 1.0)
- PREFERRED skills are nice-to-have (weight: 0.6)
- Consider both direct technology matches AND transferable skills
- Match depth of experience if years are mentioned in requirements

Provide a JSON response with:
1. "relevance_score": A number from 0-100
   - 90-100: Matches most REQUIRED skills, demonstrates clear expertise
   - 70-89: Matches several REQUIRED skills with good depth
   - 50-69: Matches some REQUIRED or many PREFERRED skills
   - 30-49: Limited match to REQUIRED, some PREFERRED skills
   - 0-29: Minimal overlap with requirements

2. "reasoning": Brief explanation (2-3 sentences) focusing on which REQUIRED skills are matched

3. "matched_skills": List of specific skills/technologies from requirements that this project demonstrates

Respond ONLY with valid JSON in this format:
{{
  "relevance_score": <number>,
  "reasoning": "<explanation>",
  "matched_skills": ["skill1", "skill2", ...]
}}"""

        try:
            response = self.llm.invoke(prompt)

            # Extract JSON from response
            score_data = self._parse_json_response(response)

            # Validate score is in range
            score = score_data.get('relevance_score', 0)
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                logger.warning(f"Invalid score {score}, defaulting to 0")
                score = 0

            return {
                'relevance_score': float(score),
                'reasoning': score_data.get('reasoning', 'No reasoning provided'),
                'matched_skills': score_data.get('matched_skills', [])
            }

        except Exception as e:
            logger.error(f"Error scoring project '{project.title}': {str(e)}")
            # Return default low score on error
            return {
                'relevance_score': 0.0,
                'reasoning': f'Error during scoring: {str(e)}',
                'matched_skills': []
            }

    def _parse_json_response(self, response: str) -> Dict:
        """
        Parse JSON from LLM response, handling common formatting issues.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dict
        """
        # Try direct JSON parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # If all parsing fails, return default
        logger.warning(f"Could not parse JSON from response: {response[:200]}")
        return {
            'relevance_score': 0,
            'reasoning': 'Failed to parse LLM response',
            'matched_skills': []
        }

    def generate_project_summary(self, ranked_projects: List[Dict], top_k: int = 5) -> str:
        """
        Generate a summary of the top projects.

        Args:
            ranked_projects: List of ranked project dicts
            top_k: Number of top projects to include

        Returns:
            Formatted summary string
        """
        top_projects = ranked_projects[:top_k]

        if not top_projects:
            return "No projects found."

        summary = f"Top {len(top_projects)} Most Relevant Projects:\n\n"

        for i, proj in enumerate(top_projects, 1):
            summary += f"{i}. {proj['title']} (Relevance: {proj['relevance_score']:.0f}%)\n"
            summary += f"   Source: Resume {proj.get('source_resume_id', 'Unknown')}\n"
            summary += f"   Technologies: {', '.join(proj['technologies'])}\n"
            summary += f"   Why relevant: {proj['reasoning']}\n"

            if proj.get('matched_skills'):
                summary += f"   Matched skills: {', '.join(proj['matched_skills'])}\n"

            summary += "\n"

        return summary
