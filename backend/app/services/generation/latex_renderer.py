"""
LaTeX Renderer Service
Compiles LaTeX templates to PDF using pdflatex.
"""

import os
import subprocess
import tempfile
import logging
import re
from pathlib import Path
from typing import Dict, Optional
import shutil

from jinja2 import Template, Environment, FileSystemLoader
from app.core.config import settings

logger = logging.getLogger(__name__)


class LaTeXRenderer:
    """
    Renders LaTeX templates to PDF files.

    Requires pdflatex to be installed on the system:
    - Linux/Mac: sudo apt-get install texlive-full (or brew install mactex)
    - Windows: Install MiKTeX or TeX Live
    """

    # LaTeX special characters that need escaping
    LATEX_SPECIAL_CHARS = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
    }

    def __init__(self, template_path: Optional[Path] = None):
        """
        Initialize LaTeX Renderer.

        Args:
            template_path: Path to LaTeX template file
        """
        self.template_path = template_path or settings.pdf_template_path

        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        # Setup Jinja2 environment
        template_dir = self.template_path.parent
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            block_start_string='<%',
            block_end_string='%>',
            variable_start_string='{{',
            variable_end_string='}}',
            comment_start_string='<#',
            comment_end_string='#>',
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Check if pdflatex is available
        if not self._check_pdflatex():
            logger.warning(
                "pdflatex not found. PDF generation will fail. "
                "Install TeX Live or MiKTeX to enable PDF generation."
            )

        logger.info(f"LaTeX Renderer initialized with template: {self.template_path}")

    def _check_pdflatex(self) -> bool:
        """
        Check if pdflatex is available on the system.

        Returns:
            True if pdflatex is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def escape_latex(self, text: str) -> str:
        """
        Escape special LaTeX characters in text.

        Args:
            text: Text to escape

        Returns:
            LaTeX-safe text
        """
        if not text:
            return ""

        # Escape special characters
        for char, replacement in self.LATEX_SPECIAL_CHARS.items():
            text = text.replace(char, replacement)

        return text

    def escape_dict(self, data: Dict) -> Dict:
        """
        Recursively escape LaTeX special characters in a dictionary.

        Args:
            data: Dictionary with data

        Returns:
            Dictionary with escaped values
        """
        escaped = {}
        for key, value in data.items():
            if isinstance(value, str):
                escaped[key] = self.escape_latex(value)
            elif isinstance(value, list):
                escaped[key] = [
                    self.escape_dict(item) if isinstance(item, dict)
                    else self.escape_latex(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, dict):
                escaped[key] = self.escape_dict(value)
            else:
                escaped[key] = value

        return escaped

    def render_template(self, resume_data: Dict) -> str:
        """
        Render LaTeX template with resume data.

        Args:
            resume_data: Dictionary with resume data

        Returns:
            Rendered LaTeX string
        """
        try:
            # Escape LaTeX special characters
            escaped_data = self.escape_dict(resume_data)

            # Load template
            template = self.jinja_env.get_template(self.template_path.name)

            # Render
            latex_content = template.render(**escaped_data)

            logger.debug("Template rendered successfully")
            return latex_content

        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            raise

    def compile_latex_to_pdf(
        self,
        latex_content: str,
        output_path: Optional[Path] = None,
        cleanup: bool = True
    ) -> Path:
        """
        Compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX content string
            output_path: Optional output PDF path (if None, generates temp file)
            cleanup: Whether to clean up temporary files

        Returns:
            Path to generated PDF file
        """
        # Create temporary directory for compilation
        temp_dir = tempfile.mkdtemp()
        temp_tex_path = Path(temp_dir) / "resume.tex"
        temp_pdf_path = Path(temp_dir) / "resume.pdf"

        try:
            # Write LaTeX content to temp file
            with open(temp_tex_path, 'w', encoding='utf-8') as f:
                f.write(latex_content)

            logger.info(f"Compiling LaTeX file: {temp_tex_path}")

            # Run pdflatex (run twice for proper references)
            for i in range(2):
                result = subprocess.run(
                    [
                        'pdflatex',
                        '-interaction=nonstopmode',
                        '-output-directory', temp_dir,
                        str(temp_tex_path)
                    ],
                    capture_output=True,
                    timeout=settings.latex_compile_timeout,
                    cwd=temp_dir
                )

                if result.returncode != 0:
                    error_log = result.stdout.decode('utf-8', errors='ignore')
                    logger.error(f"LaTeX compilation failed:\n{error_log}")
                    raise RuntimeError(
                        f"LaTeX compilation failed. Check logs for details.\n"
                        f"Error: {self._extract_latex_error(error_log)}"
                    )

            # Check if PDF was generated
            if not temp_pdf_path.exists():
                raise RuntimeError("PDF file was not generated")

            # Move PDF to output location
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(temp_pdf_path, output_path)
                final_path = output_path
            else:
                # Keep in temp location
                final_path = temp_pdf_path

            logger.info(f"PDF generated successfully: {final_path}")
            return final_path

        except subprocess.TimeoutExpired:
            logger.error("LaTeX compilation timed out")
            raise RuntimeError(
                f"LaTeX compilation timed out after {settings.latex_compile_timeout}s"
            )

        except Exception as e:
            logger.error(f"Error compiling LaTeX: {str(e)}")
            raise

        finally:
            # Clean up temporary files (except the PDF if it's the output)
            if cleanup and output_path:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {str(e)}")

    def _extract_latex_error(self, error_log: str) -> str:
        """
        Extract the main error message from LaTeX log.

        Args:
            error_log: Full LaTeX error log

        Returns:
            Extracted error message
        """
        # Look for common error patterns
        error_patterns = [
            r'! (.+)',  # LaTeX errors start with !
            r'Error: (.+)',
            r'Fatal error: (.+)'
        ]

        for pattern in error_patterns:
            match = re.search(pattern, error_log)
            if match:
                return match.group(1).strip()

        return "Unknown LaTeX error. Check logs for details."

    def generate_pdf(
        self,
        resume_data: Dict,
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Generate PDF resume from data.

        Args:
            resume_data: Dictionary with resume data
            output_filename: Optional output filename (default: auto-generated)

        Returns:
            Path to generated PDF file
        """
        # Render LaTeX template
        latex_content = self.render_template(resume_data)

        # Determine output path
        if output_filename:
            output_path = settings.pdf_output_dir / output_filename
        else:
            # Auto-generate filename
            name = resume_data.get('name', 'resume').replace(' ', '_')
            output_path = settings.pdf_output_dir / f"{name}_resume.pdf"

        # Compile to PDF
        pdf_path = self.compile_latex_to_pdf(
            latex_content=latex_content,
            output_path=output_path,
            cleanup=True
        )

        return pdf_path
