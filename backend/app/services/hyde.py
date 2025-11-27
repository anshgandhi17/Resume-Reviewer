"""
HyDE (Hypothetical Document Embeddings) Service
Generates hypothetical resume bullets that would match a job description
to improve retrieval quality.
"""

from typing import List, Dict
import logging
import re
import json

from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from app.core.config import settings

logger = logging.getLogger(__name__)


class HyDEService:
    """
    Implements HyDE (Hypothetical Document Embeddings) for query expansion.

    Instead of directly searching with the job description, we generate
    hypothetical "ideal" resume bullets that would perfectly match the job,
    then use those for retrieval.
    """

    def __init__(self, llm=None):
        """
        Initialize HyDE service.

        Args:
            llm: Optional LLM instance. If not provided, creates new Ollama instance.
        """
        self.llm = llm or Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model
        )

    def generate_hypothetical_documents(
        self,
        job_description: str,
        num_documents: int = 5,
        temperature: float = 0.7
    ) -> List[str]:
        """
        Generate hypothetical resume bullets that would match the job description.

        Args:
            job_description: The job description text
            num_documents: Number of hypothetical documents to generate
            temperature: LLM temperature for generation diversity

        Returns:
            List of hypothetical resume bullets
        """
        try:
            prompt = PromptTemplate(
                input_variables=["job_description", "num_documents"],
                template="""You are an expert resume writer. Based on the following job description, generate {num_documents} hypothetical resume bullet points that would be PERFECT matches for this role.

Job Description:
{job_description}

Requirements:
1. Each bullet should describe a specific achievement or responsibility
2. Use action verbs and quantify results where possible
3. Include relevant technical skills and tools mentioned in the job description
4. Write in past tense (e.g., "Developed", "Led", "Implemented")
5. Make each bullet 1-2 sentences maximum
6. Focus on different aspects of the role (technical skills, leadership, impact, etc.)

Generate {num_documents} distinct, high-quality resume bullets that would make a candidate stand out for this position.

Format your response as a JSON array of strings:
["bullet 1", "bullet 2", "bullet 3", ...]"""
            )

            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                job_description=job_description,
                num_documents=num_documents
            )

            # Parse JSON response
            hypothetical_docs = self._parse_response(response)

            # Fallback if parsing fails
            if not hypothetical_docs:
                logger.warning("Failed to parse HyDE response, using fallback")
                hypothetical_docs = self._generate_fallback_documents(job_description)

            logger.info(f"Generated {len(hypothetical_docs)} hypothetical documents")
            return hypothetical_docs[:num_documents]

        except Exception as e:
            logger.error(f"Error generating hypothetical documents: {str(e)}")
            # Return fallback documents
            return self._generate_fallback_documents(job_description)

    def generate_hypothetical_experiences(
        self,
        job_description: str,
        num_experiences: int = 3
    ) -> List[Dict[str, str]]:
        """
        Generate hypothetical work experiences (not just bullets).

        Args:
            job_description: The job description text
            num_experiences: Number of experiences to generate

        Returns:
            List of experience dictionaries with title, company, and bullets
        """
        try:
            prompt = PromptTemplate(
                input_variables=["job_description", "num_experiences"],
                template="""Based on this job description, generate {num_experiences} hypothetical work experiences that would make someone a perfect candidate.

Job Description:
{job_description}

For each experience, provide:
- Job title
- Company (can be generic like "Tech Company" or "Financial Services Firm")
- 2-3 bullet points describing key achievements

Format as JSON:
[
    {{
        "title": "Job Title",
        "company": "Company Name",
        "bullets": ["Achievement 1", "Achievement 2", "Achievement 3"]
    }}
]"""
            )

            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                job_description=job_description,
                num_experiences=num_experiences
            )

            # Parse JSON response
            experiences = self._parse_json_response(response)

            if not experiences:
                logger.warning("Failed to parse experiences, using fallback")
                experiences = self._generate_fallback_experiences(job_description)

            logger.info(f"Generated {len(experiences)} hypothetical experiences")
            return experiences[:num_experiences]

        except Exception as e:
            logger.error(f"Error generating hypothetical experiences: {str(e)}")
            return self._generate_fallback_experiences(job_description)

    def expand_query(
        self,
        job_description: str,
        strategy: str = 'bullets'
    ) -> Dict[str, any]:
        """
        Expand a job description query using HyDE.

        Args:
            job_description: The job description text
            strategy: 'bullets' or 'experiences' - type of expansion to use

        Returns:
            Dictionary with original query and generated hypothetical documents
        """
        if strategy == 'bullets':
            hypothetical_docs = self.generate_hypothetical_documents(job_description)
            return {
                'original_query': job_description,
                'hypothetical_documents': hypothetical_docs,
                'strategy': 'bullets',
                'count': len(hypothetical_docs)
            }
        elif strategy == 'experiences':
            experiences = self.generate_hypothetical_experiences(job_description)

            # Flatten experiences into text chunks
            hypothetical_docs = []
            for exp in experiences:
                exp_text = f"{exp['title']} at {exp['company']}\n"
                exp_text += '\n'.join(f"• {bullet}" for bullet in exp['bullets'])
                hypothetical_docs.append(exp_text)

            return {
                'original_query': job_description,
                'hypothetical_documents': hypothetical_docs,
                'hypothetical_experiences': experiences,
                'strategy': 'experiences',
                'count': len(experiences)
            }
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _parse_response(self, response: str) -> List[str]:
        """Parse LLM response to extract list of strings."""
        try:
            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                bullets = json.loads(json_match.group())
                if isinstance(bullets, list):
                    return [str(b) for b in bullets if b]
        except json.JSONDecodeError:
            pass

        # Fallback: split by newlines and extract bullet points
        lines = response.split('\n')
        bullets = []
        for line in lines:
            line = line.strip()
            # Remove bullet markers
            line = re.sub(r'^[\d\.\-\*•]+\s*', '', line)
            if line and len(line) > 20:  # At least 20 chars
                bullets.append(line)

        return bullets

    def _parse_json_response(self, response: str) -> List[Dict]:
        """Parse LLM response to extract JSON array."""
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    return data
        except json.JSONDecodeError:
            pass

        return []

    def _generate_fallback_documents(self, job_description: str) -> List[str]:
        """
        Generate fallback hypothetical documents using rule-based approach.
        Used when LLM generation fails.
        """
        # Extract key requirements from job description
        text_lower = job_description.lower()

        fallback_bullets = []

        # Technical skills pattern
        if any(skill in text_lower for skill in ['python', 'java', 'javascript']):
            fallback_bullets.append(
                "Developed and maintained production applications using modern programming languages, "
                "improving system performance by 30%"
            )

        # Leadership pattern
        if any(word in text_lower for word in ['lead', 'manage', 'team']):
            fallback_bullets.append(
                "Led cross-functional team of 5+ engineers to deliver critical projects on time "
                "and within budget"
            )

        # Data/Analytics pattern
        if any(word in text_lower for word in ['data', 'analytics', 'analysis']):
            fallback_bullets.append(
                "Analyzed large datasets to identify trends and insights, resulting in data-driven "
                "decisions that increased revenue by 25%"
            )

        # Cloud/Infrastructure pattern
        if any(word in text_lower for word in ['aws', 'cloud', 'azure', 'gcp']):
            fallback_bullets.append(
                "Designed and implemented scalable cloud infrastructure, reducing operational costs "
                "by 40% while improving system reliability"
            )

        # Testing/Quality pattern
        if any(word in text_lower for word in ['test', 'quality', 'qa']):
            fallback_bullets.append(
                "Implemented comprehensive testing framework, increasing code coverage from 60% to 95% "
                "and reducing production bugs by 50%"
            )

        # Default fallback if no patterns matched
        if not fallback_bullets:
            fallback_bullets = [
                "Delivered high-impact projects that improved business outcomes and user satisfaction",
                "Collaborated with stakeholders to define requirements and implement solutions",
                "Applied best practices and modern technologies to solve complex problems"
            ]

        return fallback_bullets[:5]

    def _generate_fallback_experiences(self, job_description: str) -> List[Dict]:
        """Generate fallback experiences using rule-based approach."""
        return [
            {
                "title": "Software Engineer",
                "company": "Technology Company",
                "bullets": [
                    "Developed features aligned with role requirements",
                    "Collaborated with team members on technical solutions",
                    "Delivered projects that improved business metrics"
                ]
            }
        ]
