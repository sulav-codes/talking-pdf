"""FastAPI app for Pinecone-hosted semantic search."""
import io
import logging
import os
import re
import uuid
from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader

from config import settings
from db import clear_namespace, delete_records_by_upload_id, get_index_stats, pinecone_namespace, search_records, upsert_records
from rag import query_rag_langchain

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
    engine: Literal["direct", "langchain"] = Field(default="direct")


class CompareQueryRequest(BaseModel):
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
    answer: str
    sources: list[str]
    engine: Literal["direct", "langchain"]
    matches: list[SearchMatch]


class CompareQueryResponse(BaseModel):
    question: str
    top_k: int
    direct: SearchResponse
    langchain: SearchResponse


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


def _extract_pdf_pages(file_content: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(file_content))
    pages: list[tuple[int, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            pages.append((page_number, page_text))
    return pages


def _normalize_hit(hit: dict[str, Any]) -> SearchMatch:
    return SearchMatch(
        id=str(hit.get("_id") or hit.get("id") or ""),
        score=hit.get("_score") if hit.get("_score") is not None else hit.get("score"),
        metadata=hit.get("fields") or hit.get("metadata") or {},
    )


def _build_answer_and_sources(matches: list[SearchMatch]) -> tuple[str, list[str]]:
    answer = "No relevant result found in the indexed documents."
    sources: list[str] = []

    for match in matches:
        metadata = match.metadata or {}
        source = metadata.get("source")
        if source:
            pages = metadata.get("pages")
            source_entry = f"{source} (p. {pages})" if pages else str(source)
            if source_entry not in sources:
                sources.append(source_entry)

        text = metadata.get("text")
        if text and answer.startswith("No relevant result"):
            answer = text

    return answer, sources


def _friendly_ingestion_error(exc: Exception) -> str:
    message = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)

    if (
        status == 429
        or "too many requests" in message
        or "resource_exhausted" in message
        or "max tokens per minute" in message
    ):
        return (
            "The indexing service is currently rate-limited. "
            "Please wait a minute and try uploading again."
        )

    return "We could not index this file right now. Please try again shortly."


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

    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    page_texts = _extract_pdf_pages(file_content)
    if not page_texts:
        raise HTTPException(status_code=400, detail="No extractable text found in PDF")

    upload_id = str(uuid.uuid4())
    records: list[dict[str, Any]] = []

    for page_number, page_text in page_texts:
        page_chunks = _approx_token_chunks(page_text, settings.CHUNK_WORDS, settings.CHUNK_OVERLAP_WORDS)
        for chunk_text in page_chunks:
            records.append(
                {
                    "_id": "",
                    "upload_id": upload_id,
                    "text": chunk_text,
                    "source": file.filename,
                    "pages": str(page_number),
                }
            )

    total_chunks = len(records)
    for index, record in enumerate(records):
        record["_id"] = f"{upload_id}-{index}"
        record["chunk_index"] = index
        record["total_chunks"] = total_chunks

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
        raise HTTPException(status_code=500, detail=_friendly_ingestion_error(exc)) from exc

    return {
        "message": "File indexed successfully",
        "filename": file.filename,
        "chunks_indexed": total_chunks,
        "namespace": pinecone_namespace,
    }


@app.post("/query", response_model=SearchResponse)
async def ask_question(request: QueryRequest):
    try:
        raw_matches = search_records(request.question, request.top_k)
        matches = [_normalize_hit(match) for match in raw_matches]

        answer, sources = query_rag_langchain(request.question, top_k=request.top_k)

        if not answer:
            # Keep the API resilient even when generation path returns empty output.
            answer, fallback_sources = _build_answer_and_sources(matches)
            if not sources:
                sources = fallback_sources

        return {
            "query": request.question,
            "namespace": pinecone_namespace,
            "top_k": request.top_k,
            "answer": answer,
            "sources": sources,
            "engine": request.engine,
            "matches": matches,
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