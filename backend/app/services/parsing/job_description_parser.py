"""
Job description parser with semantic chunking and metadata extraction.
Extracts structured requirements, skills, and qualifications from job descriptions.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """A single job requirement with metadata."""
    text: str
    category: str  # 'technical', 'soft_skill', 'experience', 'education', 'certification'
    priority: str  # 'required', 'preferred', 'nice_to_have'
    weight: float = 1.0  # Importance weight (0.0 - 1.0)
    years: Optional[int] = None  # Years of experience if specified
    level: Optional[str] = None  # 'junior', 'mid', 'senior', 'lead', 'principal'


@dataclass
class ParsedJobDescription:
    """Structured representation of a job description."""
    raw_text: str
    title: Optional[str] = None
    seniority_level: Optional[str] = None  # 'junior', 'mid', 'senior', 'lead', 'principal'

    # Categorized requirements
    required_skills: List[Requirement] = field(default_factory=list)
    preferred_skills: List[Requirement] = field(default_factory=list)

    # Specific categories
    technical_skills: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)

    # Experience and education
    years_experience_required: Optional[int] = None
    education_requirements: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

    # All requirements with weights
    all_requirements: List[Requirement] = field(default_factory=list)


class JobDescriptionParser:
    """Parse and extract structured information from job descriptions."""

    # Common technical skills and tools
    TECHNICAL_KEYWORDS = {
        # Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'ruby',
        'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'sql',

        # Frameworks
        'react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'spring', 'express',
        'node.js', 'nodejs', 'next.js', 'nuxt', '.net', 'asp.net', 'laravel',

        # Cloud & Infrastructure
        'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'k8s', 'terraform',
        'ansible', 'jenkins', 'ci/cd', 'github actions', 'gitlab', 'circleci',

        # Databases
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb',
        'cassandra', 'oracle', 'sql server', 'sqlite', 'mariadb',

        # Data & ML
        'machine learning', 'deep learning', 'nlp', 'computer vision', 'tensorflow',
        'pytorch', 'scikit-learn', 'pandas', 'numpy', 'spark', 'hadoop', 'kafka',

        # Other
        'git', 'rest api', 'graphql', 'microservices', 'agile', 'scrum', 'jira'
    }

    # Soft skills keywords
    SOFT_SKILL_KEYWORDS = {
        'communication', 'leadership', 'teamwork', 'problem-solving', 'analytical',
        'creative', 'adaptable', 'self-motivated', 'detail-oriented', 'organized',
        'time management', 'collaboration', 'mentoring', 'presentation', 'writing'
    }

    # Seniority level indicators
    SENIORITY_LEVELS = {
        'junior': ['junior', 'entry level', 'entry-level', 'associate', 'jr'],
        'mid': ['mid-level', 'intermediate', 'mid level', 'ii', 'iii'],
        'senior': ['senior', 'sr', 'lead', 'staff', 'principal', 'architect']
    }

    def parse(self, job_description: str, job_title: Optional[str] = None) -> ParsedJobDescription:
        """
        Parse a job description into structured components.

        Args:
            job_description: Raw job description text
            job_title: Optional job title

        Returns:
            ParsedJobDescription with extracted metadata
        """
        logger.info("Parsing job description")

        parsed = ParsedJobDescription(raw_text=job_description, title=job_title)

        # Extract seniority level
        parsed.seniority_level = self._extract_seniority_level(job_description, job_title)

        # Extract years of experience
        parsed.years_experience_required = self._extract_years_experience(job_description)

        # Extract education requirements
        parsed.education_requirements = self._extract_education(job_description)

        # Extract certifications
        parsed.certifications = self._extract_certifications(job_description)

        # Extract and categorize requirements
        requirements = self._extract_requirements(job_description)

        for req in requirements:
            # Categorize as technical or soft skill
            req_lower = req.text.lower()

            # Determine category
            if any(tech in req_lower for tech in self.TECHNICAL_KEYWORDS):
                req.category = 'technical'
            elif any(soft in req_lower for soft in self.SOFT_SKILL_KEYWORDS):
                req.category = 'soft_skill'
            elif any(kw in req_lower for kw in ['year', 'experience']):
                req.category = 'experience'
            elif any(kw in req_lower for kw in ['degree', 'bachelor', 'master', 'phd']):
                req.category = 'education'
            elif any(kw in req_lower for kw in ['certification', 'certified']):
                req.category = 'certification'
            else:
                req.category = 'technical'  # Default to technical

            # Determine priority and weight
            if any(kw in req_lower for kw in ['required', 'must have', 'must-have', 'essential']):
                req.priority = 'required'
                req.weight = 1.0
            elif any(kw in req_lower for kw in ['preferred', 'nice to have', 'nice-to-have', 'bonus', 'plus']):
                req.priority = 'preferred'
                req.weight = 0.6
            else:
                # Infer from position in text (requirements at top are usually more important)
                req.priority = 'required'
                req.weight = 0.8

            # Extract years if mentioned
            years_match = re.search(r'(\d+)\+?\s*years?', req_lower)
            if years_match:
                req.years = int(years_match.group(1))

            # Add to appropriate lists
            if req.priority == 'required':
                parsed.required_skills.append(req)
            else:
                parsed.preferred_skills.append(req)

            if req.category == 'technical':
                # Extract specific technologies mentioned
                for tech in self.TECHNICAL_KEYWORDS:
                    if tech in req_lower and tech not in parsed.technical_skills:
                        parsed.technical_skills.append(tech)
            elif req.category == 'soft_skill':
                for skill in self.SOFT_SKILL_KEYWORDS:
                    if skill in req_lower and skill not in parsed.soft_skills:
                        parsed.soft_skills.append(skill)

            parsed.all_requirements.append(req)

        logger.info(f"Extracted {len(parsed.required_skills)} required and "
                   f"{len(parsed.preferred_skills)} preferred requirements")

        return parsed

    def _extract_seniority_level(self, text: str, title: Optional[str] = None) -> Optional[str]:
        """Extract seniority level from job description or title."""
        combined_text = (title or '') + ' ' + text
        combined_lower = combined_text.lower()

        for level, keywords in self.SENIORITY_LEVELS.items():
            if any(keyword in combined_lower for keyword in keywords):
                return level

        return None

    def _extract_years_experience(self, text: str) -> Optional[int]:
        """Extract required years of experience."""
        # Look for patterns like "5+ years", "3-5 years", "minimum 5 years"
        patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'minimum\s+(\d+)\s+years?',
            r'at least\s+(\d+)\s+years?',
            r'(\d+)-\d+\s+years?'
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))

        return None

    def _extract_education(self, text: str) -> List[str]:
        """Extract education requirements."""
        education = []
        text_lower = text.lower()

        degrees = [
            ('phd', 'PhD'),
            ('doctorate', 'Doctorate'),
            ('master', "Master's Degree"),
            ('mba', 'MBA'),
            ('bachelor', "Bachelor's Degree"),
            ('bs ', "Bachelor's Degree"),
            ('ba ', "Bachelor's Degree"),
            ('associate', "Associate's Degree")
        ]

        for keyword, formal_name in degrees:
            if keyword in text_lower and formal_name not in education:
                education.append(formal_name)

        return education

    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certification requirements."""
        certifications = []

        # Common certifications
        cert_patterns = [
            r'AWS\s+Certified',
            r'Azure\s+Certified',
            r'GCP\s+Certified',
            r'PMP',
            r'Scrum\s+Master',
            r'CISSP',
            r'Security\+',
            r'CKA',
            r'CKAD'
        ]

        for pattern in cert_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                cert = match.group(0)
                if cert not in certifications:
                    certifications.append(cert)

        return certifications

    def _extract_requirements(self, text: str) -> List[Requirement]:
        """Extract individual requirements from job description."""
        requirements = []

        # Split into lines and bullet points
        lines = text.split('\n')

        for line in lines:
            line = line.strip()

            # Skip empty lines and very short lines
            if len(line) < 10:
                continue

            # Clean bullet points
            line = re.sub(r'^[•\-\*]\s*', '', line)

            # Split by semicolons and commas for compound requirements
            sub_items = re.split(r'[;,](?=\s)', line)

            for item in sub_items:
                item = item.strip()

                # Skip if too short or just a header
                if len(item) < 15:
                    continue

                # Skip common section headers
                if any(header in item.lower() for header in [
                    'responsibilities:', 'requirements:', 'qualifications:',
                    'skills:', 'about us', 'company description', 'benefits:'
                ]):
                    continue

                # Create requirement
                req = Requirement(text=item, category='unknown', priority='required')
                requirements.append(req)

        # If we didn't find many requirements via line splitting, try sentence splitting
        if len(requirements) < 5:
            sentences = re.split(r'[.!?]\s+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:
                    req = Requirement(text=sentence, category='unknown', priority='required')
                    requirements.append(req)

        logger.info(f"Extracted {len(requirements)} raw requirements")
        return requirements

    def get_weighted_requirements_text(self, parsed: ParsedJobDescription) -> List[tuple]:
        """
        Get requirements as (text, weight) tuples for ranking.

        Args:
            parsed: ParsedJobDescription object

        Returns:
            List of (requirement_text, weight) tuples
        """
        weighted = []

        for req in parsed.all_requirements:
            weighted.append((req.text, req.weight))

        # Add full description with lower weight for holistic matching
        weighted.append((parsed.raw_text, 0.3))

        return weighted
