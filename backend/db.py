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


def _extract_value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _extract_metadata(item: Any) -> dict[str, Any]:
    metadata = _extract_value(item, "metadata")
    if metadata is None:
        metadata = _extract_value(item, "fields")

    if isinstance(metadata, dict):
        return metadata

    if metadata is None:
        return {}

    return _to_dict(metadata)


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_index_stats() -> dict:
    # Return lightweight index stats for health checks.
    stats = _to_dict(pinecone_index.describe_index_stats())
    namespaces = stats.get("namespaces", {}) if isinstance(stats, dict) else {}

    def _get_vector_count(value: Any) -> int:
        if isinstance(value, dict):
            return value.get("vector_count", value.get("vectorCount", 0)) or 0
        return 0

    namespace_vector_count = 0
    if isinstance(namespaces, dict) and namespaces:
        if pinecone_namespace in namespaces:
            namespace_vector_count = _get_vector_count(namespaces[pinecone_namespace])
        elif "" in namespaces:
            namespace_vector_count = _get_vector_count(namespaces[""])
        elif len(namespaces) == 1:
            namespace_vector_count = _get_vector_count(next(iter(namespaces.values())))

    total_vector_count = stats.get("total_vector_count", stats.get("totalVectorCount", 0))

    return {
        "name": settings.PINECONE_INDEX_NAME or settings.PINECONE_INDEX_HOST,
        "namespace": pinecone_namespace,
        "vector_count": namespace_vector_count or total_vector_count,
        "total_vector_count": total_vector_count,
        "dimension": stats.get("dimension", 0),
        "index_fullness": stats.get("index_fullness", 0.0),
    }


def get_upload_chunk_total(upload_ids: list[str], namespace: str | None = None) -> int:
    if not upload_ids:
        return 0

    target_namespace = namespace or pinecone_namespace
    record_ids = [f"{upload_id}-0" for upload_id in upload_ids if upload_id]
    if not record_ids:
        return 0

    response = pinecone_index.fetch(ids=record_ids, namespace=target_namespace)
    payload = _to_dict(response)
    records = payload.get("records") or payload.get("vectors") or {}

    total = 0
    if isinstance(records, dict):
        for record in records.values():
            metadata = _extract_metadata(record)
            total += _coerce_int(
                metadata.get("total_chunks") or metadata.get("totalChunks")
            )

    return total


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

        if "namespace not found" in message or status == 404:
            logger.info(
                "Pinecone namespace '%s' does not exist yet; skipping pre-clean for upload_id=%s",
                target_namespace,
                upload_id,
            )
            return

        raise


def search_records(
    query_text: str,
    top_k: int,
    namespace: str | None = None,
    filters: dict[str, Any] | None = None,
) -> list[dict]:
    # Semantic search using Pinecone hosted embeddings.
    target_namespace = namespace or pinecone_namespace
    query_payload = {"inputs": {"text": query_text}, "top_k": top_k}
    if filters:
        query_payload["filter"] = filters

    response = pinecone_index.search(
        namespace=target_namespace,
        query=query_payload,
    )

    hits = _extract_hits(response)

    normalized_hits: list[dict] = []
    for hit in hits:
        hit_id = _extract_value(hit, "_id") or _extract_value(hit, "id") or ""
        hit_score = _extract_value(hit, "_score")
        if hit_score is None:
            hit_score = _extract_value(hit, "score")
        normalized_hits.append(
            {
                "id": str(hit_id),
                "score": hit_score,
                "metadata": _extract_metadata(hit),
            }
        )

    return normalized_hits


def clear_namespace(namespace: str | None = None) -> None:
    # Delete all records from the configured namespace.
    target_namespace = namespace or pinecone_namespace
    pinecone_index.delete(delete_all=True, namespace=target_namespace)