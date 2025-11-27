import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from app.core.config import settings
import uuid
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages vector storage and retrieval for resumes."""

    def __init__(self):
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(settings.vector_db_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(settings.embedding_model)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="resumes",
            metadata={"description": "Resume embeddings for similarity search"}
        )

    def add_resume(
        self,
        resume_text: str,
        metadata: Dict = None,
        resume_id: str = None
    ) -> str:
        """Add a resume to the vector store."""
        if resume_id is None:
            resume_id = str(uuid.uuid4())

        # Generate embedding
        embedding = self.embedding_model.encode(resume_text).tolist()

        # Add to collection
        self.collection.add(
            ids=[resume_id],
            embeddings=[embedding],
            documents=[resume_text],
            metadatas=[metadata or {}]
        )

        return resume_id

    def search_similar_resumes(
        self,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict]:
        """Search for similar resumes based on query text."""
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query_text).tolist()

        # Search in collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        # Format results
        similar_resumes = []
        if results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                similar_resumes.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None
                })

        return similar_resumes

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        emb1 = self.embedding_model.encode(text1)
        emb2 = self.embedding_model.encode(text2)

        # Cosine similarity
        from numpy import dot
        from numpy.linalg import norm

        similarity = dot(emb1, emb2) / (norm(emb1) * norm(emb2))
        return float(similarity)

    def delete_resume(self, resume_id: str):
        """Delete a resume from the vector store."""
        self.collection.delete(ids=[resume_id])

    def count_resumes(self) -> int:
        """Get total number of resumes in the store."""
        return self.collection.count()

    # New methods for semantic chunk support

    def add_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict
    ) -> str:
        """
        Add a semantic chunk to the vector store.

        Args:
            chunk_id: Unique identifier for the chunk
            content: Text content of the chunk
            metadata: Metadata dictionary (source_type, chunk_type, etc.)

        Returns:
            chunk_id
        """
        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()

        # Add to collection
        self.collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )

        return chunk_id

    def add_chunks_batch(
        self,
        chunks: List[Dict]
    ) -> List[str]:
        """
        Add multiple chunks in batch for better performance.

        Args:
            chunks: List of chunk dictionaries with 'chunk_id', 'content', 'metadata'

        Returns:
            List of chunk IDs
        """
        if not chunks:
            return []

        # Extract data
        chunk_ids = [c['chunk_id'] for c in chunks]
        contents = [c['content'] for c in chunks]
        metadatas = [c.get('metadata', {}) for c in chunks]

        # Generate embeddings in batch
        embeddings = self.embedding_model.encode(contents).tolist()

        # Add to collection
        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )

        return chunk_ids

    def search_similar_chunks(
        self,
        query_text: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar chunks based on query text.

        Args:
            query_text: The search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {'source_type': 'resume'})

        Returns:
            List of similar chunks with scores and metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query_text).tolist()

        # Prepare where clause for filtering
        where_clause = filter_metadata if filter_metadata else None

        # Search in collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )

        # Format results
        similar_chunks = []
        if results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                similar_chunks.append({
                    "id": results["ids"][0][i],
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                    "score": 1 - results["distances"][0][i] if results.get("distances") else 0.5
                })

        return similar_chunks

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """
        Retrieve a specific chunk by ID.

        Args:
            chunk_id: The chunk identifier

        Returns:
            Chunk dictionary or None if not found
        """
        try:
            results = self.collection.get(ids=[chunk_id])

            if results["ids"] and len(results["ids"]) > 0:
                return {
                    "chunk_id": results["ids"][0],
                    "content": results["documents"][0] if results["documents"] else "",
                    "metadata": results["metadatas"][0] if results["metadatas"] else {}
                }
        except Exception as e:
            logger.error(f"Error retrieving chunk {chunk_id}: {str(e)}")

        return None

    def delete_chunks(self, chunk_ids: List[str]):
        """Delete multiple chunks by ID."""
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)

    def delete_by_metadata(self, metadata_filter: Dict):
        """
        Delete chunks matching metadata filter.

        Args:
            metadata_filter: Metadata filter (e.g., {'resume_id': 'abc123'})
        """
        self.collection.delete(where=metadata_filter)

    def get_all_metadata(self, field: str) -> List[any]:
        """
        Get all unique values for a metadata field.

        Args:
            field: Metadata field name (e.g., 'source_type', 'chunk_type')

        Returns:
            List of unique values
        """
        # ChromaDB doesn't have a direct way to get unique metadata values
        # We'd need to query all documents and extract unique values
        # For now, return empty list (can be implemented if needed)
        return []
