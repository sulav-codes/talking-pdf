"""Database configuration and initialization for Pinecone"""
import logging
from pinecone import Pinecone

# Use the refactored, cloud-ready settings
from config import settings

logger = logging.getLogger(__name__)

# This will be our global Pinecone index object
pinecone_index = None

try:
    # 1. Initialize Pinecone Client
    logger.info("Initializing Pinecone client...")
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    
    index_name = settings.PINECONE_INDEX_NAME

    # 2. Check if the index exists. If not, raise an error.
    # In a cloud setup, we assume the index has been created beforehand.
    if index_name not in pc.list_indexes().names():
        logger.error(f"Pinecone index '{index_name}' not found!")
        logger.error("Please create the index in the Pinecone console with the following specs:")
        logger.error(f"  - Name: {index_name}")
        logger.error(f"  - Dimension: {settings.EMBEDDING_DIMENSION}")
        logger.error("  - Metric: cosine")
        raise NameError(f"Pinecone index '{index_name}' does not exist.")

    # 3. Connect to the existing index
    pinecone_index = pc.Index(index_name)
    
    logger.info(f"Successfully connected to Pinecone index: '{index_name}'")
    
    # Optional: Log initial stats
    stats = pinecone_index.describe_index_stats()
    logger.info(f"Index stats: {stats}")

except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {e}")
    # Re-raise the exception to halt application startup if the DB isn't available
    raise


def get_index_stats() -> dict:
    """
    Get statistics about the current Pinecone index.

    Returns:
        Dictionary with index statistics.
    """
    if not pinecone_index:
        return {"error": "Pinecone index not initialized"}
        
    try:
        stats = pinecone_index.describe_index_stats()
        return {
            "name": pinecone_index.name,
            "vector_count": stats.get('total_vector_count', 0),
            "dimension": stats.get('dimension', 0),
            "index_fullness": stats.get('index_fullness', 0.0),
        }
    except Exception as e:
        logger.error(f"Failed to get Pinecone index stats: {e}")
        return {
            "name": settings.PINECONE_INDEX_NAME,
            "vector_count": 0,
            "error": str(e)
        }


def clear_index():
    """
    Clear all vectors from the Pinecone index.
    This does NOT delete the index itself.
    """
    if not pinecone_index:
        raise ConnectionError("Pinecone index not initialized, cannot clear.")
        
    try:
        # The 'delete_all' parameter removes all vectors from the index
        pinecone_index.delete(delete_all=True)
        logger.info(f"All vectors cleared from index '{pinecone_index.name}'.")
        
    except Exception as e:
        logger.error(f"Failed to clear Pinecone index: {e}")
        raise