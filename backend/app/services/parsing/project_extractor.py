"""
Project extraction service for parsing projects from resume text.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Project:
    """Represents a single project from a resume."""
    title: str
    description: str
    technologies: List[str]
    bullets: List[str]
    source_resume_id: Optional[str] = None
    raw_text: str = ""


class ProjectExtractor:
    """Extract and parse individual projects from resume sections."""

    # Common technology keywords
    TECH_KEYWORDS = [
        'python', 'java', 'javascript', 'typescript', 'react', 'node', 'angular', 'vue',
        'django', 'flask', 'fastapi', 'spring', 'express', 'mongodb', 'postgresql',
        'mysql', 'redis', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'rest', 'graphql',
        'microservices', 'ci/cd', 'jenkins', 'github actions', 'terraform', 'ansible',
        'rabbitmq', 'kafka', 'elasticsearch', 'redis', 'nginx', 'apache', 'linux',
        'go', 'rust', 'c++', 'c#', '.net', 'ruby', 'php', 'swift', 'kotlin', 'scala'
    ]

    @staticmethod
    def extract_projects_from_text(resume_text: str, resume_id: Optional[str] = None) -> List[Project]:
        """
        Extract all projects from resume text.

        Args:
            resume_text: Full resume text
            resume_id: Optional identifier for the source resume

        Returns:
            List of Project objects
        """
        # First, try to find the projects section
        projects_section = ProjectExtractor._find_projects_section(resume_text)

        if not projects_section:
            return []

        # Split into individual projects
        project_blocks = ProjectExtractor._split_into_projects(projects_section)

        # Parse each project
        projects = []
        for block in project_blocks:
            project = ProjectExtractor._parse_project_block(block, resume_id)
            if project:
                projects.append(project)

        return projects

    @staticmethod
    def _find_projects_section(text: str) -> Optional[str]:
        """Find the projects section in resume text."""
        text_lower = text.lower()

        # Look for projects section header
        patterns = [
            r'projects?\s*\n',
            r'personal\s+projects?\s*\n',
            r'portfolio\s*\n',
            r'key\s+projects?\s*\n',
            r'selected\s+projects?\s*\n'
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
            r'\n(?:work\s+)?experience\s*\n',
            r'\neducation\s*\n',
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
    def _split_into_projects(projects_section: str) -> List[str]:
        """
        Split projects section into individual project blocks.

        Heuristics:
        - Projects often start with a bold/capitalized title
        - Projects are separated by blank lines or clear headers
        - Look for patterns like "Project Name | Technology Stack"
        """
        lines = projects_section.split('\n')
        project_blocks = []
        current_block = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines between projects
            if not stripped:
                if current_block:
                    project_blocks.append('\n'.join(current_block))
                    current_block = []
                continue

            # Check if this looks like a new project title
            # (all caps, or has pipe separator, or ends with colon)
            is_title = (
                stripped.isupper() or
                '|' in stripped or
                stripped.endswith(':') or
                (i > 0 and not lines[i-1].strip())  # Follows blank line
            )

            # If we detect a new project and already have content, save the previous
            if is_title and current_block and len(current_block) > 2:
                project_blocks.append('\n'.join(current_block))
                current_block = [line]
            else:
                current_block.append(line)

        # Add the last block
        if current_block:
            project_blocks.append('\n'.join(current_block))

        return project_blocks

    @staticmethod
    def _parse_project_block(block: str, resume_id: Optional[str] = None) -> Optional[Project]:
        """Parse a single project block into a Project object."""
        lines = [l.strip() for l in block.split('\n') if l.strip()]

        if len(lines) < 2:
            return None

        # First line is usually the title (may include tech stack)
        title_line = lines[0]

        # Extract title and technologies from first line
        if '|' in title_line:
            parts = title_line.split('|')
            title = parts[0].strip()
            tech_string = parts[1].strip() if len(parts) > 1 else ""
        else:
            title = title_line.strip(':').strip()
            tech_string = ""

        # Extract bullet points (lines starting with -, •, *, or similar)
        bullets = []
        description_lines = []

        for line in lines[1:]:
            # Check if it's a bullet point
            if re.match(r'^[\-\•\*\◦\▪\→]\s*', line):
                bullet = re.sub(r'^[\-\•\*\◦\▪\→]\s*', '', line).strip()
                bullets.append(bullet)
            elif line and not line.startswith('Technologies:'):
                description_lines.append(line)

        # Combine description
        description = ' '.join(description_lines) if description_lines else ''

        # Extract technologies
        technologies = ProjectExtractor._extract_technologies(block, tech_string)

        return Project(
            title=title,
            description=description,
            technologies=technologies,
            bullets=bullets,
            source_resume_id=resume_id,
            raw_text=block
        )

    @staticmethod
    def _extract_technologies(text: str, tech_string: str = "") -> List[str]:
        """Extract technology keywords from project text."""
        text_lower = (text + ' ' + tech_string).lower()
        found_techs = []

        for tech in ProjectExtractor.TECH_KEYWORDS:
            # Use word boundaries to avoid partial matches
            if re.search(rf'\b{re.escape(tech)}\b', text_lower):
                found_techs.append(tech.title())

        # Also look for technologies explicitly listed
        tech_patterns = [
            r'technologies?:\s*([^\n]+)',
            r'tech\s+stack:\s*([^\n]+)',
            r'built\s+with:\s*([^\n]+)'
        ]

        for pattern in tech_patterns:
            match = re.search(pattern, text_lower)
            if match:
                tech_list = match.group(1)
                # Split by common delimiters
                techs = re.split(r'[,;|]', tech_list)
                for tech in techs:
                    tech = tech.strip().title()
                    if tech and len(tech) > 2:
                        found_techs.append(tech)

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
    def combine_projects_info(projects: List[Project]) -> str:
        """
        Format a list of projects into a readable summary.

        Args:
            projects: List of Project objects

        Returns:
            Formatted string with all projects
        """
        if not projects:
            return "No projects found."

        output = []
        for i, project in enumerate(projects, 1):
            output.append(f"\n{i}. {project.title}")

            if project.technologies:
                output.append(f"   Technologies: {', '.join(project.technologies)}")

            if project.description:
                output.append(f"   {project.description}")

            if project.bullets:
                for bullet in project.bullets:
                    output.append(f"   • {bullet}")

        return '\n'.join(output)
