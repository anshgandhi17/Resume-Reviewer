import pdfplumber
from typing import Dict
import re


class PDFParser:
    """Extract text and metadata from PDF resumes."""

    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """Extract all text from a PDF file."""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise ValueError(f"Error parsing PDF: {str(e)}")

        return text.strip()

    @staticmethod
    def extract_sections(text: str) -> Dict[str, str]:
        """
        Extract common resume sections.
        This is a simple implementation - can be enhanced with NLP.
        """
        sections = {}

        # Common section headers
        section_patterns = {
            "summary": r"(?:professional\s+)?summary|(?:career\s+)?objective",
            "experience": r"(?:work\s+)?experience|(?:professional\s+)?experience|employment\s+history",
            "education": r"education|academic\s+background",
            "skills": r"(?:technical\s+)?skills|competencies|expertise",
            "projects": r"projects|portfolio",
            "certifications": r"certifications?|licenses?",
        }

        text_lower = text.lower()

        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                start_idx = match.start()
                # Find the next section or end of text
                next_section = len(text)
                for other_pattern in section_patterns.values():
                    other_match = re.search(other_pattern, text_lower[start_idx + 10:])
                    if other_match:
                        potential_end = start_idx + 10 + other_match.start()
                        next_section = min(next_section, potential_end)

                sections[section_name] = text[start_idx:next_section].strip()

        return sections

    @staticmethod
    def extract_contact_info(text: str) -> Dict[str, str]:
        """Extract basic contact information."""
        contact = {}

        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            contact["email"] = email_match.group(0)

        # Phone (simple pattern)
        phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
        if phone_match:
            contact["phone"] = phone_match.group(0)

        # LinkedIn
        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text.lower())
        if linkedin_match:
            contact["linkedin"] = linkedin_match.group(0)

        return contact
