"""Pinecone client and index helpers."""
import logging
from typing import Any

from pinecone import Pinecone

from config import settings

logger = logging.getLogger(__name__)

pc = Pinecone(api_key=settings.PINECONE_API_KEY)

if settings.PINECONE_INDEX_HOST:
    pinecone_index = pc.Index(host=settings.PINECONE_INDEX_HOST)
else:
    pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)

pinecone_namespace = settings.PINECONE_NAMESPACE or "default"


def _to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    as_dict = getattr(value, "dict", None)
    if callable(as_dict):
        return as_dict()
    return dict(getattr(value, "__dict__", {}))


def _extract_hits(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        result = payload.get("result", {})
        return result.get("hits", []) if isinstance(result, dict) else []

    result = getattr(payload, "result", None)
    if result is None:
        return []
    if isinstance(result, dict):
        return result.get("hits", [])
    result_model_dump = getattr(result, "model_dump", None)
    if callable(result_model_dump):
        return result_model_dump().get("hits", [])
    result_dict = getattr(result, "dict", None)
    if callable(result_dict):
        return result_dict().get("hits", [])
    return list(getattr(result, "hits", []) or [])


def get_index_stats() -> dict:
    # Return lightweight index stats for health checks.
    stats = _to_dict(pinecone_index.describe_index_stats())
    return {
        "name": settings.PINECONE_INDEX_NAME or settings.PINECONE_INDEX_HOST,
        "namespace": pinecone_namespace,
        "vector_count": stats.get("total_vector_count", 0),
        "dimension": stats.get("dimension", 0),
        "index_fullness": stats.get("index_fullness", 0.0),
    }


def upsert_records(records: list[dict], namespace: str | None = None) -> Any:
    # Upsert raw text records into Pinecone with integrated embeddings.
    target_namespace = namespace or pinecone_namespace
    return pinecone_index.upsert_records(target_namespace, records)


def delete_records_by_upload_id(upload_id: str, namespace: str | None = None) -> None:
    # Delete all records that belong to a specific upload attempt.
    target_namespace = namespace or pinecone_namespace
    try:
        pinecone_index.delete(
            filter={"upload_id": {"$eq": upload_id}},
            namespace=target_namespace,
        )
    except Exception as exc:
        message = str(exc).lower()
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        code = getattr(exc, "code", None)

        if "namespace not found" in message or status == 404 or code == 404:
            logger.info(
                "Pinecone namespace '%s' does not exist yet; skipping pre-clean for upload_id=%s",
                target_namespace,
                upload_id,
            )
            return

        raise


def search_records(query_text: str, top_k: int, namespace: str | None = None) -> list[dict]:
    #Semantic search using Pinecone hosted embeddings.
    target_namespace = namespace or pinecone_namespace
    response = pinecone_index.search(
        namespace=target_namespace,
        query={"inputs": {"text": query_text}, "top_k": top_k},
    )

    hits = _extract_hits(response)

    normalized_hits: list[dict] = []
    for hit in hits:
        hit_dict = _to_dict(hit)
        normalized_hits.append(
            {
                "id": hit_dict.get("_id") if hit_dict.get("_id") is not None else hit_dict.get("id"),
                "score": hit_dict.get("_score") if hit_dict.get("_score") is not None else hit_dict.get("score"),
                "metadata": hit_dict.get("fields") or hit_dict.get("metadata") or {},
            }
        )

    return normalized_hits


def clear_namespace(namespace: str | None = None) -> None:
    # Delete all records from the configured namespace.
    target_namespace = namespace or pinecone_namespace
    pinecone_index.delete(delete_all=True, namespace=target_namespace)