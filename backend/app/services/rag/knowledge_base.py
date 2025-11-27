"""
Knowledge Base Ingestion Service
Handles ingestion of various document types into ChromaDB with semantic chunking.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime
import uuid

from app.services.rag.semantic_chunker import SemanticChunker
from app.services.parsing.pdf_parser import PDFParser

try:
    from docx import Document
except ImportError:
    Document = None

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Manages ingestion of various document types into the knowledge base.
    Supports: resumes (PDF/DOCX/TXT), projects (MD), STAR stories (JSON/MD),
    and job descriptions.
    """

    def __init__(self, vector_store=None):
        """
        Initialize Knowledge Base.

        Args:
            vector_store: VectorStore instance for storing chunks
        """
        self.chunker = SemanticChunker()
        self.vector_store = vector_store
        self.pdf_parser = PDFParser()

    def ingest_resume(
        self,
        file_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest a resume file (PDF, DOCX, or TXT).

        Args:
            file_path: Path to resume file
            metadata: Optional metadata (e.g., candidate name, date)

        Returns:
            Ingestion result with chunk count and IDs
        """
        try:
            # Extract text based on file type
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.pdf':
                text = self.pdf_parser.extract_text(file_path)
            elif file_ext == '.docx':
                text = self._extract_from_docx(file_path)
            elif file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            if not text or not text.strip():
                raise ValueError("No text could be extracted from the file")

            # Generate resume ID
            resume_id = metadata.get('resume_id', str(uuid.uuid4()))

            # Chunk the resume semantically
            chunks = self.chunker.chunk_resume(text, resume_id=resume_id)

            # Add chunks to vector store if available
            chunk_ids = []
            if self.vector_store:
                for chunk in chunks:
                    chunk_metadata = {
                        'source_type': 'resume',
                        'source_file': os.path.basename(file_path),
                        'resume_id': resume_id,
                        'chunk_type': chunk['chunk_type'],
                        'chunk_index': chunk['chunk_index'],
                        **(metadata or {}),
                        **chunk['metadata']
                    }

                    chunk_id = self.vector_store.add_chunk(
                        chunk_id=chunk['chunk_id'],
                        content=chunk['content'],
                        metadata=chunk_metadata
                    )
                    chunk_ids.append(chunk_id)

            logger.info(f"Ingested resume {resume_id}: {len(chunks)} chunks created")

            return {
                'success': True,
                'resume_id': resume_id,
                'chunk_count': len(chunks),
                'chunk_ids': chunk_ids,
                'chunks': chunks  # Return chunks for inspection
            }

        except Exception as e:
            logger.error(f"Error ingesting resume from {file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def ingest_project_description(
        self,
        file_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest a project description (Markdown or TXT).

        Args:
            file_path: Path to project file
            metadata: Optional metadata (e.g., project name, date)

        Returns:
            Ingestion result
        """
        try:
            # Read markdown/text file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                raise ValueError("File is empty")

            project_id = metadata.get('project_id', str(uuid.uuid4()))

            # For projects, we treat the whole file as context but may split
            # by sections if it's large
            chunks = self._chunk_project(content, project_id)

            # Add to vector store
            chunk_ids = []
            if self.vector_store:
                for chunk in chunks:
                    chunk_metadata = {
                        'source_type': 'project',
                        'source_file': os.path.basename(file_path),
                        'project_id': project_id,
                        'chunk_index': chunk['chunk_index'],
                        **(metadata or {}),
                        **chunk['metadata']
                    }

                    chunk_id = self.vector_store.add_chunk(
                        chunk_id=chunk['chunk_id'],
                        content=chunk['content'],
                        metadata=chunk_metadata
                    )
                    chunk_ids.append(chunk_id)

            logger.info(f"Ingested project {project_id}: {len(chunks)} chunks")

            return {
                'success': True,
                'project_id': project_id,
                'chunk_count': len(chunks),
                'chunk_ids': chunk_ids
            }

        except Exception as e:
            logger.error(f"Error ingesting project from {file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def ingest_star_story(
        self,
        file_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest STAR format stories (JSON or Markdown).

        STAR = Situation, Task, Action, Result

        Args:
            file_path: Path to STAR story file
            metadata: Optional metadata

        Returns:
            Ingestion result
        """
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    star_data = json.load(f)

                # Expected format: {"situation": "...", "task": "...", "action": "...", "result": "..."}
                content = self._format_star_story(star_data)
            else:
                # Markdown or text
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            story_id = metadata.get('story_id', str(uuid.uuid4()))

            # STAR stories are kept as single chunks to preserve narrative flow
            chunk = {
                'chunk_id': f"{story_id}_star_0",
                'content': content,
                'chunk_type': 'star_story',
                'chunk_index': 0,
                'metadata': {
                    'story_id': story_id,
                    'created_at': datetime.utcnow().isoformat()
                }
            }

            chunk_id = None
            if self.vector_store:
                chunk_metadata = {
                    'source_type': 'star_story',
                    'source_file': os.path.basename(file_path),
                    'story_id': story_id,
                    **(metadata or {}),
                    **chunk['metadata']
                }

                chunk_id = self.vector_store.add_chunk(
                    chunk_id=chunk['chunk_id'],
                    content=chunk['content'],
                    metadata=chunk_metadata
                )

            logger.info(f"Ingested STAR story {story_id}")

            return {
                'success': True,
                'story_id': story_id,
                'chunk_id': chunk_id
            }

        except Exception as e:
            logger.error(f"Error ingesting STAR story from {file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def ingest_job_description(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest a job description (as text).

        Args:
            content: Job description text
            metadata: Optional metadata (e.g., job title, company)

        Returns:
            Ingestion result
        """
        try:
            jd_id = metadata.get('jd_id', str(uuid.uuid4()))

            # For job descriptions, we keep as single chunk but could
            # optionally split by sections (requirements, responsibilities, etc.)
            chunk = {
                'chunk_id': f"{jd_id}_jd_0",
                'content': content,
                'chunk_type': 'job_description',
                'chunk_index': 0,
                'metadata': {
                    'jd_id': jd_id,
                    'created_at': datetime.utcnow().isoformat()
                }
            }

            chunk_id = None
            if self.vector_store:
                chunk_metadata = {
                    'source_type': 'job_description',
                    'jd_id': jd_id,
                    **(metadata or {}),
                    **chunk['metadata']
                }

                chunk_id = self.vector_store.add_chunk(
                    chunk_id=chunk['chunk_id'],
                    content=chunk['content'],
                    metadata=chunk_metadata
                )

            logger.info(f"Ingested job description {jd_id}")

            return {
                'success': True,
                'jd_id': jd_id,
                'chunk_id': chunk_id
            }

        except Exception as e:
            logger.error(f"Error ingesting job description: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def ingest_directory(
        self,
        directory_path: str,
        document_type: str = 'auto',
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Batch ingest all documents in a directory.

        Args:
            directory_path: Path to directory containing documents
            document_type: Type of documents ('resume', 'project', 'star', 'auto')
            metadata: Common metadata for all documents

        Returns:
            Summary of ingestion results
        """
        results = {
            'success': [],
            'failed': [],
            'total': 0
        }

        directory = Path(directory_path)
        if not directory.is_dir():
            return {'error': 'Invalid directory path'}

        # Get all files
        files = list(directory.glob('**/*'))
        files = [f for f in files if f.is_file()]

        for file_path in files:
            results['total'] += 1

            # Determine document type
            if document_type == 'auto':
                doc_type = self._infer_document_type(file_path)
            else:
                doc_type = document_type

            # Ingest based on type
            if doc_type == 'resume':
                result = self.ingest_resume(str(file_path), metadata)
            elif doc_type == 'project':
                result = self.ingest_project_description(str(file_path), metadata)
            elif doc_type == 'star':
                result = self.ingest_star_story(str(file_path), metadata)
            else:
                result = {'success': False, 'error': 'Unknown document type'}

            if result.get('success'):
                results['success'].append(str(file_path))
            else:
                results['failed'].append({
                    'file': str(file_path),
                    'error': result.get('error', 'Unknown error')
                })

        logger.info(
            f"Batch ingestion complete: {len(results['success'])}/{results['total']} successful"
        )

        return results

    # Helper methods

    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        if Document is None:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")

        doc = Document(file_path)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        return text

    def _chunk_project(self, content: str, project_id: str) -> List[Dict]:
        """Chunk a project description."""
        # Simple chunking by sections or paragraphs
        # Can be enhanced with more sophisticated splitting

        # For now, treat as single chunk if small, or split by markdown headers
        if len(content) < 2000:
            return [{
                'chunk_id': f"{project_id}_project_0",
                'content': content,
                'chunk_index': 0,
                'metadata': {
                    'project_id': project_id,
                    'created_at': datetime.utcnow().isoformat()
                }
            }]

        # Split by markdown headers (## or ###)
        sections = content.split('\n## ')
        chunks = []

        for i, section in enumerate(sections):
            if section.strip():
                chunks.append({
                    'chunk_id': f"{project_id}_project_{i}",
                    'content': section.strip(),
                    'chunk_index': i,
                    'metadata': {
                        'project_id': project_id,
                        'created_at': datetime.utcnow().isoformat()
                    }
                })

        return chunks

    def _format_star_story(self, star_data: Dict) -> str:
        """Format STAR story from JSON data."""
        template = """
Situation: {situation}

Task: {task}

Action: {action}

Result: {result}
        """.strip()

        return template.format(
            situation=star_data.get('situation', ''),
            task=star_data.get('task', ''),
            action=star_data.get('action', ''),
            result=star_data.get('result', '')
        )

    def _infer_document_type(self, file_path: Path) -> str:
        """Infer document type from filename and extension."""
        filename = file_path.name.lower()
        ext = file_path.suffix.lower()

        if 'resume' in filename or 'cv' in filename:
            return 'resume'
        elif 'project' in filename:
            return 'project'
        elif 'star' in filename or 'story' in filename:
            return 'star'
        elif ext in ['.pdf', '.docx'] and 'jd' not in filename:
            # Default PDFs/DOCX to resume unless specifically named otherwise
            return 'resume'
        else:
            return 'unknown'
