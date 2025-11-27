"""
Enhanced Analysis Service with Advanced RAG Pipeline
Integrates: Semantic Chunking, HyDE, Cross-Encoder Re-ranking, and Evaluation
"""

import logging
import time
from typing import Dict, List, Optional

from app.services.parsing.pdf_parser import PDFParser
from app.services.storage.vector_store import VectorStore
from app.services.llm.llm_service import LLMService
from app.services.rag.semantic_chunker import SemanticChunker
from app.services.rag.knowledge_base import KnowledgeBase
from app.services.rag.hyde import HyDEService
from app.services.rag.retriever import AdvancedRetriever
from app.services.rag.reranker import ReRanker
from app.services.monitoring.observability import observability, TraceStep
from app.evaluation.llm_judge import llm_judge
from app.core.config import settings

logger = logging.getLogger(__name__)


class EnhancedAnalysisService:
    """
    Enhanced resume analysis service with advanced RAG pipeline.

    Pipeline flow:
    1. Ingest resume with semantic chunking
    2. HyDE query expansion (generate hypothetical resume bullets)
    3. Bi-encoder retrieval (get top candidates)
    4. Cross-encoder re-ranking (refine results)
    5. LLM generation (create analysis/tailored resume)
    6. Evaluation (optional)
    """

    def __init__(self):
        # Initialize components
        self.pdf_parser = PDFParser()
        self.vector_store = VectorStore()
        self.llm_service = LLMService()
        self.chunker = SemanticChunker()
        self.knowledge_base = KnowledgeBase(vector_store=self.vector_store)
        self.hyde_service = HyDEService()
        self.retriever = AdvancedRetriever(
            vector_store=self.vector_store,
            hyde_service=self.hyde_service
        )

        # Only initialize reranker if enabled
        self.reranker = None
        if settings.use_reranking:
            try:
                self.reranker = ReRanker(model_name=settings.cross_encoder_model)
                logger.info("Cross-encoder re-ranker initialized")
            except Exception as e:
                logger.error(f"Failed to initialize re-ranker: {str(e)}")
                self.reranker = None

    def analyze_resume_enhanced(
        self,
        resume_path: str,
        job_description: str,
        job_title: Optional[str] = None,
        enable_evaluation: bool = False
    ) -> Dict:
        """
        Analyze a resume using the enhanced RAG pipeline.

        Args:
            resume_path: Path to resume file
            job_description: Job description text
            job_title: Optional job title
            enable_evaluation: Whether to run evaluation

        Returns:
            Enhanced analysis result
        """
        start_time = time.time()
        pipeline_steps = []

        try:
            # Step 1: Extract and chunk resume
            with TraceStep("extract_and_chunk", observability) as step:
                logger.info("Step 1: Extracting and chunking resume")

                # Extract text
                resume_text = self.pdf_parser.extract_text(resume_path)
                if not resume_text:
                    raise ValueError("Could not extract text from PDF")

                # Semantic chunking
                chunks = self.chunker.chunk_resume(resume_text)

                # Store chunks in vector DB
                for chunk in chunks:
                    chunk_metadata = {
                        'source_type': 'resume',
                        'source_file': resume_path,
                        'chunk_type': chunk['chunk_type'],
                        'chunk_index': chunk['chunk_index'],
                        **chunk['metadata']
                    }

                    self.vector_store.add_chunk(
                        chunk_id=chunk['chunk_id'],
                        content=chunk['content'],
                        metadata=chunk_metadata
                    )

                step.log_result({
                    "chunks_created": len(chunks),
                    "resume_length": len(resume_text)
                })

                pipeline_steps.append({
                    "step": "chunking",
                    "chunks_created": len(chunks)
                })

            # Step 2: HyDE Query Expansion (optional)
            hypothetical_docs = []
            if settings.use_hyde:
                with TraceStep("hyde_expansion", observability) as step:
                    logger.info("Step 2: HyDE query expansion")

                    hyde_result = self.hyde_service.expand_query(
                        job_description,
                        strategy=settings.hyde_strategy
                    )
                    hypothetical_docs = hyde_result['hypothetical_documents']

                    step.log_result({
                        "num_hypothetical_docs": len(hypothetical_docs)
                    })

                    pipeline_steps.append({
                        "step": "hyde",
                        "docs_generated": len(hypothetical_docs)
                    })

            # Step 3: Advanced Retrieval
            with TraceStep("retrieval", observability) as step:
                logger.info("Step 3: Retrieving relevant chunks")

                retrieved_chunks = self.retriever.retrieve(
                    query=job_description,
                    top_k=settings.retrieval_top_k,
                    use_hyde=settings.use_hyde,
                    hyde_strategy=settings.hyde_strategy,
                    num_hyde_docs=settings.hyde_num_documents
                )

                step.log_result({
                    "chunks_retrieved": len(retrieved_chunks),
                    "avg_score": sum(c.get('score', 0) for c in retrieved_chunks) / len(retrieved_chunks) if retrieved_chunks else 0
                })

                pipeline_steps.append({
                    "step": "retrieval",
                    "chunks_retrieved": len(retrieved_chunks)
                })

            # Step 4: Cross-Encoder Re-ranking (optional)
            if self.reranker and settings.use_reranking:
                with TraceStep("reranking", observability) as step:
                    logger.info("Step 4: Re-ranking with cross-encoder")

                    reranked_chunks = self.reranker.rerank_with_hybrid_scoring(
                        query=job_description,
                        chunks=retrieved_chunks,
                        top_k=settings.rerank_top_k,
                        retrieval_weight=settings.retrieval_score_weight,
                        rerank_weight=settings.rerank_score_weight
                    )

                    step.log_result({
                        "chunks_after_reranking": len(reranked_chunks),
                        "top_score": reranked_chunks[0].get('score', 0) if reranked_chunks else 0
                    })

                    pipeline_steps.append({
                        "step": "reranking",
                        "final_chunks": len(reranked_chunks)
                    })

                    # Use reranked chunks for analysis
                    final_chunks = reranked_chunks
            else:
                final_chunks = retrieved_chunks[:settings.rerank_top_k]

            # Step 5: LLM Analysis
            with TraceStep("llm_analysis", observability) as step:
                logger.info("Step 5: Generating analysis with LLM")

                # Analyze match
                match_analysis = self.llm_service.analyze_resume_match(
                    resume_text=resume_text,
                    job_description=job_description,
                    similar_resumes=[]  # Not used in enhanced version
                )

                # Generate improvements
                improvements = self.llm_service.generate_improvements(
                    resume_text=resume_text,
                    job_description=job_description,
                    analysis=match_analysis
                )

                # Compare requirements
                comparisons = self.llm_service.compare_requirements(
                    resume_text=resume_text,
                    job_description=job_description
                )

                step.log_result({
                    "overall_score": match_analysis.get('overall_score', 0),
                    "improvements_count": len(improvements)
                })

                pipeline_steps.append({
                    "step": "llm_analysis",
                    "overall_score": match_analysis.get('overall_score', 0)
                })

            # Step 6: Evaluation (optional)
            evaluation_results = None
            if enable_evaluation:
                with TraceStep("evaluation", observability) as step:
                    logger.info("Step 6: Running evaluation")

                    # Extract chunk contents for evaluation
                    chunk_contents = [c['content'] for c in final_chunks]

                    # Run LLM-as-judge evaluation
                    evaluation_results = llm_judge.evaluate_complete_pipeline(
                        job_description=job_description,
                        retrieved_chunks=chunk_contents,
                        generated_content=str(improvements)  # Or use tailored resume
                    )

                    step.log_result({
                        "overall_eval_score": evaluation_results.get('overall_score', 0)
                    })

                    pipeline_steps.append({
                        "step": "evaluation",
                        "score": evaluation_results.get('overall_score', 0)
                    })

            # Build final result
            total_duration = time.time() - start_time

            result = {
                "match_analysis": {
                    "overall_score": match_analysis.get("overall_score", 0),
                    "skills": {
                        "matched": match_analysis.get("matched_skills", []),
                        "missing": match_analysis.get("missing_skills", []),
                        "transferable": []
                    },
                    "experience_relevance": {},
                    "ats_score": match_analysis.get("ats_score", 0)
                },
                "improvements": improvements,
                "comparisons": comparisons,
                "retrieved_chunks": [
                    {
                        "content": c['content'][:200] + "...",  # Truncate for response
                        "score": c.get('score', 0),
                        "chunk_type": c.get('metadata', {}).get('chunk_type', 'unknown')
                    }
                    for c in final_chunks[:5]  # Top 5 for response
                ],
                "rag_metadata": {
                    "pipeline_steps": pipeline_steps,
                    "total_duration": total_duration,
                    "use_hyde": settings.use_hyde,
                    "use_reranking": settings.use_reranking,
                    "chunks_retrieved": len(retrieved_chunks),
                    "chunks_after_reranking": len(final_chunks)
                },
                "evaluation": evaluation_results if enable_evaluation else None
            }

            logger.info(f"Enhanced analysis completed in {total_duration:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Error in enhanced analysis: {str(e)}")
            raise

    def ingest_resume_to_knowledge_base(
        self,
        resume_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest a resume into the knowledge base with semantic chunking.

        Args:
            resume_path: Path to resume file
            metadata: Optional metadata

        Returns:
            Ingestion result
        """
        return self.knowledge_base.ingest_resume(resume_path, metadata)

    def batch_ingest_directory(
        self,
        directory_path: str,
        document_type: str = 'auto'
    ) -> Dict:
        """
        Batch ingest documents from a directory.

        Args:
            directory_path: Path to directory
            document_type: Type of documents to ingest

        Returns:
            Batch ingestion results
        """
        return self.knowledge_base.ingest_directory(directory_path, document_type)

    def get_pipeline_stats(self) -> Dict:
        """
        Get statistics about the RAG pipeline.

        Returns:
            Pipeline statistics
        """
        return {
            "vector_store_count": self.vector_store.count_resumes(),
            "hyde_enabled": settings.use_hyde,
            "reranking_enabled": settings.use_reranking and self.reranker is not None,
            "semantic_chunking_enabled": settings.enable_semantic_chunking,
            "retrieval_top_k": settings.retrieval_top_k,
            "rerank_top_k": settings.rerank_top_k,
            "cross_encoder_model": settings.cross_encoder_model if self.reranker else None
        }


# Global enhanced service instance
enhanced_service = EnhancedAnalysisService()
