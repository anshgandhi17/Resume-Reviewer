from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from pathlib import Path
from typing import List
import logging


class FeatureFlags(BaseSettings):
    """Feature flags for enabling/disabling functionality."""
    enable_enhanced_rag: bool = Field(default=True, description="Enable enhanced RAG pipeline")
    enable_hyde: bool = Field(default=True, description="Enable HyDE query expansion")
    enable_reranking: bool = Field(default=True, description="Enable cross-encoder re-ranking")
    enable_star_formatting: bool = Field(default=False, description="Enable STAR format rewriting")
    enable_pdf_generation: bool = Field(default=False, description="Enable PDF resume generation")
    enable_batch_upload: bool = Field(default=False, description="Enable parallel multi-resume upload")
    enable_evaluation: bool = Field(default=False, description="Enable evaluation framework")
    enable_tracing: bool = Field(default=False, description="Enable Arize Phoenix tracing")

    model_config = ConfigDict(
        env_prefix="FEATURE_",
        case_sensitive=False
    )


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

    # STAR Formatting Settings (Phase 3)
    star_llm_model: str = "llama3.2"           # LLM model for STAR formatting
    star_temperature: float = 0.3              # Low temperature for factual rewriting
    star_validation_strictness: str = "high"   # Validation strictness: low, medium, high

    # PDF Generation Settings (Phase 4)
    pdf_template_path: Path = Path("./app/templates/jakes_resume.tex")
    pdf_output_dir: Path = Path("./data/outputs")
    latex_compile_timeout: int = 30            # Seconds

    # Batch Upload Settings (Phase 2)
    batch_max_files: int = 5                   # Maximum files per batch
    batch_timeout_per_file: int = 60           # Seconds per file
    batch_use_parallel: bool = True            # Use parallel processing

    # Concurrency Settings (Memory Management)
    max_concurrent_llm_calls: int = 3          # Max parallel LLM calls (Ollama)
    max_concurrent_pdf_processing: int = 5     # Max parallel PDF parsing
    enable_resource_monitoring: bool = True    # Monitor CPU/memory and adjust
    sequential_mode_memory_threshold_gb: float = 2.0  # Switch to sequential if <2GB free

    # Logging Settings
    log_level: str = "INFO"                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = ""                         # Empty = no file logging

    # Data Storage Paths
    data_dir: Path = Path("./data")
    knowledge_base_dir: Path = Path("./data/knowledge_base")
    evaluation_results_dir: Path = Path("./evaluation_results")

    # Feature Flags
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__"
    )


settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
settings.pdf_output_dir.mkdir(parents=True, exist_ok=True)
settings.evaluation_results_dir.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)

if settings.log_file:
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setFormatter(logging.Formatter(settings.log_format))
    logging.getLogger().addHandler(file_handler)
