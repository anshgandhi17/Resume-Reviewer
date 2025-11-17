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

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
