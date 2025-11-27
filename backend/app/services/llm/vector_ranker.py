"""
Vector similarity-based project ranking service.
Ranks projects by vector similarity to job requirements instead of LLM.
"""

from typing import List, Dict
from sentence_transformers import SentenceTransformer
from ..parsing.project_extractor import Project
from ..parsing.job_description_parser import JobDescriptionParser, ParsedJobDescription
from ...core.config import settings
import numpy as np
import logging
import re

logger = logging.getLogger(__name__)


class VectorRanker:
    """Rank projects by vector similarity to job description."""

    def __init__(self):
        """Initialize the vector ranker with embedding model."""
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.job_parser = JobDescriptionParser()
        logger.info(f"Vector ranker initialized with {settings.embedding_model}")

    def rank_projects(
        self,
        projects: List[Project],
        job_description: str,
        top_k: int = None
    ) -> List[Dict]:
        """
        Rank projects by vector similarity to job description.

        Args:
            projects: List of Project objects to rank
            job_description: Job description text
            top_k: Return only top K projects (None = all)

        Returns:
            List of dicts with project info and relevance scores, sorted by score
        """
        if not projects:
            return []

        logger.info(f"Ranking {len(projects)} projects using vector similarity with weighted requirements")

        # Parse job description to extract structured requirements
        parsed_jd = self.job_parser.parse(job_description)
        logger.info(f"Parsed job description: {len(parsed_jd.required_skills)} required, "
                   f"{len(parsed_jd.preferred_skills)} preferred requirements")

        # Get weighted requirements
        weighted_requirements = self.job_parser.get_weighted_requirements_text(parsed_jd)
        logger.info(f"Using {len(weighted_requirements)} weighted requirements for ranking")

        # Embed requirements with their weights
        requirement_texts = [req[0] for req in weighted_requirements]
        weights = np.array([req[1] for req in weighted_requirements])

        requirement_embeddings = self.embedding_model.encode(requirement_texts)

        # Compute weighted average of requirement embeddings
        # Normalize weights to sum to 1
        normalized_weights = weights / np.sum(weights)
        job_vector = np.average(requirement_embeddings, axis=0, weights=normalized_weights)

        # Score each project
        ranked_projects = []
        for project in projects:
            # Create project text representation
            project_text = self._project_to_text(project)

            # Embed project
            project_vector = self.embedding_model.encode(project_text)

            # Calculate cosine similarity
            similarity = self._cosine_similarity(job_vector, project_vector)

            # Convert to 0-100 scale
            relevance_score = float(similarity * 100)

            # Find matched skills from parsed job description
            matched_skills = self._find_matched_skills_from_parsed(project, parsed_jd)

            # Generate reasoning
            reasoning = self._generate_reasoning(relevance_score, matched_skills, project)

            ranked_projects.append({
                'title': project.title,
                'description': project.description,
                'technologies': project.technologies,
                'bullets': project.bullets,
                'source_resume_id': project.source_resume_id,
                'relevance_score': relevance_score,
                'reasoning': reasoning,
                'matched_skills': matched_skills,
                'raw_text': project.raw_text
            })

        # Sort by relevance score (descending)
        ranked_projects.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Return top K if specified
        if top_k:
            return ranked_projects[:top_k]

        return ranked_projects

    def _project_to_text(self, project: Project) -> str:
        """
        Convert project to text representation for embedding.

        Args:
            project: Project object

        Returns:
            Text representation of project
        """
        parts = [
            f"Project: {project.title}",
            f"Description: {project.description}",
            f"Technologies: {', '.join(project.technologies)}" if project.technologies else "",
            "Achievements: " + " ".join(project.bullets) if project.bullets else ""
        ]

        return " ".join(filter(None, parts))

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score between -1 and 1 (typically 0 to 1 for embeddings)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _find_matched_skills_from_parsed(
        self,
        project: Project,
        parsed_jd: ParsedJobDescription
    ) -> List[str]:
        """
        Find skills/technologies that match between project and parsed job description.

        Args:
            project: Project object
            parsed_jd: ParsedJobDescription object

        Returns:
            List of matched skills
        """
        matched = set()

        # Combine all project text
        project_text = (
            f"{project.title} {project.description} "
            f"{' '.join(project.technologies)} {' '.join(project.bullets)}"
        ).lower()

        # Check against technical skills from parsed JD
        for tech_skill in parsed_jd.technical_skills:
            if tech_skill.lower() in project_text:
                matched.add(tech_skill.title())

        # Check against explicit project technologies
        for tech in project.technologies:
            tech_lower = tech.lower()
            # Check if project tech is in JD's technical skills or requirements
            if tech_lower in parsed_jd.technical_skills:
                matched.add(tech)
            else:
                # Check in requirement text
                for req in parsed_jd.all_requirements:
                    if tech_lower in req.text.lower():
                        matched.add(tech)
                        break

        # Check soft skills if mentioned in project
        for soft_skill in parsed_jd.soft_skills:
            if soft_skill.lower() in project_text:
                matched.add(soft_skill.title())

        return sorted(list(matched))

    def _generate_reasoning(
        self,
        score: float,
        matched_skills: List[str],
        project: Project
    ) -> str:
        """
        Generate human-readable reasoning for the score.

        Args:
            score: Relevance score (0-100)
            matched_skills: List of matched skills
            project: Project object

        Returns:
            Reasoning string
        """
        if score >= 80:
            level = "Highly relevant"
        elif score >= 60:
            level = "Moderately relevant"
        elif score >= 40:
            level = "Somewhat relevant"
        else:
            level = "Limited relevance"

        if matched_skills:
            skills_text = ", ".join(matched_skills[:5])  # Show top 5
            if len(matched_skills) > 5:
                skills_text += f" and {len(matched_skills) - 5} more"
            return f"{level} based on vector similarity. Matched technologies: {skills_text}."
        else:
            return f"{level} based on vector similarity to job requirements."

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

        summary = f"Top {len(top_projects)} Most Relevant Projects (Vector Similarity):\n\n"

        for i, proj in enumerate(top_projects, 1):
            summary += f"{i}. {proj['title']} (Relevance: {proj['relevance_score']:.1f}%)\n"
            summary += f"   Source: Resume {proj.get('source_resume_id', 'Unknown')}\n"
            summary += f"   Technologies: {', '.join(proj['technologies'])}\n"
            summary += f"   Why relevant: {proj['reasoning']}\n"

            if proj.get('matched_skills'):
                summary += f"   Matched skills: {', '.join(proj['matched_skills'])}\n"

            summary += "\n"

        return summary
