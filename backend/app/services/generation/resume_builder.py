"""
Resume builder service - generates optimized resumes from ranked projects.
"""

from typing import List, Dict, Optional
from ..parsing.project_extractor import Project
from ..parsing.pdf_parser import PDFParser
import logging

logger = logging.getLogger(__name__)


class ResumeBuilder:
    """Build optimized resumes from ranked projects and resume data."""

    @staticmethod
    def build_resume_data(
        ranked_projects: List[Dict],
        contact_info: Dict[str, str],
        skills: List[str],
        name: str = "Your Name",
        job_title: str = "Software Engineer",
        summary: Optional[str] = None,
        education: Optional[List[Dict]] = None,
        ranked_experiences: Optional[List[Dict]] = None,
        top_k_projects: int = 3,
        top_k_experiences: int = 3
    ) -> Dict:
        """
        Build resume data dictionary for LaTeX rendering.

        Args:
            ranked_projects: List of ranked project dicts
            contact_info: Dict with email, phone, linkedin, etc.
            skills: List of skill strings
            name: Candidate name
            job_title: Target job title
            summary: Optional professional summary
            education: Optional list of education entries
            ranked_experiences: Optional list of ranked work experiences
            top_k_projects: Number of top projects to include
            top_k_experiences: Number of top experiences to include

        Returns:
            Dict with resume data formatted for LaTeX template
        """
        # Select top K projects
        top_projects = ranked_projects[:top_k_projects] if ranked_projects else []

        # Build projects section
        projects_section = []
        for proj in top_projects:
            project_entry = {
                'name': proj['title'],
                'technologies': ', '.join(proj['technologies'][:8]) if proj['technologies'] else '',
                'bullets': proj['bullets'][:4],  # Limit to 4 bullets per project
                'date': ''  # No date for projects from multiple resumes
            }
            projects_section.append(project_entry)

        # Select top K experiences
        top_experiences = ranked_experiences[:top_k_experiences] if ranked_experiences else []

        # Build experience section
        experience_section = []
        for exp in top_experiences:
            # Parse title to extract company
            title_parts = exp['title'].split(' at ')
            job_title_exp = title_parts[0] if len(title_parts) > 0 else exp['title']
            company = title_parts[1] if len(title_parts) > 1 else 'Unknown Company'

            # Parse description for date and location
            description_parts = exp.get('description', '').split(' | ')
            date_range = description_parts[0] if len(description_parts) > 0 else ''
            location = description_parts[1] if len(description_parts) > 1 else ''

            experience_entry = {
                'company': company,
                'title': job_title_exp,
                'location': location or '',
                'date_range': date_range or '',
                'bullets': exp['bullets'][:4]  # Limit to 4 bullets per experience
            }
            experience_section.append(experience_entry)

        # Build skills section (unique skills from all projects and experiences)
        all_skills = set(skills)
        for proj in top_projects:
            if proj.get('technologies'):
                all_skills.update(proj['technologies'])
            if proj.get('matched_skills'):
                all_skills.update(proj['matched_skills'])

        for exp in top_experiences:
            if exp.get('technologies'):
                all_skills.update(exp['technologies'])
            if exp.get('matched_skills'):
                all_skills.update(exp['matched_skills'])

        # Group skills by category
        skill_categories = ResumeBuilder._categorize_skills(list(all_skills))

        # Format skills for LaTeX template
        skills_formatted = []
        for category, items in skill_categories.items():
            skills_formatted.append({
                'category': category,
                'items': ': ' + ', '.join(items)
            })

        # Build resume data
        resume_data = {
            'name': name,
            'email': contact_info.get('email', 'your.email@example.com'),
            'phone': contact_info.get('phone', '123-456-7890'),
            'linkedin_url': f"https://{contact_info['linkedin']}" if contact_info.get('linkedin') else '',
            'github_url': '',
            'website': '',
            'skills': skills_formatted,
            'projects': projects_section,
            'education': education or [],
            'experience': experience_section
        }

        return resume_data

    @staticmethod
    def extract_contact_from_resume(resume_text: str) -> Dict[str, str]:
        """
        Extract contact information from resume text.

        Args:
            resume_text: Full resume text

        Returns:
            Dict with contact info (email, phone, linkedin, etc.)
        """
        return PDFParser.extract_contact_info(resume_text)

    @staticmethod
    def extract_name_from_resume(resume_text: str) -> str:
        """
        Extract candidate name from resume (first line heuristic).

        Args:
            resume_text: Full resume text

        Returns:
            Candidate name or default
        """
        lines = resume_text.strip().split('\n')
        if lines:
            # First line is usually the name
            first_line = lines[0].strip()
            # Check if it looks like a name (not too long, no special chars)
            if len(first_line) < 50 and not any(char in first_line for char in ['@', 'http', '|']):
                return first_line

        return "Your Name"

    @staticmethod
    def _categorize_skills(skills: List[str]) -> Dict[str, List[str]]:
        """
        Categorize skills into groups.

        Args:
            skills: List of skill strings

        Returns:
            Dict with categorized skills
        """
        # Define skill categories
        languages = ['python', 'java', 'javascript', 'typescript', 'go', 'rust', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'scala']
        frameworks = ['react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'spring', 'express', 'node', '.net', 'rails']
        databases = ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb', 'cassandra']
        cloud_devops = ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible', 'jenkins', 'github actions', 'ci/cd']
        tools = ['git', 'linux', 'nginx', 'apache', 'rabbitmq', 'kafka']

        categorized = {
            'Languages': [],
            'Frameworks': [],
            'Databases': [],
            'Cloud & DevOps': [],
            'Tools': []
        }

        skills_lower = [s.lower() for s in skills]

        for skill in skills:
            skill_lower = skill.lower()

            if skill_lower in languages:
                categorized['Languages'].append(skill)
            elif skill_lower in frameworks:
                categorized['Frameworks'].append(skill)
            elif skill_lower in databases:
                categorized['Databases'].append(skill)
            elif skill_lower in cloud_devops:
                categorized['Cloud & DevOps'].append(skill)
            elif skill_lower in tools:
                categorized['Tools'].append(skill)
            else:
                # Default to Tools
                categorized['Tools'].append(skill)

        # Remove empty categories
        categorized = {k: v for k, v in categorized.items() if v}

        return categorized

    @staticmethod
    def _generate_summary(job_title: str, projects: List[Dict]) -> str:
        """
        Generate a professional summary based on projects.

        Args:
            job_title: Target job title
            projects: List of project dicts

        Returns:
            Professional summary string
        """
        # Extract key technologies
        all_techs = set()
        for proj in projects[:3]:
            if proj.get('technologies'):
                all_techs.update(proj['technologies'][:5])

        tech_list = ', '.join(list(all_techs)[:6])

        summary = (
            f"Results-driven {job_title} with proven expertise in {tech_list}. "
            f"Demonstrated ability to deliver high-impact projects with measurable results. "
            f"Strong problem-solving skills and experience in full software development lifecycle."
        )

        return summary

    @staticmethod
    def extract_education_from_resume(resume_text: str) -> List[Dict]:
        """
        Extract education entries from resume.

        Args:
            resume_text: Full resume text

        Returns:
            List of education dicts
        """
        sections = PDFParser.extract_sections(resume_text)
        education_text = sections.get('education', '')

        if not education_text:
            return []

        # Simple parsing - look for degree and university
        import re
        education_entries = []

        # Look for degree patterns
        degree_patterns = [
            r'(Bachelor|Master|PhD|B\.S\.|M\.S\.|B\.A\.|M\.A\.).*',
            r'(BS|MS|BA|MA|Ph\.D\.).*'
        ]

        lines = education_text.split('\n')
        current_entry = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for degree
            for pattern in degree_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if current_entry:
                        education_entries.append(current_entry)
                    current_entry = {'degree': line}
                    break

        if current_entry:
            education_entries.append(current_entry)

        return education_entries
