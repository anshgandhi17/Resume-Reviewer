"""
Work experience extraction service for parsing experience from resume text.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class WorkExperience:
    """Represents a single work experience entry from a resume."""
    company: str
    title: str
    location: str
    date_range: str
    bullets: List[str]
    technologies: List[str]
    source_resume_id: Optional[str] = None
    raw_text: str = ""


class ExperienceExtractor:
    """Extract and parse individual work experiences from resume sections."""

    # Common technology keywords
    TECH_KEYWORDS = [
        'python', 'java', 'javascript', 'typescript', 'react', 'node', 'angular', 'vue',
        'django', 'flask', 'fastapi', 'spring', 'express', 'mongodb', 'postgresql',
        'mysql', 'redis', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'rest', 'graphql',
        'microservices', 'ci/cd', 'jenkins', 'github actions', 'terraform', 'ansible',
        'rabbitmq', 'kafka', 'elasticsearch', 'nginx', 'apache', 'linux',
        'go', 'rust', 'c++', 'c#', '.net', 'ruby', 'php', 'swift', 'kotlin', 'scala',
        'sql', 'nosql', 'api', 'rest api', 'graphql', 'agile', 'scrum', 'jira'
    ]

    @staticmethod
    def extract_experiences_from_text(resume_text: str, resume_id: Optional[str] = None) -> List[WorkExperience]:
        """
        Extract all work experiences from resume text.

        Args:
            resume_text: Full resume text
            resume_id: Optional identifier for the source resume

        Returns:
            List of WorkExperience objects
        """
        # First, try to find the experience section
        experience_section = ExperienceExtractor._find_experience_section(resume_text)

        if not experience_section:
            return []

        # Split into individual experiences
        experience_blocks = ExperienceExtractor._split_into_experiences(experience_section)

        # Parse each experience
        experiences = []
        for block in experience_blocks:
            experience = ExperienceExtractor._parse_experience_block(block, resume_id)
            if experience:
                experiences.append(experience)

        return experiences

    @staticmethod
    def _find_experience_section(text: str) -> Optional[str]:
        """Find the work experience section in resume text."""
        text_lower = text.lower()

        # Look for experience section header
        patterns = [
            r'(?:work\s+)?experience\s*\n',
            r'professional\s+experience\s*\n',
            r'employment\s+history\s*\n',
            r'work\s+history\s*\n',
            r'career\s+history\s*\n'
        ]

        start_idx = None
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                start_idx = match.start()
                break

        if start_idx is None:
            return None

        # Find the next section (or end of text)
        next_section_patterns = [
            r'\neducation\s*\n',
            r'\nprojects?\s*\n',
            r'\nskills?\s*\n',
            r'\ncertifications?\s*\n',
            r'\nawards?\s*\n',
            r'\npublications?\s*\n'
        ]

        end_idx = len(text)
        for pattern in next_section_patterns:
            match = re.search(pattern, text_lower[start_idx + 10:])
            if match:
                potential_end = start_idx + 10 + match.start()
                end_idx = min(end_idx, potential_end)

        return text[start_idx:end_idx].strip()

    @staticmethod
    def _split_into_experiences(experience_section: str) -> List[str]:
        """
        Split experience section into individual job blocks.

        Heuristics:
        - Jobs typically have company name, title, and dates
        - Jobs are separated by blank lines or date patterns
        """
        lines = experience_section.split('\n')
        experience_blocks = []
        current_block = []

        # Date pattern to detect new job entries
        date_pattern = r'\b(20\d{2}|19\d{2}|\d{1,2}/\d{4}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|present|current)\b'

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines between jobs
            if not stripped:
                if current_block and len(current_block) > 2:
                    experience_blocks.append('\n'.join(current_block))
                    current_block = []
                continue

            # Check if this line contains a date (likely a job header)
            has_date = re.search(date_pattern, stripped.lower())

            # If we detect a date and already have content, this might be a new job
            if has_date and current_block and len(current_block) > 3:
                # Check if previous line also had a date (could be continuation)
                prev_line = current_block[-1] if current_block else ""
                prev_has_date = re.search(date_pattern, prev_line.lower())

                if not prev_has_date:  # New job entry
                    experience_blocks.append('\n'.join(current_block))
                    current_block = [line]
                else:
                    current_block.append(line)
            else:
                current_block.append(line)

        # Add the last block
        if current_block and len(current_block) > 2:
            experience_blocks.append('\n'.join(current_block))

        return experience_blocks

    @staticmethod
    def _parse_experience_block(block: str, resume_id: Optional[str] = None) -> Optional[WorkExperience]:
        """Parse a single experience block into a WorkExperience object."""
        lines = [l.strip() for l in block.split('\n') if l.strip()]

        if len(lines) < 2:
            return None

        # Extract company, title, location, and dates
        # Common formats:
        # Line 1: Company Name | Location
        # Line 2: Job Title | Date Range
        # OR
        # Line 1: Job Title
        # Line 2: Company Name | Location | Date Range

        company = ""
        title = ""
        location = ""
        date_range = ""

        # Try to extract from first few lines
        header_lines = lines[:3]

        for line in header_lines:
            # Extract date range
            date_match = re.search(
                r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}\s*[-–]\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|'
                r'\d{4}\s*[-–]\s*\d{4}|'
                r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}\s*[-–]\s*(?:present|current)|'
                r'\d{1,2}/\d{4}\s*[-–]\s*\d{1,2}/\d{4})',
                line,
                re.IGNORECASE
            )
            if date_match:
                date_range = date_match.group(0)
                # Remove date from line for further parsing
                line = line.replace(date_range, '').strip()

            # Check for location (city, state/country patterns)
            location_match = re.search(
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}(?:\s+\d{5})?|'
                r'[A-Z][a-z]+,\s*[A-Z][a-z]+|'
                r'Remote|remote)',
                line
            )
            if location_match:
                location = location_match.group(0)
                line = line.replace(location, '').strip()

            # Parse remaining parts separated by |, -, or similar
            parts = re.split(r'\s*[|–-]\s*', line)
            parts = [p.strip() for p in parts if p.strip()]

            if parts:
                if not title:
                    title = parts[0]
                if not company and len(parts) > 1:
                    company = parts[1]
                elif not company:
                    company = parts[0]

        # Extract bullet points
        bullets = []
        for line in lines[2:]:  # Skip header lines
            # Check if it's a bullet point
            if re.match(r'^[\-\•\*\◦\▪\→]\s*', line):
                bullet = re.sub(r'^[\-\•\*\◦\▪\→]\s*', '', line).strip()
                bullets.append(bullet)
            elif line and not any(x in line.lower() for x in ['experience', 'skills', 'education']):
                # Could be a non-bulleted achievement
                if len(line) > 20 and not re.search(r'\d{4}', line):  # Not a date line
                    bullets.append(line)

        # Extract technologies
        technologies = ExperienceExtractor._extract_technologies(block)

        # Validate we have minimum required fields
        if not title or not bullets:
            return None

        return WorkExperience(
            company=company or "Unknown Company",
            title=title,
            location=location or "",
            date_range=date_range or "",
            bullets=bullets,
            technologies=technologies,
            source_resume_id=resume_id,
            raw_text=block
        )

    @staticmethod
    def _extract_technologies(text: str) -> List[str]:
        """Extract technology keywords from experience text."""
        text_lower = text.lower()
        found_techs = []

        for tech in ExperienceExtractor.TECH_KEYWORDS:
            # Use word boundaries to avoid partial matches
            if re.search(rf'\b{re.escape(tech)}\b', text_lower):
                found_techs.append(tech.title())

        # Remove duplicates while preserving order
        seen = set()
        unique_techs = []
        for tech in found_techs:
            tech_lower = tech.lower()
            if tech_lower not in seen:
                seen.add(tech_lower)
                unique_techs.append(tech)

        return unique_techs

    @staticmethod
    def combine_experiences_info(experiences: List[WorkExperience]) -> str:
        """
        Format a list of experiences into a readable summary.

        Args:
            experiences: List of WorkExperience objects

        Returns:
            Formatted string with all experiences
        """
        if not experiences:
            return "No work experiences found."

        output = []
        for i, exp in enumerate(experiences, 1):
            output.append(f"\n{i}. {exp.title} at {exp.company}")

            if exp.date_range:
                output.append(f"   {exp.date_range}")

            if exp.location:
                output.append(f"   Location: {exp.location}")

            if exp.technologies:
                output.append(f"   Technologies: {', '.join(exp.technologies)}")

            if exp.bullets:
                for bullet in exp.bullets:
                    output.append(f"   • {bullet}")

        return '\n'.join(output)
