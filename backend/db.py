"""Database configuration and initialization for ChromaDB"""
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings

logger = logging.getLogger(__name__)

# Initialize ChromaDB with persistent storage
try:
    chroma_client = chromadb.Client(
        ChromaSettings(
            persist_directory=str(settings.CHROMA_PERSIST_DIR),
            anonymized_telemetry=False
        )
    )
    
    # Get or create collection with metadata
    collection = chroma_client.get_or_create_collection(
        name=settings.COLLECTION_NAME,
        metadata={"description": "PDF document embeddings for RAG chatbot"}
    )
    
    logger.info(f"ChromaDB initialized with collection: {settings.COLLECTION_NAME}")
    logger.info(f"Persist directory: {settings.CHROMA_PERSIST_DIR}")
    
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB: {e}")
    raise


def get_collection_stats() -> dict:
    """
    Get statistics about the current collection
    
    Returns:
        Dictionary with collection statistics
    """
    try:
        count = collection.count()
        return {
            "name": settings.COLLECTION_NAME,
            "document_count": count,
            "persist_directory": settings.CHROMA_PERSIST_DIR
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {
            "name": settings.COLLECTION_NAME,
            "document_count": 0,
            "error": str(e)
        }


def clear_collection():
    """
    Clear all documents from the collection
    """
    global collection, chroma_client
    
    try:
        # Delete the collection
        chroma_client.delete_collection(name=settings.COLLECTION_NAME)
        
        # Recreate it
        collection = chroma_client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            metadata={"description": "PDF document embeddings for RAG chatbot"}
        )
        
        logger.info("Collection cleared and recreated")
        
    except Exception as e:
        logger.error(f"Failed to clear collection: {e}")
        raise
