"""
Concurrency control utilities for managing resource-intensive operations.
"""

import threading
from typing import Callable, TypeVar, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class Semaphore:
    """Thread-safe semaphore for limiting concurrent operations."""

    def __init__(self, max_permits: int):
        """
        Initialize semaphore with maximum permits.

        Args:
            max_permits: Maximum number of concurrent operations allowed
        """
        self._semaphore = threading.Semaphore(max_permits)
        self._max_permits = max_permits

    def __enter__(self):
        """Acquire a permit."""
        self._semaphore.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release a permit."""
        self._semaphore.release()

    def execute(self, fn: Callable[[], R]) -> R:
        """
        Execute a function with semaphore control.

        Args:
            fn: Function to execute

        Returns:
            Result of the function
        """
        with self:
            return fn()


def parallel_map_with_limit(
    items: List[T],
    fn: Callable[[T], R],
    max_workers: int = 3,
    timeout: int = None
) -> List[R]:
    """
    Map a function over items in parallel with concurrency limit.

    Args:
        items: List of items to process
        fn: Function to apply to each item
        max_workers: Maximum number of parallel workers
        timeout: Optional timeout per item in seconds

    Returns:
        List of results in the same order as input items
    """
    if not items:
        return []

    results = [None] * len(items)
    item_indices = {id(item): idx for idx, item in enumerate(items)}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_item = {
            executor.submit(fn, item): item
            for item in items
        }

        # Collect results as they complete
        for future in as_completed(future_to_item, timeout=timeout):
            item = future_to_item[future]
            idx = item_indices[id(item)]

            try:
                result = future.result()
                results[idx] = result
            except Exception as e:
                logger.error(f"Error processing item {idx}: {str(e)}")
                # Keep None for failed items
                results[idx] = None

    return results


class ResourceMonitor:
    """Monitor system resources to prevent overload."""

    @staticmethod
    def get_recommended_workers(max_workers: int = None) -> int:
        """
        Get recommended number of workers based on system resources.

        Args:
            max_workers: Optional maximum worker limit from config

        Returns:
            Recommended worker count
        """
        try:
            from app.core.config import settings

            # Use config if provided
            if max_workers is None:
                max_workers = settings.max_concurrent_llm_calls

            # If resource monitoring is disabled, return config value
            if not settings.enable_resource_monitoring:
                return max_workers

            import os
            cpu_count = os.cpu_count() or 2

            # Conservative approach: use half the CPUs
            # This leaves headroom for the main process and Ollama
            recommended = max(1, cpu_count // 2)

            # Cap at configured max
            return min(max_workers, recommended)
        except Exception:
            # Default to 2 workers if we can't determine
            return 2

    @staticmethod
    def should_use_sequential_processing() -> bool:
        """
        Determine if sequential processing should be used.

        Returns:
            True if system resources are constrained
        """
        try:
            from app.core.config import settings

            # If resource monitoring is disabled, don't force sequential
            if not settings.enable_resource_monitoring:
                return False

            import psutil

            # Check available memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024 ** 3)

            # Use configured threshold
            if available_gb < settings.sequential_mode_memory_threshold_gb:
                logger.warning(
                    f"Low memory ({available_gb:.1f}GB available, "
                    f"threshold: {settings.sequential_mode_memory_threshold_gb}GB), "
                    f"using sequential processing"
                )
                return True

            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # If CPU is heavily loaded (>80%), use sequential
            if cpu_percent > 80:
                logger.warning(f"High CPU usage ({cpu_percent}%), using sequential processing")
                return True

            return False
        except ImportError:
            # psutil not available, use conservative default
            logger.info("psutil not installed, cannot monitor resources. Install with: pip install psutil")
            return False
        except Exception as e:
            logger.warning(f"Error checking system resources: {e}")
            return False
