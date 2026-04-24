"""
RAG (Retrieval Augmented Generation) implementation using Pinecone, Groq, and LangChain.
"""
import uuid
import logging
import io
from typing import Tuple, List, Any

from groq import Groq
from sentence_transformers import SentenceTransformer
from pydantic import ConfigDict, Field
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough

# Import from our refactored, cloud-ready modules
from db import pinecone_index
from utils import extract_text, chunk_text_with_pages
from config import settings

logger = logging.getLogger(__name__)

# --- INITIALIZE MODELS AND CLIENTS (Unchanged) ---
groq_client = Groq(api_key=settings.GROQ_API_KEY)

logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
embedding_model = SentenceTransformer(
    settings.EMBEDDING_MODEL,
    trust_remote_code=True,
    token=settings.HF_TOKEN if settings.HF_TOKEN else None
)
logger.info("Embedding model loaded successfully")

class PineconeRetriever(BaseRetriever):
    """LangChain retriever backed by a Pinecone index."""

    index: Any = Field(...)
    embedding_model: SentenceTransformer = Field(...)
    default_k: int = Field(default=settings.TOP_K_RESULTS)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Document]:
        """Synchronous retrieval of documents from Pinecone."""
        query_embedding = self.embedding_model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True
        ).tolist()

        results = self.index.query(
            vector=query_embedding,
            top_k=self.default_k,
            include_metadata=True
        )

        relevant_docs: List[Document] = []
        for match in results.get("matches", []):
            meta = match.get("metadata", {})
            # The document text is now stored in the 'text' field of the metadata
            page_content = meta.get("text", "")

            # Reconstruct the Document object
            pages_str = meta.get("pages", "")
            pages = [int(p) for p in pages_str.split(",") if p.strip()] if pages_str else []

            relevant_docs.append(
                Document(
                    page_content=page_content,
                    metadata={
                        "source": meta.get("source", "Unknown"),
                        "pages": pages,
                        "chunk_index": meta.get("chunk_index"),
                        "total_chunks": meta.get("total_chunks"),
                    },
                )
            )
        return relevant_docs

    async def _aget_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Document]:
        """Asynchronous retrieval (delegates to sync version for simplicity)."""
        return self._get_relevant_documents(query, run_manager=run_manager)


def _build_context_from_documents(documents: List[Document]) -> str:
    return "\n\n".join(
        f"[Context {i + 1}]\n{doc.page_content}" for i, doc in enumerate(documents)
    )

def _extract_sources_from_documents(documents: List[Document]) -> List[str]:
    sources = []
    for doc in documents:
        source = doc.metadata.get("source", "Unknown")
        pages = doc.metadata.get("pages", [])
        page_str = f" (p. {', '.join(map(str, pages))})" if pages else ""
        source_entry = f"{source}{page_str}"
        if source_entry not in sources:
            sources.append(source_entry)
    return sources

def _invoke_groq_from_prompt(prompt_value: Any) -> str:
    role_map = {
        "human": "user",
        "ai": "assistant",
        "system": "system",
    }

    messages = []
    for msg in prompt_value.to_messages():
        role = role_map.get(msg.type, "user")
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        messages.append({"role": role, "content": content})

    chat_response = groq_client.chat.completions.create(
        model=settings.CHAT_MODEL, messages=messages, temperature=0.7, max_tokens=1000
    )
    return chat_response.choices[0].message.content


def index_pdf(file_stream: io.BytesIO, filename: str) -> int:
    """
    Extracts text from an in-memory PDF file, chunks it, and indexes it in Pinecone.
    
    Args:
        file_stream: A file-like object (BytesIO) containing the PDF content.
        filename: The original name of the file, used for 'source' metadata.

    Returns:
        The total number of chunks indexed.
    """
    try:
        logger.info(f"Starting indexing for: {filename}")
        
        # NOTE: Assumes `extract_text` can handle a file-like object.
        text, page_map = extract_text(file_stream)
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Extracted text is too short or empty")
        
        logger.info(f"Extracted {len(text)} characters from {filename}")
        
        chunks_with_pages = chunk_text_with_pages(
            text, page_map, chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        logger.info(f"Created {len(chunks_with_pages)} chunks")
        
        batch_size = 32  # Recommended batch size for Pinecone upserts
        total_indexed = 0
        
        for i in range(0, len(chunks_with_pages), batch_size):
            batch_items = chunks_with_pages[i:i + batch_size]
            batch_texts = [item[0] for item in batch_items]
            
            embeddings = embedding_model.encode(
                batch_texts, show_progress_bar=False, convert_to_numpy=True
            ).tolist()
            
            # Prepare vectors in the format Pinecone expects: (id, values, metadata)
            vectors_to_upsert = []
            for j, text_chunk in enumerate(batch_texts):
                chunk_pages = batch_items[j][1]
                vector_id = str(uuid.uuid4())
                metadata = {
                    "text": text_chunk,  # IMPORTANT: Store the text in the metadata
                    "source": filename,
                    "chunk_index": i + j,
                    "total_chunks": len(chunks_with_pages),
                    "pages": ",".join(map(str, chunk_pages)) if chunk_pages else ""
                }
                vectors_to_upsert.append((vector_id, embeddings[j], metadata))
            
            # Upsert batch to Pinecone
            pinecone_index.upsert(vectors=vectors_to_upsert)
            
            total_indexed += len(batch_texts)
            logger.info(f"Indexed {total_indexed}/{len(chunks_with_pages)} chunks")
        
        logger.info(f"Successfully indexed {total_indexed} chunks from {filename}")
        return total_indexed
        
    except Exception as e:
        logger.error(f"Indexing failed for {filename}: {e}", exc_info=True)
        raise


# This function is now redundant if you use the LangChain version, but kept for completeness.
def query_rag(question: str, top_k: int = None) -> Tuple[str, List[str]]:
    """Simple RAG query using direct Pinecone and Groq calls."""
    return query_rag_langchain(question, top_k)


def query_rag_langchain(question: str, top_k: int = None) -> Tuple[str, List[str]]:
    """
    Queries the RAG system using the Pinecone retriever and a LangChain pipeline.
    """
    try:
        k = top_k if top_k is not None else settings.TOP_K_RESULTS
        logger.info(f"Processing LangChain query with top_k={k}")

        # Use our new PineconeRetriever
        retriever = PineconeRetriever(
            index=pinecone_index,
            embedding_model=embedding_model,
            default_k=k
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant..."), # Your prompt here
            ("human", "Context:\n\n{context}\n\nQuestion: {question}\n\nAnswer:"),
        ])

        # This chain combines retrieval, context formatting, and the final answer generation
        retrieval_chain = (
            { "question": RunnablePassthrough(), "docs": retriever }
            | RunnableLambda(
                lambda payload: {
                    "question": payload["question"],
                    "context": _build_context_from_documents(payload["docs"]),
                    "sources": _extract_sources_from_documents(payload["docs"]),
                    "docs": payload["docs"], # Pass docs through for the branch
                }
            )
            | RunnablePassthrough.assign(
                answer=RunnableBranch(
                    (lambda payload: len(payload["docs"]) == 0, lambda _: "I don't have any documents to answer that question. Please upload a PDF first."),
                    prompt | RunnableLambda(_invoke_groq_from_prompt),
                )
            )
        )

        result = retrieval_chain.invoke(question)
        
        logger.info(f"Generated LangChain answer with {len(result['sources'])} sources")
        return result["answer"], result["sources"]

    except Exception as e:
        logger.error(f"LangChain query failed: {e}", exc_info=True)
        raise