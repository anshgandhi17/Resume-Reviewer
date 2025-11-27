"""
STAR Formatter Service
Rewrites resume bullets in STAR format without hallucination.

STAR Format:
- Situation: Context/challenge
- Task: What needed to be done
- Action: What you did (tools, methods)
- Result: Outcome (only if present in original)
"""

import logging
import re
from typing import Dict, List, Optional
import json

from langchain_community.llms import Ollama
from app.core.config import settings

logger = logging.getLogger(__name__)


class STARFormatter:
    """
    Formats resume bullets into STAR format with strict no-hallucination rules.

    Key Principles:
    1. Use ONLY information from the original bullet
    2. Do NOT add metrics, numbers, or percentages that don't exist
    3. Do NOT invent results or outcomes
    4. Preserve all technical terms exactly
    5. Mark missing STAR components as [NOT PROVIDED]
    """

    # STAR formatting prompt with strict rules
    STAR_PROMPT_TEMPLATE = """You are a resume formatting expert. Your task is to rewrite a resume bullet point in STAR format.

CRITICAL RULES - FOLLOW EXACTLY:
1. Use ONLY information from the original bullet point
2. Do NOT add ANY metrics, percentages, or numbers that don't exist in the original
3. Do NOT invent results or outcomes
4. Do NOT add technology names not mentioned
5. Preserve all technical terms, tools, and technologies EXACTLY as written
6. If a STAR component is missing from the original, write [NOT PROVIDED]
7. Do NOT embellish or exaggerate

Original Bullet Point:
{original_bullet}

Context:
Job Title: {job_title}
Company: {company}

Format the bullet point following this exact structure:

**Situation**: [Describe the context or challenge - if not in original, write "NOT PROVIDED"]
**Task**: [What needed to be done - if not in original, write "NOT PROVIDED"]
**Action**: [What you did, tools/methods used - extract from original]
**Result**: [Outcome - ONLY if explicitly stated in original, otherwise write "NOT PROVIDED"]

Write the STAR-formatted bullet below:
"""

    def __init__(self, llm=None):
        """
        Initialize STAR Formatter.

        Args:
            llm: Optional LLM instance. If not provided, creates new Ollama instance.
        """
        self.llm = llm or Ollama(
            base_url=settings.ollama_base_url,
            model=settings.star_llm_model,
            temperature=settings.star_temperature
        )
        logger.info(f"STAR Formatter initialized with model: {settings.star_llm_model}")

    def extract_bullets_from_text(self, resume_text: str) -> List[Dict]:
        """
        Extract bullet points from resume text.

        Args:
            resume_text: Full resume text

        Returns:
            List of bullet point dictionaries with text and context
        """
        bullets = []
        lines = resume_text.split('\n')

        current_job_title = None
        current_company = None
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            if re.match(r'(?i)(work\s+experience|professional\s+experience|experience)', line):
                current_section = 'experience'
                continue

            # Detect job titles and companies (heuristic)
            # Pattern: "Senior Software Engineer | Google" or "Software Engineer at Microsoft"
            job_match = re.match(r'^([A-Z][^|•\-]+?)(?:\s+(?:at|@|\|)\s+([A-Z][^•\-]+?))?$', line)
            if job_match and current_section == 'experience':
                current_job_title = job_match.group(1).strip()
                current_company = job_match.group(2).strip() if job_match.group(2) else None
                continue

            # Detect bullet points
            if line.startswith(('•', '-', '*', '◦')) or re.match(r'^\d+\.', line):
                # Clean bullet marker
                bullet_text = re.sub(r'^[•\-\*◦\d\.]+\s*', '', line).strip()

                if bullet_text:
                    bullets.append({
                        'original': bullet_text,
                        'job_title': current_job_title or 'Unknown',
                        'company': current_company or 'Unknown',
                        'section': current_section or 'unknown'
                    })

        logger.info(f"Extracted {len(bullets)} bullet points from resume")
        return bullets

    def format_bullet_to_star(
        self,
        original_bullet: str,
        job_title: str = "Unknown",
        company: str = "Unknown"
    ) -> Dict:
        """
        Format a single bullet point to STAR format.

        Args:
            original_bullet: Original bullet point text
            job_title: Job title for context
            company: Company name for context

        Returns:
            Dictionary with original and STAR-formatted bullet
        """
        try:
            # Generate prompt
            prompt = self.STAR_PROMPT_TEMPLATE.format(
                original_bullet=original_bullet,
                job_title=job_title,
                company=company
            )

            # Call LLM
            logger.debug(f"Formatting bullet: {original_bullet[:50]}...")
            star_formatted = self.llm.invoke(prompt).strip()

            # Parse STAR components
            situation = self._extract_star_component(star_formatted, "Situation")
            task = self._extract_star_component(star_formatted, "Task")
            action = self._extract_star_component(star_formatted, "Action")
            result = self._extract_star_component(star_formatted, "Result")

            return {
                'original': original_bullet,
                'star_formatted': star_formatted,
                'components': {
                    'situation': situation,
                    'task': task,
                    'action': action,
                    'result': result
                },
                'job_title': job_title,
                'company': company,
                'status': 'formatted'
            }

        except Exception as e:
            logger.error(f"Error formatting bullet: {str(e)}")
            return {
                'original': original_bullet,
                'star_formatted': None,
                'components': {},
                'job_title': job_title,
                'company': company,
                'status': 'failed',
                'error': str(e)
            }

    def _extract_star_component(self, star_text: str, component: str) -> str:
        """
        Extract a specific STAR component from formatted text.

        Args:
            star_text: Full STAR-formatted text
            component: Component name (Situation, Task, Action, Result)

        Returns:
            Extracted component text
        """
        pattern = rf'\*\*{component}\*\*:\s*(.+?)(?=\*\*|$)'
        match = re.search(pattern, star_text, re.IGNORECASE | re.DOTALL)

        if match:
            return match.group(1).strip()
        else:
            return "NOT PROVIDED"

    def format_resume_bullets(
        self,
        resume_text: str,
        filter_section: Optional[str] = None
    ) -> List[Dict]:
        """
        Format all bullets in a resume to STAR format.

        Args:
            resume_text: Full resume text
            filter_section: Optional section filter ('experience', 'projects', etc.)

        Returns:
            List of formatted bullet dictionaries
        """
        # Extract bullets
        bullets = self.extract_bullets_from_text(resume_text)

        # Filter by section if specified
        if filter_section:
            bullets = [b for b in bullets if b.get('section') == filter_section]

        # Format each bullet
        formatted_bullets = []
        for bullet in bullets:
            formatted = self.format_bullet_to_star(
                original_bullet=bullet['original'],
                job_title=bullet['job_title'],
                company=bullet['company']
            )
            formatted_bullets.append(formatted)

        logger.info(
            f"Formatted {len(formatted_bullets)} bullets. "
            f"Success: {sum(1 for b in formatted_bullets if b['status'] == 'formatted')}, "
            f"Failed: {sum(1 for b in formatted_bullets if b['status'] == 'failed')}"
        )

        return formatted_bullets

    def format_chunks_to_star(self, chunks: List[Dict]) -> List[Dict]:
        """
        Format bullets from semantic chunks to STAR format.

        Args:
            chunks: List of semantic chunks with metadata

        Returns:
            List of formatted bullet dictionaries
        """
        formatted_bullets = []

        for chunk in chunks:
            # Extract bullets from chunk text
            chunk_text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})

            job_title = metadata.get('job_title', 'Unknown')
            company = metadata.get('company', 'Unknown')
            chunk_type = metadata.get('chunk_type', '')

            # Only process experience and project chunks
            if chunk_type not in ['experience_item', 'project_item']:
                continue

            # Extract bullet points from chunk
            bullets = self.extract_bullets_from_text(chunk_text)

            # Format each bullet
            for bullet in bullets:
                formatted = self.format_bullet_to_star(
                    original_bullet=bullet['original'],
                    job_title=job_title,
                    company=company
                )
                formatted['chunk_id'] = chunk.get('id')
                formatted['chunk_type'] = chunk_type
                formatted_bullets.append(formatted)

        return formatted_bullets
