"""FastAPI app for Pinecone-hosted semantic search."""
import base64
import io
import json
import logging
import os
import re
import uuid
from urllib.parse import quote
from typing import Any

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader
import requests

from config import settings
from db import clear_namespace, delete_records_by_upload_id, get_index_stats, pinecone_namespace, search_records, upsert_records

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=settings.TOP_K_RESULTS, ge=1, le=50)


class SearchMatch(BaseModel):
    id: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    namespace: str
    top_k: int
    matches: list[SearchMatch]


class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_indexed: int
    namespace: str


class IndexHealthResponse(BaseModel):
    status: str
    index_stats: dict[str, Any]


def _approx_token_chunks(text: str, max_words: int, overlap_words: int) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []

    if max_words <= overlap_words:
        raise ValueError("max_words must be greater than overlap_words")

    chunks: list[str] = []
    start = 0
    total_words = len(words)

    while start < total_words:
        end = min(start + max_words, total_words)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)

        if end >= total_words:
            break
        start = end - overlap_words

    return chunks


def _extract_pdf_text(file_content: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_content))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text)
    return "\n\n".join(pages)


def _normalize_hit(hit: dict[str, Any]) -> SearchMatch:
    return SearchMatch(
        id=str(hit.get("_id") or hit.get("id") or ""),
        score=hit.get("_score") or hit.get("score"),
        metadata=hit.get("fields") or hit.get("metadata") or {},
    )


def _is_service_role_key(supabase_key: str) -> bool:
    if not supabase_key:
        return False

    if supabase_key.startswith("sb_secret_"):
        return True
    if supabase_key.startswith("sb_publishable_") or supabase_key.startswith("sb_anon_"):
        return False

    parts = supabase_key.split(".")
    if len(parts) == 3:
        try:
            payload = parts[1]
            padding = "=" * (-len(payload) % 4)
            data = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
            claims = json.loads(data)
            return claims.get("role") == "service_role"
        except Exception:
            return True

    return True


def upload_pdf_to_supabase(file_content: bytes, filename: str, content_type: str = "application/pdf") -> str:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY or not settings.SUPABASE_BUCKET:
        raise RuntimeError(
            "Supabase storage is not configured. Set SUPABASE_URL, SUPABASE_SERVICE_KEY, and SUPABASE_BUCKET."
        )

    if not _is_service_role_key(settings.SUPABASE_SERVICE_KEY):
        raise RuntimeError("Supabase upload blocked: use a service-role key, not anon/publishable key.")

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
        raise RuntimeError(f"Supabase upload failed ({response.status_code}): {response.text}")

    return object_path


@app.get("/health", response_model=IndexHealthResponse)
async def health_check(response: Response):
    try:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return {"status": "ok", "index_stats": get_index_stats()}
    except Exception as exc:
        logger.exception("Health check failed")
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {exc}") from exc


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    _, file_ext = os.path.splitext(file.filename)
    file_ext = file_ext.lower()
    if not file_ext:
        raise HTTPException(status_code=400, detail="Missing file extension")
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_ext}")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    try:
        object_path = upload_pdf_to_supabase(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
        )
        logger.info("Stored PDF in Supabase at %s", object_path)
    except Exception as exc:
        logger.exception("Supabase upload failed")
        raise HTTPException(status_code=500, detail=f"Supabase upload failed: {exc}") from exc

    text = _extract_pdf_text(file_content)
    if not text.strip():
        raise HTTPException(status_code=400, detail="No extractable text found in PDF")

    chunks = _approx_token_chunks(text, settings.CHUNK_WORDS, settings.CHUNK_OVERLAP_WORDS)
    upload_id = str(uuid.uuid4())
    records: list[dict[str, Any]] = []
    total_chunks = len(chunks)

    for index, chunk_text in enumerate(chunks):
        records.append(
            {
                "_id": f"{upload_id}-{index}",
                "upload_id": upload_id,
                "text": chunk_text,
                "source": file.filename,
                "chunk_index": index,
                "total_chunks": total_chunks,
            }
        )

    batch_size = 96
    try:
        delete_records_by_upload_id(upload_id)
        for start in range(0, len(records), batch_size):
            upsert_records(records[start : start + batch_size])
    except Exception as exc:
        logger.exception("Pinecone ingestion failed, cleaning up upload %s", upload_id)
        try:
            delete_records_by_upload_id(upload_id)
        except Exception:
            logger.exception("Rollback cleanup failed for upload %s", upload_id)
        raise HTTPException(status_code=500, detail=f"Pinecone ingestion failed: {exc}") from exc

    return {
        "message": "File indexed successfully",
        "filename": file.filename,
        "chunks_indexed": total_chunks,
        "namespace": pinecone_namespace,
    }


@app.post("/query", response_model=SearchResponse)
async def ask_question(request: QueryRequest):
    try:
        matches = search_records(request.question, request.top_k)
        return {
            "query": request.question,
            "namespace": pinecone_namespace,
            "top_k": request.top_k,
            "matches": [_normalize_hit(match) for match in matches],
        }
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@app.delete("/collection")
async def clear_pinecone_index():
    try:
        clear_namespace()
        return {"message": "Pinecone namespace cleared successfully", "namespace": pinecone_namespace}
    except Exception as exc:
        logger.exception("Failed to clear namespace")
        raise HTTPException(status_code=500, detail=f"Failed to clear index: {exc}") from exc


@app.get("/stats")
async def get_index_statistics():
    try:
        return get_index_stats()
    except Exception as exc:
        logger.exception("Failed to get stats")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))