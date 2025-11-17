import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
from app.core.config import settings
import uuid


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
