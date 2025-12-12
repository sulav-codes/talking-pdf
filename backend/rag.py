"""RAG (Retrieval Augmented Generation) implementation"""
import uuid
import logging
from typing import Tuple, List
from pathlib import Path

from groq import Groq
from sentence_transformers import SentenceTransformer

from db import collection
from utils import extract_text, chunk_text
from config import settings

logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(api_key=settings.GROQ_API_KEY)

# Initialize HuggingFace embedding model (Nomic)
logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
embedding_model = SentenceTransformer(
    settings.EMBEDDING_MODEL,
    trust_remote_code=True,
    token=settings.HF_TOKEN if settings.HF_TOKEN else None
)
logger.info("Embedding model loaded successfully")


def index_pdf(file_path: str) -> int:
    """
    Extract text from PDF, chunk it, and index into vector database
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Number of chunks indexed
    """
    try:
        logger.info(f"Starting indexing for: {file_path}")
        
        # Extract text from PDF
        text = extract_text(file_path)
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Extracted text is too short or empty")
        
        logger.info(f"Extracted {len(text)} characters from PDF")
        
        # Chunk the text
        chunks = chunk_text(
            text,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Batch process embeddings for efficiency
        batch_size = 32  # Optimized for sentence-transformers
        total_indexed = 0
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Generate embeddings using HuggingFace model (LOCAL - FAST!)
            embeddings = embedding_model.encode(
                batch,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Prepare data for batch insertion
            ids = [str(uuid.uuid4()) for _ in batch]
            embeddings_list = embeddings.tolist()  # Convert numpy to list for ChromaDB
            metadatas = [
                {
                    "source": Path(file_path).name,
                    "chunk_index": i + j,
                    "total_chunks": len(chunks)
                }
                for j in range(len(batch))
            ]
            
            # Add to collection
            collection.add(
                ids=ids,
                embeddings=embeddings_list,
                metadatas=metadatas,
                documents=batch
            )
            
            total_indexed += len(batch)
            logger.info(f"Indexed {total_indexed}/{len(chunks)} chunks")
        
        logger.info(f"Successfully indexed {total_indexed} chunks from {file_path}")
        return total_indexed
        
    except Exception as e:
        logger.error(f"Indexing failed for {file_path}: {e}", exc_info=True)
        raise


def query_rag(question: str, top_k: int = None) -> Tuple[str, List[str]]:
    """
    Query the RAG system with a question
    
    Args:
        question: The question to ask
        top_k: Number of context chunks to retrieve
        
    Returns:
        Tuple of (answer, list of source documents)
    """
    try:
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        logger.info(f"Processing query with top_k={top_k}")
        
        # Generate embedding for the question using HuggingFace (LOCAL - INSTANT!)
        query_embedding = embedding_model.encode(
            question,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        # Query the vector database
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        # Check if we have results
        if not results["documents"][0]:
            return "I don't have any documents indexed yet. Please upload a PDF first.", []
        
        # Extract documents and sources
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        
        # Build context from retrieved documents
        context_parts = []
        sources = []
        
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            context_parts.append(f"[Context {i+1}]\n{doc}")
            source = meta.get("source", "Unknown")
            if source not in sources:
                sources.append(source)
        
        context = "\n\n".join(context_parts)
        
        # Create prompt for Groq Llama 3
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "Use the context to provide accurate and detailed answers. "
            "If the context doesn't contain relevant information, say so clearly. "
            "Always cite which context section(s) you used in your answer."
        )
        
        user_prompt = (
            f"Context from documents:\n\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Please provide a detailed answer based on the context above."
        )
        
        # Generate answer using Groq (INSANELY FAST!)
        chat_response = groq_client.chat.completions.create(
            model=settings.CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = chat_response.choices[0].message.content
        
        logger.info(f"Generated answer with {len(sources)} sources")
        
        return answer, sources
        
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise
