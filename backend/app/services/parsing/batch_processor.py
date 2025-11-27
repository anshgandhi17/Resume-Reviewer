"""
Batch Processor Service
Handles parallel processing of multiple resume uploads.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from app.services.parsing.pdf_parser import PDFParser
from app.services.rag.semantic_chunker import SemanticChunker
from app.services.rag.knowledge_base import KnowledgeBase
from app.services.storage.vector_store import VectorStore
from app.core.config import settings

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processes multiple resume files in parallel.

    Pipeline for each file:
    1. Parse PDF → Extract text
    2. Semantic chunking → Split into meaningful chunks
    3. Embed → Generate vector embeddings
    4. Store → Save to ChromaDB
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        timeout_per_file: int = 60
    ):
        """
        Initialize Batch Processor.

        Args:
            max_workers: Maximum number of parallel workers (default: min(5, cpu_count))
            timeout_per_file: Timeout in seconds for processing each file
        """
        self.max_workers = max_workers or min(5, (asyncio.cpu_count() or 1))
        self.timeout_per_file = timeout_per_file

        # Initialize services (thread-safe)
        self.pdf_parser = PDFParser()
        self.chunker = SemanticChunker()
        self.vector_store = VectorStore()
        self.knowledge_base = KnowledgeBase(vector_store=self.vector_store)

    def process_single_file(
        self,
        file_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Process a single resume file.

        Args:
            file_path: Path to the resume file
            metadata: Optional metadata (resume_id, candidate_name, etc.)

        Returns:
            Processing result with status, chunk_count, and timing
        """
        start_time = time.time()
        file_name = Path(file_path).name

        result = {
            'file_name': file_name,
            'file_path': file_path,
            'status': 'pending',
            'chunk_count': 0,
            'error': None,
            'processing_time': 0
        }

        try:
            logger.info(f"Processing file: {file_name}")

            # Ingest the resume (parse, chunk, embed, store)
            ingestion_result = self.knowledge_base.ingest_resume(
                file_path=file_path,
                metadata=metadata or {}
            )

            result['status'] = 'success'
            result['chunk_count'] = ingestion_result.get('chunk_count', 0)
            result['resume_id'] = ingestion_result.get('resume_id')

            logger.info(
                f"Successfully processed {file_name}: "
                f"{result['chunk_count']} chunks in "
                f"{time.time() - start_time:.2f}s"
            )

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(
                f"Failed to process {file_name}: {str(e)}\n"
                f"{traceback.format_exc()}"
            )

        finally:
            result['processing_time'] = time.time() - start_time

        return result

    def process_batch(
        self,
        file_paths: List[str],
        metadata_list: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Process multiple resume files in parallel.

        Args:
            file_paths: List of file paths to process
            metadata_list: Optional list of metadata dicts (one per file)

        Returns:
            Batch processing result with individual results and aggregated stats
        """
        start_time = time.time()

        # Validate inputs
        if not file_paths:
            return {
                'status': 'failed',
                'error': 'No files provided',
                'results': [],
                'summary': {}
            }

        if len(file_paths) > settings.batch_max_files:
            return {
                'status': 'failed',
                'error': f'Too many files. Maximum: {settings.batch_max_files}',
                'results': [],
                'summary': {}
            }

        # Prepare metadata
        if metadata_list is None:
            metadata_list = [{}] * len(file_paths)
        elif len(metadata_list) != len(file_paths):
            metadata_list = metadata_list + [{}] * (len(file_paths) - len(metadata_list))

        logger.info(
            f"Starting batch processing of {len(file_paths)} files "
            f"with {self.max_workers} workers"
        )

        results = []

        if settings.batch_use_parallel:
            # Process files in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(
                        self.process_single_file,
                        file_path,
                        metadata
                    ): (file_path, metadata)
                    for file_path, metadata in zip(file_paths, metadata_list)
                }

                # Collect results as they complete
                for future in as_completed(future_to_file, timeout=self.timeout_per_file * len(file_paths)):
                    try:
                        result = future.result(timeout=self.timeout_per_file)
                        results.append(result)
                    except TimeoutError:
                        file_path, _ = future_to_file[future]
                        file_name = Path(file_path).name
                        logger.error(f"Timeout processing {file_name}")
                        results.append({
                            'file_name': file_name,
                            'file_path': file_path,
                            'status': 'failed',
                            'error': f'Timeout after {self.timeout_per_file}s',
                            'chunk_count': 0,
                            'processing_time': self.timeout_per_file
                        })
                    except Exception as e:
                        file_path, _ = future_to_file[future]
                        file_name = Path(file_path).name
                        logger.error(f"Error processing {file_name}: {str(e)}")
                        results.append({
                            'file_name': file_name,
                            'file_path': file_path,
                            'status': 'failed',
                            'error': str(e),
                            'chunk_count': 0,
                            'processing_time': 0
                        })
        else:
            # Process files sequentially (for debugging)
            for file_path, metadata in zip(file_paths, metadata_list):
                result = self.process_single_file(file_path, metadata)
                results.append(result)

        # Calculate summary statistics
        total_time = time.time() - start_time
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        total_chunks = sum(r['chunk_count'] for r in successful)

        summary = {
            'total_files': len(file_paths),
            'successful': len(successful),
            'failed': len(failed),
            'total_chunks': total_chunks,
            'total_time': round(total_time, 2),
            'avg_time_per_file': round(total_time / len(file_paths), 2) if file_paths else 0,
            'chunks_per_file_avg': round(total_chunks / len(successful), 2) if successful else 0
        }

        logger.info(
            f"Batch processing complete: {summary['successful']}/{summary['total_files']} "
            f"successful in {summary['total_time']}s"
        )

        return {
            'status': 'success' if not failed else 'partial',
            'results': results,
            'summary': summary
        }

    def cleanup_temp_files(self, file_paths: List[str]):
        """
        Clean up temporary uploaded files.

        Args:
            file_paths: List of file paths to delete
        """
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    logger.info(f"Deleted temp file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp file {file_path}: {str(e)}")
