"""
Observability Service with Arize Phoenix
Provides tracing and monitoring for RAG operations.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from functools import wraps
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import Phoenix, but make it optional
try:
    import phoenix as px
    from phoenix.trace import trace
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    logger.warning("Arize Phoenix not installed. Tracing will be disabled.")
    # Create dummy decorator if Phoenix not available
    def trace(name=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator


class ObservabilityService:
    """
    Service for observability and tracing of RAG operations.
    Uses Arize Phoenix for visualization and monitoring.
    """

    def __init__(self):
        self.enabled = settings.enable_tracing and PHOENIX_AVAILABLE
        self.session = None

        if self.enabled:
            self._initialize_phoenix()
        else:
            logger.info("Observability tracing is disabled")

    def _initialize_phoenix(self):
        """Initialize Phoenix session."""
        try:
            logger.info("Initializing Arize Phoenix...")

            # Launch Phoenix server
            self.session = px.launch_app(port=settings.phoenix_port)

            logger.info(
                f"Phoenix UI available at http://localhost:{settings.phoenix_port}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Phoenix: {str(e)}")
            self.enabled = False

    @trace(name="embedding_generation")
    def trace_embedding(
        self,
        texts: List[str],
        model_name: str,
        embeddings: Optional[List] = None
    ) -> Dict:
        """
        Trace embedding generation.

        Args:
            texts: Input texts
            model_name: Name of embedding model
            embeddings: Generated embeddings (optional)

        Returns:
            Trace metadata
        """
        return {
            "operation": "embedding",
            "model": model_name,
            "input_count": len(texts),
            "timestamp": datetime.utcnow().isoformat()
        }

    @trace(name="vector_search")
    def trace_retrieval(
        self,
        query: str,
        results: List[Dict],
        retrieval_method: str = "direct",
        top_k: int = 10
    ) -> Dict:
        """
        Trace retrieval operation.

        Args:
            query: Search query
            results: Retrieved results
            retrieval_method: Method used (direct, hyde, etc.)
            top_k: Number of results requested

        Returns:
            Trace metadata
        """
        return {
            "operation": "retrieval",
            "method": retrieval_method,
            "query_length": len(query),
            "results_count": len(results),
            "top_k": top_k,
            "avg_score": sum(r.get('score', 0) for r in results) / len(results) if results else 0,
            "timestamp": datetime.utcnow().isoformat()
        }

    @trace(name="reranking")
    def trace_reranking(
        self,
        query: str,
        input_results: List[Dict],
        reranked_results: List[Dict],
        model_name: str
    ) -> Dict:
        """
        Trace re-ranking operation.

        Args:
            query: Search query
            input_results: Results before re-ranking
            reranked_results: Results after re-ranking
            model_name: Cross-encoder model name

        Returns:
            Trace metadata
        """
        # Calculate rank changes
        input_ids = [r['chunk_id'] for r in input_results[:10]]
        reranked_ids = [r['chunk_id'] for r in reranked_results[:10]]
        overlap = len(set(input_ids) & set(reranked_ids))

        return {
            "operation": "reranking",
            "model": model_name,
            "input_count": len(input_results),
            "output_count": len(reranked_results),
            "top10_overlap": overlap,
            "timestamp": datetime.utcnow().isoformat()
        }

    @trace(name="hyde_generation")
    def trace_hyde(
        self,
        query: str,
        hypothetical_docs: List[str],
        strategy: str
    ) -> Dict:
        """
        Trace HyDE generation.

        Args:
            query: Original query
            hypothetical_docs: Generated hypothetical documents
            strategy: HyDE strategy used

        Returns:
            Trace metadata
        """
        return {
            "operation": "hyde",
            "strategy": strategy,
            "query_length": len(query),
            "num_docs_generated": len(hypothetical_docs),
            "avg_doc_length": sum(len(d) for d in hypothetical_docs) / len(hypothetical_docs) if hypothetical_docs else 0,
            "timestamp": datetime.utcnow().isoformat()
        }

    @trace(name="llm_generation")
    def trace_llm_call(
        self,
        prompt: str,
        response: str,
        model: str,
        duration: float
    ) -> Dict:
        """
        Trace LLM generation call.

        Args:
            prompt: Input prompt
            response: LLM response
            model: Model name
            duration: Call duration in seconds

        Returns:
            Trace metadata
        """
        return {
            "operation": "llm_generation",
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat()
        }

    @trace(name="rag_pipeline")
    def trace_full_pipeline(
        self,
        query: str,
        pipeline_steps: List[Dict],
        final_result: Any,
        total_duration: float
    ) -> Dict:
        """
        Trace complete RAG pipeline execution.

        Args:
            query: Input query
            pipeline_steps: List of step metadata
            final_result: Final pipeline output
            total_duration: Total execution time

        Returns:
            Trace metadata
        """
        return {
            "operation": "rag_pipeline",
            "query_length": len(query),
            "num_steps": len(pipeline_steps),
            "total_duration": total_duration,
            "steps": pipeline_steps,
            "timestamp": datetime.utcnow().isoformat()
        }

    def log_metrics(self, metrics: Dict):
        """
        Log custom metrics.

        Args:
            metrics: Dictionary of metrics to log
        """
        if self.enabled:
            logger.info(f"Metrics: {metrics}")
        # In production, you might want to send these to a monitoring system

    def get_trace_stats(self) -> Dict:
        """
        Get statistics about traced operations.

        Returns:
            Dictionary with trace statistics
        """
        # This would query Phoenix for statistics
        # For now, return empty dict
        return {
            "tracing_enabled": self.enabled,
            "phoenix_available": PHOENIX_AVAILABLE
        }


# Global observability instance
observability = ObservabilityService()


# Convenience decorator for timing operations
def timed_operation(operation_name: str):
    """
    Decorator to time and log operations.

    Args:
        operation_name: Name of the operation

    Usage:
        @timed_operation("my_function")
        def my_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"{operation_name} completed in {duration:.2f}s"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation_name} failed after {duration:.2f}s: {str(e)}"
                )
                raise

        return wrapper
    return decorator


# Context manager for tracing pipeline steps
class TraceStep:
    """
    Context manager for tracing individual pipeline steps.

    Usage:
        with TraceStep("retrieval", observability) as step:
            results = retrieve(query)
            step.log_result({"count": len(results)})
    """

    def __init__(self, step_name: str, obs_service: ObservabilityService):
        self.step_name = step_name
        self.obs_service = obs_service
        self.start_time = None
        self.metadata = {}

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        self.metadata.update({
            "step": self.step_name,
            "duration": duration,
            "success": exc_type is None
        })

        if exc_type:
            self.metadata["error"] = str(exc_val)

        logger.info(f"Step '{self.step_name}' completed: {self.metadata}")

    def log_result(self, result_data: Dict):
        """Log intermediate results."""
        self.metadata.update(result_data)
