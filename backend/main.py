"""Main FastAPI application for RAG Chatbot Backend"""
import os
import shutil
from pathlib import Path
from typing import Optional, Literal

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging

from config import settings
from rag import index_pdf, query_rag, query_rag_langchain
from db import get_collection_stats, clear_collection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """Request model for querying the RAG system"""
    question: str = Field(..., min_length=1, max_length=1000, description="Question to ask")
    top_k: Optional[int] = Field(default=None, ge=1, le=10, description="Number of context chunks to retrieve")
    engine: Literal["direct", "langchain"] = Field(
        default="direct",
        description="Query pipeline to use"
    )


class CompareQueryRequest(BaseModel):
    """Request model for comparing direct and LangChain query pipelines"""
    question: str = Field(..., min_length=1, max_length=1000, description="Question to ask")
    top_k: Optional[int] = Field(default=None, ge=1, le=10, description="Number of context chunks to retrieve")


class QueryResponse(BaseModel):
    """Response model for RAG queries"""
    answer: str
    sources: list[str]
    engine: Literal["direct", "langchain"]


class CompareQueryResponse(BaseModel):
    """Response model for comparing both query pipelines"""
    question: str
    top_k: int
    direct: QueryResponse
    langchain: QueryResponse
    

class UploadResponse(BaseModel):
    """Response model for file uploads"""
    message: str
    filename: str
    chunks_indexed: int


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    collection_stats: dict


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with collection statistics"""
    try:
        stats = get_collection_stats()
        return {
            "status": "ok",
            "collection_stats": stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Save file
        file_path = settings.UPLOAD_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Uploaded file: {file.filename} ({file_size} bytes)")
        
        # Index the PDF
        chunks_count = index_pdf(str(file_path))
        
        logger.info(f"Indexed {chunks_count} chunks from {file.filename}")
        
        return {
            "message": "File uploaded and indexed successfully",
            "filename": file.filename,
            "chunks_indexed": chunks_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def ask_question(request: QueryRequest):

    try:
        top_k = request.top_k or settings.TOP_K_RESULTS
        engine = request.engine
        
        logger.info(f"Processing {engine} query: {request.question[:50]}...")
        
        if engine == "langchain":
            answer, sources = query_rag_langchain(request.question, top_k=top_k)
        else:
            answer, sources = query_rag(request.question, top_k=top_k)
        
        return {
            "answer": answer,
            "sources": sources,
            "engine": engine
        }
        
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/query/compare", response_model=CompareQueryResponse)
async def compare_query_paths(request: CompareQueryRequest):
    """Run the same query through both direct and LangChain pipelines."""
    try:
        top_k = request.top_k or settings.TOP_K_RESULTS

        logger.info(f"Comparing query pipelines for: {request.question[:50]}...")

        direct_answer, direct_sources = query_rag(request.question, top_k=top_k)
        lc_answer, lc_sources = query_rag_langchain(request.question, top_k=top_k)

        return {
            "question": request.question,
            "top_k": top_k,
            "direct": {
                "answer": direct_answer,
                "sources": direct_sources,
                "engine": "direct"
            },
            "langchain": {
                "answer": lc_answer,
                "sources": lc_sources,
                "engine": "langchain"
            }
        }

    except Exception as e:
        logger.error(f"Query comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query comparison failed: {str(e)}")


@app.delete("/collection")
async def clear_all_documents():
    """Clear all documents from the collection"""
    try:
        clear_collection()
        logger.info("Collection cleared")
        return {"message": "Collection cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear collection: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get collection statistics"""
    try:
        return get_collection_stats()
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
