"""
Configuration management for the RAG Chatbot Backend
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the backend directory (where this config file is located)
BACKEND_DIR = Path(__file__).parent.resolve()

class Settings:
    """Application settings and configuration"""
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    
    # Model Configuration
    EMBEDDING_MODEL: str = "nomic-ai/nomic-embed-text-v1.5"  # HuggingFace model
    CHAT_MODEL: str = "llama-3.1-8b-instant"  # Groq Llama 3.1 8B (current model)
    
    # Database Configuration
    CHROMA_PERSIST_DIR: Path = BACKEND_DIR / "chroma_db"
    COLLECTION_NAME: str = "pdf_documents"
    
    # Upload Configuration
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".pdf"}
    
    # RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RESULTS: int = 4
    
    # API Configuration
    API_TITLE: str = "RAG Chatbot Backend"
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = "A professional RAG-based chatbot for PDF documents using free APIs (HuggingFace + Groq)"
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
    ]
    
    def __init__(self):
        """Validate settings on initialization"""
        if not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        # HF_TOKEN is optional but recommended for better rate limits
        if not self.HF_TOKEN:
            import warnings
            warnings.warn("HF_TOKEN not set. You may experience rate limits with HuggingFace API.")
        
        # Create upload directory if it doesn't exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create chroma persist directory if it doesn't exist
        self.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

# Global settings instance
settings = Settings()
