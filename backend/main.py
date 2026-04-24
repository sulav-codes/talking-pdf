"""Main FastAPI application for RAG Chatbot Backend - Cloud Ready"""
import base64
import io
import json
import uuid
import logging
from typing import Optional, Literal
from urllib.parse import quote

import requests

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import from our refactored, cloud-ready modules
from config import settings
from rag import index_pdf, query_rag, query_rag_langchain
from db import get_index_stats, clear_index

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _is_service_role_key(supabase_key: str) -> bool:
    """Best-effort check that key is service-role or secret key, not anon/publishable."""
    if not supabase_key:
        return False

    if supabase_key.startswith("sb_secret_"):
        return True
    if supabase_key.startswith("sb_publishable_") or supabase_key.startswith("sb_anon_"):
        return False

    # Legacy JWT-style keys: decode payload and check role claim when possible.
    parts = supabase_key.split(".")
    if len(parts) == 3:
        try:
            payload = parts[1]
            padding = "=" * (-len(payload) % 4)
            data = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
            claims = json.loads(data)
            return claims.get("role") == "service_role"
        except Exception:
            # If parsing fails, let request proceed and rely on Supabase response.
            return True

    return True


def upload_pdf_to_supabase(file_content: bytes, filename: str, content_type: str = "application/pdf") -> str:
    """Upload PDF bytes to Supabase Storage and return the object path."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY or not settings.SUPABASE_BUCKET:
        raise RuntimeError(
            "Supabase storage is not configured. Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SERVICE_KEY), and SUPABASE_BUCKET."
        )

    if not _is_service_role_key(settings.SUPABASE_SERVICE_KEY):
        raise RuntimeError(
            "Supabase upload blocked: use a service-role key, not anon/publishable key. "
            "Set SUPABASE_SERVICE_ROLE_KEY in backend .env."
        )

    object_path = f"{settings.SUPABASE_UPLOAD_PREFIX.strip('/')}/{uuid.uuid4()}-{filename}"
    encoded_object_path = quote(object_path, safe="/-_.")
    endpoint = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{settings.SUPABASE_BUCKET}/{encoded_object_path}"

    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    response = requests.post(endpoint, headers=headers, data=file_content, timeout=30)
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Supabase upload failed ({response.status_code}): {response.text}. "
            "If message mentions RLS, ensure backend uses SUPABASE_SERVICE_ROLE_KEY and URL/key belong to same project."
        )

    return object_path

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# Add CORS middleware (uses the flexible config from settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Models
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(default=None, ge=1, le=10)
    # The 'engine' parameter is kept for API compatibility, but logic now defaults to LangChain
    engine: Literal["direct", "langchain"] = Field(default="langchain")

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    engine: Literal["direct", "langchain"]

class CompareQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(default=None, ge=1, le=10)

class CompareQueryResponse(BaseModel):
    question: str
    top_k: int
    direct: QueryResponse
    langchain: QueryResponse
    
class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_indexed: int

class IndexHealthResponse(BaseModel):
    status: str
    index_stats: dict


# API Endpoints

@app.get("/health", response_model=IndexHealthResponse, summary="Check service health and vector index status")
async def health_check():
    """Health check endpoint with Pinecone index statistics."""
    try:
        # UPDATED: from get_collection_stats to get_index_stats
        stats = get_index_stats()
        return {
            "status": "ok",
            "index_stats": stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {e}")


@app.post("/upload", response_model=UploadResponse, summary="Upload and index a PDF document")
async def upload_pdf(file: UploadFile = File(...)):

    # 1. Validate file metadata
    file_ext = file.filename.split(".")[-1].lower()
    if f".{file_ext}" not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_ext}")

    try:
        # 2. Read file content into memory
        file_content = await file.read()
        
        # 3. Validate file content size
        if len(file_content) > settings.MAX_FILE_SIZE:
            mb_size = settings.MAX_FILE_SIZE / 1024 / 1024
            raise HTTPException(status_code=400, detail=f"File too large. Max size: {mb_size:.1f}MB")
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")

        logger.info(f"Uploaded file: {file.filename} ({len(file_content)} bytes)")

        # 4. Upload original PDF to Supabase Storage
        object_path = upload_pdf_to_supabase(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
        )
        logger.info(f"Stored PDF in Supabase bucket at: {object_path}")
        
        # 5. Create an in-memory file-like object
        file_stream = io.BytesIO(file_content)
        
        # 6. Index the PDF using the refactored function
        chunks_count = index_pdf(file_stream, file.filename)
        
        logger.info(f"Indexed {chunks_count} chunks from {file.filename}")
        
        return {
            "message": "File uploaded and indexed successfully",
            "filename": file.filename,
            "chunks_indexed": chunks_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.post("/query", response_model=QueryResponse, summary="Ask a question to the RAG system")
async def ask_question(request: QueryRequest):
    """Queries the RAG system using the selected engine."""
    try:
        top_k = request.top_k or settings.TOP_K_RESULTS
        logger.info(f"Processing {request.engine} query: '{request.question[:50]}...'")
        
        if request.engine == "direct":
            answer, sources = query_rag(request.question, top_k=top_k)
        else:
            answer, sources = query_rag_langchain(request.question, top_k=top_k)
        
        return { "answer": answer, "sources": sources, "engine": request.engine }
        
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@app.post("/query/compare", response_model=CompareQueryResponse, summary="Compare direct and LangChain query paths")
async def compare_query_paths(request: CompareQueryRequest):
    """Runs the same query through both direct and LangChain pipelines."""
    try:
        top_k = request.top_k or settings.TOP_K_RESULTS
        logger.info(f"Comparing query pipelines for: '{request.question[:50]}...'")
        
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
        raise HTTPException(status_code=500, detail=f"Query comparison failed: {e}")


@app.delete("/collection", summary="Clear all documents from the Pinecone index")
async def clear_pinecone_index():
    """Deletes all vectors from the configured Pinecone index."""
    try:
        clear_index()
        logger.info("Pinecone index cleared successfully.")
        return {"message": "Pinecone index cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear index: {e}")


@app.get("/stats", summary="Get statistics about the Pinecone index")
async def get_index_statistics():
    """Retrieves and returns statistics from the Pinecone index."""
    try:
        return get_index_stats()
    except Exception as e:
        logger.error(f"Failed to get index stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for local development...")
    uvicorn.run(app, host="localhost", port=8000)