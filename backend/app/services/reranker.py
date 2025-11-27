"""
Cross-Encoder Re-Ranker Service
Re-ranks retrieved chunks using a cross-encoder model for better relevance scoring.
"""

from typing import List, Dict, Optional
import logging
import numpy as np

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class ReRanker:
    """
    Re-ranks retrieved documents using a cross-encoder model.

    Cross-encoders are more accurate than bi-encoders (used for initial retrieval)
    because they jointly encode both query and document, capturing more nuanced
    semantic relationships. However, they're slower, so we use them only for re-ranking.
    """

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Alternative models:
    # - "cross-encoder/ms-marco-MiniLM-L-12-v2" (larger, more accurate)
    # - "cross-encoder/ms-marco-TinyBERT-L-2-v2" (smaller, faster)

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize Re-Ranker.

        Args:
            model_name: Name of cross-encoder model to use
        """
        if CrossEncoder is None:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the cross-encoder model."""
        try:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cross-encoder model: {str(e)}")
            raise

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: Optional[int] = None,
        return_scores: bool = True
    ) -> List[Dict]:
        """
        Re-rank a list of retrieved chunks.

        Args:
            query: The search query (usually job description)
            chunks: List of chunk dictionaries with 'content' field
            top_k: Number of top results to return (None = return all)
            return_scores: Whether to include cross-encoder scores in results

        Returns:
            Re-ranked list of chunks with updated scores
        """
        if not chunks:
            return []

        try:
            # Prepare query-chunk pairs for cross-encoder
            pairs = []
            for chunk in chunks:
                content = chunk.get('content') or chunk.get('text', '')
                pairs.append([query, content])

            # Get cross-encoder scores
            logger.info(f"Re-ranking {len(chunks)} chunks with cross-encoder")
            scores = self.model.predict(pairs)

            # Convert to numpy array for easier manipulation
            scores = np.array(scores)

            # Add scores to chunks
            reranked_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_copy = chunk.copy()
                chunk_copy['rerank_score'] = float(scores[i])

                # Preserve original retrieval score
                if 'score' in chunk_copy:
                    chunk_copy['retrieval_score'] = chunk_copy['score']

                # Update main score to rerank score
                if return_scores:
                    chunk_copy['score'] = float(scores[i])

                reranked_chunks.append(chunk_copy)

            # Sort by rerank score
            reranked_chunks.sort(key=lambda x: x['rerank_score'], reverse=True)

            # Limit to top_k if specified
            if top_k is not None:
                reranked_chunks = reranked_chunks[:top_k]

            logger.info(
                f"Re-ranking complete. Top score: {reranked_chunks[0]['rerank_score']:.4f}, "
                f"Bottom score: {reranked_chunks[-1]['rerank_score']:.4f}"
            )

            return reranked_chunks

        except Exception as e:
            logger.error(f"Error in re-ranking: {str(e)}")
            # Fallback: return original chunks without re-ranking
            return chunks

    def rerank_with_hybrid_scoring(
        self,
        query: str,
        chunks: List[Dict],
        top_k: Optional[int] = None,
        retrieval_weight: float = 0.3,
        rerank_weight: float = 0.7
    ) -> List[Dict]:
        """
        Re-rank with hybrid scoring that combines retrieval and rerank scores.

        Args:
            query: Search query
            chunks: List of chunks
            top_k: Number of top results
            retrieval_weight: Weight for original retrieval score (0-1)
            rerank_weight: Weight for cross-encoder score (0-1)

        Returns:
            Re-ranked chunks with hybrid scores
        """
        if not chunks:
            return []

        # First, get rerank scores
        reranked_chunks = self.rerank(query, chunks, top_k=None, return_scores=True)

        # Normalize scores to 0-1 range
        rerank_scores = [c['rerank_score'] for c in reranked_chunks]
        retrieval_scores = [c.get('retrieval_score', c.get('final_score', 0.5)) for c in reranked_chunks]

        # Min-max normalization
        rerank_min, rerank_max = min(rerank_scores), max(rerank_scores)
        retrieval_min, retrieval_max = min(retrieval_scores), max(retrieval_scores)

        for i, chunk in enumerate(reranked_chunks):
            # Normalize rerank score
            if rerank_max > rerank_min:
                norm_rerank = (rerank_scores[i] - rerank_min) / (rerank_max - rerank_min)
            else:
                norm_rerank = 0.5

            # Normalize retrieval score
            if retrieval_max > retrieval_min:
                norm_retrieval = (retrieval_scores[i] - retrieval_min) / (retrieval_max - retrieval_min)
            else:
                norm_retrieval = 0.5

            # Compute hybrid score
            hybrid_score = (
                retrieval_weight * norm_retrieval +
                rerank_weight * norm_rerank
            )

            chunk['hybrid_score'] = hybrid_score
            chunk['normalized_rerank_score'] = norm_rerank
            chunk['normalized_retrieval_score'] = norm_retrieval
            chunk['score'] = hybrid_score  # Main score field

        # Re-sort by hybrid score
        reranked_chunks.sort(key=lambda x: x['hybrid_score'], reverse=True)

        # Limit to top_k
        if top_k is not None:
            reranked_chunks = reranked_chunks[:top_k]

        return reranked_chunks

    def compare_with_baseline(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 10
    ) -> Dict:
        """
        Compare re-ranking with baseline retrieval scores.

        Useful for evaluation and understanding the impact of re-ranking.

        Args:
            query: Search query
            chunks: List of chunks
            top_k: Number of top results to compare

        Returns:
            Comparison statistics and both rankings
        """
        if not chunks:
            return {
                'baseline_ranking': [],
                'reranked_ranking': [],
                'overlap': 0,
                'rank_changes': {}
            }

        # Get baseline top-k (by retrieval score)
        baseline_sorted = sorted(
            chunks,
            key=lambda x: x.get('score', x.get('retrieval_score', 0)),
            reverse=True
        )[:top_k]

        # Get reranked top-k
        reranked_sorted = self.rerank(query, chunks, top_k=top_k)

        # Calculate overlap
        baseline_ids = {c['chunk_id'] for c in baseline_sorted}
        reranked_ids = {c['chunk_id'] for c in reranked_sorted}
        overlap = len(baseline_ids & reranked_ids)

        # Track rank changes
        baseline_ranks = {c['chunk_id']: i for i, c in enumerate(baseline_sorted)}
        reranked_ranks = {c['chunk_id']: i for i, c in enumerate(reranked_sorted)}

        rank_changes = {}
        for chunk_id in baseline_ranks:
            if chunk_id in reranked_ranks:
                change = baseline_ranks[chunk_id] - reranked_ranks[chunk_id]
                if change != 0:
                    rank_changes[chunk_id] = {
                        'baseline_rank': baseline_ranks[chunk_id],
                        'reranked_rank': reranked_ranks[chunk_id],
                        'change': change
                    }

        return {
            'baseline_ranking': [c['chunk_id'] for c in baseline_sorted],
            'reranked_ranking': [c['chunk_id'] for c in reranked_sorted],
            'overlap': overlap,
            'overlap_percentage': (overlap / top_k) * 100,
            'rank_changes': rank_changes,
            'num_rank_changes': len(rank_changes),
            'new_in_top_k': list(reranked_ids - baseline_ids),
            'dropped_from_top_k': list(baseline_ids - reranked_ids)
        }

    def batch_rerank(
        self,
        query_chunk_pairs: List[tuple],
        top_k_per_query: Optional[int] = None
    ) -> List[List[Dict]]:
        """
        Re-rank multiple queries in batch.

        Args:
            query_chunk_pairs: List of (query, chunks) tuples
            top_k_per_query: Top-k results per query

        Returns:
            List of re-ranked results for each query
        """
        results = []
        for query, chunks in query_chunk_pairs:
            reranked = self.rerank(query, chunks, top_k=top_k_per_query)
            results.append(reranked)

        return results

    def get_score_distribution(self, chunks: List[Dict]) -> Dict:
        """
        Get statistics about score distribution.

        Args:
            chunks: List of chunks with scores

        Returns:
            Score distribution statistics
        """
        if not chunks:
            return {}

        scores = [c.get('rerank_score', c.get('score', 0)) for c in chunks]
        scores = np.array(scores)

        return {
            'mean': float(np.mean(scores)),
            'median': float(np.median(scores)),
            'std': float(np.std(scores)),
            'min': float(np.min(scores)),
            'max': float(np.max(scores)),
            'quartiles': {
                'q1': float(np.percentile(scores, 25)),
                'q2': float(np.percentile(scores, 50)),
                'q3': float(np.percentile(scores, 75))
            }
        }
