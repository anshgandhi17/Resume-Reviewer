"""
Advanced Retriever Service
Implements retrieval with HyDE (Hypothetical Document Embeddings) integration.
"""

from typing import List, Dict, Optional
import logging
from collections import defaultdict

from app.services.hyde import HyDEService
from app.core.config import settings

logger = logging.getLogger(__name__)


class AdvancedRetriever:
    """
    Advanced retrieval service that combines:
    1. Direct query embedding search
    2. HyDE (hypothetical document) search
    3. Deduplication and merging of results
    """

    def __init__(self, vector_store, hyde_service: Optional[HyDEService] = None):
        """
        Initialize Advanced Retriever.

        Args:
            vector_store: VectorStore instance for similarity search
            hyde_service: Optional HyDEService instance
        """
        self.vector_store = vector_store
        self.hyde_service = hyde_service or HyDEService()

    def retrieve(
        self,
        query: str,
        top_k: int = 30,
        use_hyde: bool = True,
        hyde_strategy: str = 'bullets',
        num_hyde_docs: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve relevant chunks using advanced techniques.

        Args:
            query: The search query (usually a job description)
            top_k: Number of results to return
            use_hyde: Whether to use HyDE query expansion
            hyde_strategy: 'bullets' or 'experiences' for HyDE generation
            num_hyde_docs: Number of hypothetical documents to generate
            filter_metadata: Optional metadata filters for vector search

        Returns:
            List of retrieved chunks with scores and metadata
        """
        all_results = []
        seen_chunk_ids = set()

        try:
            # Step 1: Direct query retrieval (baseline)
            logger.info("Performing direct query retrieval")
            direct_results = self._search_with_query(
                query,
                n_results=top_k // 2,  # Get fewer from direct search
                filter_metadata=filter_metadata
            )

            # Add direct results
            for result in direct_results:
                if result['chunk_id'] not in seen_chunk_ids:
                    result['retrieval_method'] = 'direct'
                    all_results.append(result)
                    seen_chunk_ids.add(result['chunk_id'])

            # Step 2: HyDE-based retrieval
            if use_hyde:
                logger.info(f"Performing HyDE retrieval with strategy: {hyde_strategy}")

                # Generate hypothetical documents
                hyde_expansion = self.hyde_service.expand_query(
                    query,
                    strategy=hyde_strategy
                )

                hypothetical_docs = hyde_expansion['hypothetical_documents']
                logger.info(f"Generated {len(hypothetical_docs)} hypothetical documents")

                # Search with each hypothetical document
                for i, hyde_doc in enumerate(hypothetical_docs):
                    hyde_results = self._search_with_query(
                        hyde_doc,
                        n_results=top_k // len(hypothetical_docs) + 1,
                        filter_metadata=filter_metadata
                    )

                    # Add hyde results (deduplicate by chunk_id)
                    for result in hyde_results:
                        if result['chunk_id'] not in seen_chunk_ids:
                            result['retrieval_method'] = f'hyde_{i}'
                            result['hyde_query'] = hyde_doc[:100] + '...'  # Truncate for logging
                            all_results.append(result)
                            seen_chunk_ids.add(result['chunk_id'])

            # Step 3: Sort by relevance score and limit to top_k
            all_results = self._merge_and_rank_results(all_results, top_k)

            logger.info(
                f"Retrieved {len(all_results)} unique chunks "
                f"(direct: {sum(1 for r in all_results if r['retrieval_method'] == 'direct')}, "
                f"hyde: {sum(1 for r in all_results if r['retrieval_method'].startswith('hyde'))})"
            )

            return all_results

        except Exception as e:
            logger.error(f"Error in advanced retrieval: {str(e)}")
            # Fallback to simple direct retrieval
            return self._search_with_query(query, n_results=top_k, filter_metadata=filter_metadata)

    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 20,
        use_hyde: bool = True,
        include_adjacent: bool = False
    ) -> Dict:
        """
        Retrieve chunks with additional context.

        Args:
            query: Search query
            top_k: Number of results
            use_hyde: Use HyDE expansion
            include_adjacent: Include adjacent chunks for context

        Returns:
            Dictionary with results and metadata
        """
        # Get primary results
        results = self.retrieve(
            query=query,
            top_k=top_k,
            use_hyde=use_hyde
        )

        # Optionally include adjacent chunks for better context
        if include_adjacent:
            results = self._add_adjacent_chunks(results)

        return {
            'results': results,
            'query': query,
            'total_retrieved': len(results),
            'hyde_used': use_hyde
        }

    def _search_with_query(
        self,
        query_text: str,
        n_results: int,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform similarity search with the vector store.

        Args:
            query_text: Text to search with
            n_results: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results
        """
        try:
            # Use vector store's search method
            results = self.vector_store.search_similar_chunks(
                query_text=query_text,
                n_results=n_results,
                filter_metadata=filter_metadata
            )

            # Normalize result format
            normalized_results = []
            for result in results:
                normalized_results.append({
                    'chunk_id': result.get('id') or result.get('chunk_id'),
                    'content': result.get('text') or result.get('content'),
                    'metadata': result.get('metadata', {}),
                    'score': 1 - result.get('distance', 0) if result.get('distance') is not None else 0.5,
                    'distance': result.get('distance', 0)
                })

            return normalized_results

        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []

    def _merge_and_rank_results(
        self,
        results: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Merge and rank results from multiple retrieval methods.

        Implements a simple ranking based on:
        1. Similarity score
        2. Retrieval method (direct queries get slight boost)
        3. Frequency of retrieval (if same chunk retrieved multiple times)
        """
        # Count how many times each chunk was retrieved
        chunk_frequency = defaultdict(int)
        chunk_data = {}

        for result in results:
            chunk_id = result['chunk_id']
            chunk_frequency[chunk_id] += 1

            # Keep best score for each chunk
            if chunk_id not in chunk_data or result['score'] > chunk_data[chunk_id]['score']:
                chunk_data[chunk_id] = result

        # Calculate final scores
        final_results = []
        for chunk_id, data in chunk_data.items():
            # Boost score based on frequency (retrieved by multiple queries)
            frequency_boost = min(chunk_frequency[chunk_id] * 0.05, 0.2)  # Max 20% boost

            # Slight boost for direct retrieval
            method_boost = 0.05 if data['retrieval_method'] == 'direct' else 0.0

            final_score = data['score'] + frequency_boost + method_boost
            final_score = min(final_score, 1.0)  # Cap at 1.0

            data['final_score'] = final_score
            data['frequency'] = chunk_frequency[chunk_id]
            final_results.append(data)

        # Sort by final score
        final_results.sort(key=lambda x: x['final_score'], reverse=True)

        return final_results[:top_k]

    def _add_adjacent_chunks(self, results: List[Dict]) -> List[Dict]:
        """
        Add adjacent chunks (previous/next in same document) for context.

        This can be useful for providing more context around a retrieved chunk.
        """
        # TODO: Implement if vector store supports fetching by resume_id + chunk_index
        # For now, return results as-is
        return results

    def get_retrieval_stats(self, results: List[Dict]) -> Dict:
        """
        Get statistics about retrieval results.

        Args:
            results: List of retrieval results

        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_chunks': len(results),
            'retrieval_methods': defaultdict(int),
            'chunk_types': defaultdict(int),
            'source_types': defaultdict(int),
            'avg_score': 0,
            'min_score': 1.0,
            'max_score': 0.0
        }

        if not results:
            return stats

        for result in results:
            # Retrieval method breakdown
            method = result.get('retrieval_method', 'unknown')
            stats['retrieval_methods'][method] += 1

            # Chunk type breakdown
            chunk_type = result.get('metadata', {}).get('chunk_type', 'unknown')
            stats['chunk_types'][chunk_type] += 1

            # Source type breakdown
            source_type = result.get('metadata', {}).get('source_type', 'unknown')
            stats['source_types'][source_type] += 1

            # Score statistics
            score = result.get('final_score') or result.get('score', 0)
            stats['avg_score'] += score
            stats['min_score'] = min(stats['min_score'], score)
            stats['max_score'] = max(stats['max_score'], score)

        stats['avg_score'] /= len(results)

        # Convert defaultdicts to regular dicts
        stats['retrieval_methods'] = dict(stats['retrieval_methods'])
        stats['chunk_types'] = dict(stats['chunk_types'])
        stats['source_types'] = dict(stats['source_types'])

        return stats
