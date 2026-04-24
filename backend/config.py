"""Configuration management for the Pinecone semantic search backend."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).parent.resolve()


class Settings:
    """Application settings and validation."""

    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_HOST: str = os.getenv("PINECONE_INDEX_HOST", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "")
    PINECONE_NAMESPACE: str = os.getenv("PINECONE_NAMESPACE", "default")
    PINECONE_EMBEDDING_MODEL: str = os.getenv("PINECONE_EMBEDDING_MODEL", "llama-text-embed-v2")
    PINECONE_TEXT_FIELD: str = os.getenv("PINECONE_TEXT_FIELD", "chunk_text")

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "")
    SUPABASE_UPLOAD_PREFIX: str = os.getenv("SUPABASE_UPLOAD_PREFIX", "pdfs")

    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: set[str] = {".pdf"}
    CHUNK_WORDS: int = int(os.getenv("CHUNK_WORDS", "500"))
    CHUNK_OVERLAP_WORDS: int = int(os.getenv("CHUNK_OVERLAP_WORDS", "50"))
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "4"))

    API_TITLE: str = "Pinecone Semantic Search Backend"
    API_VERSION: str = "3.0.0"
    API_DESCRIPTION: str = "FastAPI backend using Pinecone integrated embeddings for text ingestion and semantic search."

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
    ]

    def __init__(self):
        if not self.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY environment variable is required")
        if not self.PINECONE_INDEX_HOST and not self.PINECONE_INDEX_NAME:
            raise ValueError("PINECONE_INDEX_HOST or PINECONE_INDEX_NAME environment variable is required")


settings = Settings()
