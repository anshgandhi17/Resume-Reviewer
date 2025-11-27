"""
Semantic Chunker Service
Intelligently chunks resumes by semantic boundaries (sections, experiences, etc.)
rather than fixed character counts.
"""

import re
from typing import List, Dict, Optional
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Chunks resumes into semantic units based on structure and content.
    Preserves context and adds meaningful metadata to each chunk.
    """

    # Common resume section headers
    SECTION_PATTERNS = {
        'summary': r'(?i)(professional\s+summary|summary|profile|objective|about\s+me)',
        'experience': r'(?i)(work\s+experience|professional\s+experience|experience|employment\s+history)',
        'education': r'(?i)(education|academic\s+background|qualifications)',
        'skills': r'(?i)(skills|technical\s+skills|core\s+competencies|expertise)',
        'projects': r'(?i)(projects|portfolio|notable\s+projects)',
        'certifications': r'(?i)(certifications|certificates|licenses)',
        'awards': r'(?i)(awards|honors|achievements)',
    }

    # Date patterns for experience timeline
    DATE_PATTERN = r'(?i)(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}|\d{4}|present|current'

    def __init__(self):
        self.section_patterns = {
            name: re.compile(pattern)
            for name, pattern in self.SECTION_PATTERNS.items()
        }
        self.date_pattern = re.compile(self.DATE_PATTERN)

    def chunk_resume(self, resume_text: str, resume_id: Optional[str] = None) -> List[Dict]:
        """
        Chunk a resume into semantic units.

        Args:
            resume_text: The full resume text
            resume_id: Optional resume identifier

        Returns:
            List of chunks with metadata
        """
        if resume_id is None:
            resume_id = str(uuid.uuid4())

        # Split text into lines for processing
        lines = resume_text.split('\n')

        # Identify section boundaries
        sections = self._identify_sections(lines)

        # Create chunks from sections
        chunks = []

        for section in sections:
            section_type = section['type']
            section_content = section['content']

            # For experience sections, create one chunk per job
            if section_type == 'experience':
                experience_chunks = self._chunk_experience_section(
                    section_content,
                    resume_id,
                    len(chunks)
                )
                chunks.extend(experience_chunks)

            # For projects, create one chunk per project
            elif section_type == 'projects':
                project_chunks = self._chunk_projects_section(
                    section_content,
                    resume_id,
                    len(chunks)
                )
                chunks.extend(project_chunks)

            # Other sections become single chunks
            else:
                chunk = self._create_chunk(
                    content=section_content,
                    chunk_type=section_type,
                    resume_id=resume_id,
                    chunk_index=len(chunks),
                    metadata={}
                )
                chunks.append(chunk)

        logger.info(f"Created {len(chunks)} semantic chunks from resume {resume_id}")
        return chunks

    def _identify_sections(self, lines: List[str]) -> List[Dict]:
        """Identify section boundaries in the resume."""
        sections = []
        current_section = {'type': 'unknown', 'content': '', 'start_line': 0}

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Check if this line is a section header
            section_type = self._match_section_header(line_stripped)

            if section_type:
                # Save previous section if it has content
                if current_section['content'].strip():
                    sections.append(current_section)

                # Start new section
                current_section = {
                    'type': section_type,
                    'content': '',
                    'start_line': i
                }
            else:
                # Add line to current section
                current_section['content'] += line + '\n'

        # Add final section
        if current_section['content'].strip():
            sections.append(current_section)

        return sections

    def _match_section_header(self, line: str) -> Optional[str]:
        """Check if a line matches any section header pattern."""
        for section_type, pattern in self.section_patterns.items():
            if pattern.match(line):
                return section_type
        return None

    def _chunk_experience_section(
        self,
        content: str,
        resume_id: str,
        start_index: int
    ) -> List[Dict]:
        """
        Chunk experience section by individual jobs.
        Each job becomes a separate chunk with preserved context.
        """
        chunks = []

        # Split by common job delimiters (company names, job titles)
        # Look for patterns like: "Job Title | Company Name" or "Company Name"
        job_blocks = self._split_experience_by_jobs(content)

        for i, job_block in enumerate(job_blocks):
            # Extract metadata from job block
            metadata = self._extract_job_metadata(job_block)

            chunk = self._create_chunk(
                content=job_block,
                chunk_type='experience',
                resume_id=resume_id,
                chunk_index=start_index + i,
                metadata=metadata
            )
            chunks.append(chunk)

        return chunks

    def _split_experience_by_jobs(self, content: str) -> List[str]:
        """Split experience section into individual job blocks."""
        # This is a simple heuristic - can be improved
        # Split on empty lines followed by text that looks like a job title/company

        lines = content.split('\n')
        jobs = []
        current_job = []
        blank_line_count = 0

        for line in lines:
            if not line.strip():
                blank_line_count += 1
                if current_job:
                    current_job.append(line)
            else:
                # If we had 2+ blank lines and current job has content, start new job
                if blank_line_count >= 2 and current_job:
                    jobs.append('\n'.join(current_job))
                    current_job = [line]
                else:
                    current_job.append(line)
                blank_line_count = 0

        # Add final job
        if current_job:
            jobs.append('\n'.join(current_job))

        # If no splits were found, return the whole content as one job
        return jobs if jobs else [content]

    def _extract_job_metadata(self, job_text: str) -> Dict:
        """Extract metadata from a job experience block."""
        metadata = {}

        # Extract dates
        dates = self.date_pattern.findall(job_text)
        if dates:
            metadata['date_range'] = ' - '.join(dates[:2]) if len(dates) >= 2 else dates[0]

        # Extract company and title (first 1-2 non-empty lines often contain these)
        lines = [l.strip() for l in job_text.split('\n') if l.strip()]
        if len(lines) >= 1:
            metadata['title_or_company'] = lines[0]

        # Extract keywords (simple: get capitalized words and technical terms)
        keywords = self._extract_keywords(job_text)
        metadata['keywords'] = keywords[:10]  # Top 10 keywords

        return metadata

    def _chunk_projects_section(
        self,
        content: str,
        resume_id: str,
        start_index: int
    ) -> List[Dict]:
        """Chunk projects section by individual projects."""
        chunks = []

        # Split by project delimiters (similar to jobs)
        project_blocks = self._split_experience_by_jobs(content)  # Reuse same logic

        for i, project_block in enumerate(project_blocks):
            metadata = self._extract_project_metadata(project_block)

            chunk = self._create_chunk(
                content=project_block,
                chunk_type='project',
                resume_id=resume_id,
                chunk_index=start_index + i,
                metadata=metadata
            )
            chunks.append(chunk)

        return chunks

    def _extract_project_metadata(self, project_text: str) -> Dict:
        """Extract metadata from a project block."""
        metadata = {}

        # Extract project name (usually first line)
        lines = [l.strip() for l in project_text.split('\n') if l.strip()]
        if lines:
            metadata['project_name'] = lines[0]

        # Extract keywords
        keywords = self._extract_keywords(project_text)
        metadata['keywords'] = keywords[:10]

        return metadata

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        # Common technical skills and important terms
        text_lower = text.lower()

        # Common tech keywords to look for
        tech_keywords = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws',
            'docker', 'kubernetes', 'git', 'machine learning', 'data analysis',
            'fastapi', 'django', 'flask', 'mongodb', 'postgresql', 'redis',
            'typescript', 'vue.js', 'angular', 'ci/cd', 'jenkins', 'terraform',
            'agile', 'scrum', 'rest api', 'microservices', 'cloud', 'azure',
            'gcp', 'testing', 'pytorch', 'tensorflow', 'api', 'backend',
            'frontend', 'full stack', 'devops', 'linux', 'bash', 'golang'
        ]

        found_keywords = []
        for keyword in tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords

    def _create_chunk(
        self,
        content: str,
        chunk_type: str,
        resume_id: str,
        chunk_index: int,
        metadata: Dict
    ) -> Dict:
        """Create a standardized chunk dictionary."""
        chunk_id = f"{resume_id}_chunk_{chunk_index}"

        return {
            'chunk_id': chunk_id,
            'resume_id': resume_id,
            'content': content.strip(),
            'chunk_type': chunk_type,
            'chunk_index': chunk_index,
            'metadata': {
                **metadata,
                'chunk_length': len(content),
                'created_at': datetime.utcnow().isoformat()
            }
        }

    def get_chunk_summary(self, chunk: Dict) -> str:
        """Get a human-readable summary of a chunk."""
        chunk_type = chunk['chunk_type']
        metadata = chunk['metadata']

        summary_parts = [f"Type: {chunk_type}"]

        if 'title_or_company' in metadata:
            summary_parts.append(f"Title/Company: {metadata['title_or_company']}")

        if 'date_range' in metadata:
            summary_parts.append(f"Date: {metadata['date_range']}")

        if 'keywords' in metadata and metadata['keywords']:
            summary_parts.append(f"Keywords: {', '.join(metadata['keywords'][:5])}")

        return ' | '.join(summary_parts)
