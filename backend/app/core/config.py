from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from pathlib import Path


class Settings(BaseSettings):
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # Application Settings
    upload_dir: Path = Path("./uploads")
    vector_db_dir: Path = Path("./vectordb")
    max_file_size: int = 10485760  # 10MB

    # CORS Settings
    cors_origins: list = ["http://localhost:3000"]

    # Embedding Model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Advanced RAG Configuration ---

    # Cross-Encoder Model for Re-ranking
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Retrieval Settings
    retrieval_top_k: int = 30  # Initial retrieval count (before re-ranking)
    rerank_top_k: int = 10     # Final count after re-ranking
    use_hyde: bool = True      # Enable HyDE query expansion
    use_reranking: bool = True # Enable cross-encoder re-ranking

    # HyDE Settings
    hyde_num_documents: int = 5        # Number of hypothetical documents to generate
    hyde_strategy: str = "bullets"     # 'bullets' or 'experiences'
    hyde_temperature: float = 0.7      # LLM temperature for generation

    # Hybrid Scoring Weights (for combining retrieval + rerank scores)
    retrieval_score_weight: float = 0.3
    rerank_score_weight: float = 0.7

    # ChromaDB HNSW Parameters
    # ef_construction: size of dynamic candidate list during index construction (higher = better quality, slower)
    # ef_search: size of dynamic candidate list during search (higher = more accurate, slower)
    # M: number of bi-directional links per element (higher = better recall, more memory)
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 100
    hnsw_m: int = 16

    # Evaluation Settings
    enable_tracing: bool = False        # Enable Arize Phoenix tracing
    phoenix_port: int = 6006            # Port for Phoenix UI
    enable_ragas: bool = False          # Enable Ragas evaluation
    ragas_testset_size: int = 20        # Size of test set for evaluation

    # Chunking Settings
    enable_semantic_chunking: bool = True  # Use semantic chunking vs simple splitting
    min_chunk_size: int = 100             # Minimum characters per chunk
    max_chunk_size: int = 2000            # Maximum characters per chunk

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
