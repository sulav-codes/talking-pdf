"""RAG (Retrieval Augmented Generation) implementation"""
import uuid
import logging
from typing import Tuple, List, Any
from pathlib import Path

from groq import Groq
from sentence_transformers import SentenceTransformer
from pydantic import ConfigDict
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough

from db import collection
from utils import extract_text
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


class ChromaCollectionRetriever(BaseRetriever):
    """LangChain retriever backed by the existing ChromaDB collection."""

    collection: Any
    embedding_model: SentenceTransformer
    default_k: int = settings.TOP_K_RESULTS

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Document]:
        query_embedding = self.embedding_model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=self.default_k
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        relevant_docs: List[Document] = []
        for doc, meta in zip(documents, metadatas):
            pages_str = meta.get("pages", "") if meta else ""
            pages = [int(p) for p in pages_str.split(",") if p.strip()] if pages_str else []

            relevant_docs.append(
                Document(
                    page_content=doc,
                    metadata={
                        "source": meta.get("source", "Unknown") if meta else "Unknown",
                        "pages": pages,
                        "chunk_index": meta.get("chunk_index") if meta else None,
                        "total_chunks": meta.get("total_chunks") if meta else None,
                    },
                )
            )

        return relevant_docs

    async def _aget_relevant_documents(self, query: str, *, run_manager: Any = None) -> List[Document]:
        return self._get_relevant_documents(query, run_manager=run_manager)


def _build_context_from_documents(documents: List[Document]) -> str:
    return "\n\n".join(
        f"[Context {i + 1}]\n{doc.page_content}" for i, doc in enumerate(documents)
    )


def _extract_sources_from_documents(documents: List[Document]) -> List[str]:
    sources: List[str] = []

    for doc in documents:
        source = doc.metadata.get("source", "Unknown")
        pages = doc.metadata.get("pages", [])

        if pages:
            page_str = ", ".join([f"p.{p}" for p in pages])
            source_entry = f"{source} ({page_str})"
        else:
            source_entry = source

        if source_entry not in sources:
            sources.append(source_entry)

    return sources


def _invoke_groq_from_prompt(prompt_value: Any) -> str:
    """Invoke Groq with a LangChain prompt value and return plain text output."""
    role_map = {
        "human": "user",
        "ai": "assistant",
    }

    messages = []
    for message in prompt_value.to_messages():
        role = role_map.get(message.type, message.type)
        messages.append({"role": role, "content": message.content})

    chat_response = groq_client.chat.completions.create(
        model=settings.CHAT_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )

    return chat_response.choices[0].message.content


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
        
        # Extract text from PDF with page numbers
        text, page_map = extract_text(file_path)
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Extracted text is too short or empty")
        
        logger.info(f"Extracted {len(text)} characters from PDF")
        
        # Chunk the text with page tracking
        from utils import chunk_text_with_pages
        chunks_with_pages = chunk_text_with_pages(
            text,
            page_map,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        logger.info(f"Created {len(chunks_with_pages)} chunks")
        
        # Batch process embeddings for efficiency
        batch_size = 32  # Optimized for sentence-transformers
        total_indexed = 0
        
        for i in range(0, len(chunks_with_pages), batch_size):
            batch_items = chunks_with_pages[i:i + batch_size]
            batch_texts = [item[0] for item in batch_items]
            batch_pages = [item[1] for item in batch_items]
            
            # Generate embeddings using HuggingFace model (LOCAL - FAST!)
            embeddings = embedding_model.encode(
                batch_texts,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Prepare data for batch insertion
            ids = [str(uuid.uuid4()) for _ in batch_texts]
            embeddings_list = embeddings.tolist()  # Convert numpy to list for ChromaDB
            metadatas = [
                {
                    "source": Path(file_path).name,
                    "chunk_index": i + j,
                    "total_chunks": len(chunks_with_pages),
                    "pages": ",".join(map(str, batch_pages[j])) if batch_pages[j] else ""  # Store as comma-separated string
                }
                for j in range(len(batch_texts))
            ]
            
            # Add to collection
            collection.add(
                ids=ids,
                embeddings=embeddings_list,
                metadatas=metadatas,
                documents=batch_texts
            )
            
            total_indexed += len(batch_texts)
            logger.info(f"Indexed {total_indexed}/{len(chunks_with_pages)} chunks")
        
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
            pages_str = meta.get("pages", "")
            
            # Parse pages from comma-separated string
            pages = [int(p) for p in pages_str.split(",") if p.strip()] if pages_str else []
            
            # Format source with page numbers
            if pages:
                page_str = ", ".join([f"p.{p}" for p in pages])
                source_entry = f"{source} ({page_str})"
            else:
                source_entry = source
            
            if source_entry not in sources:
                sources.append(source_entry)
        
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


def query_rag_langchain(question: str, top_k: int = None) -> Tuple[str, List[str]]:
    """
    Query the RAG system using a LangChain retriever + chain pipeline.

    Args:
        question: The question to ask
        top_k: Number of context chunks to retrieve

    Returns:
        Tuple of (answer, list of source documents)
    """
    try:
        if top_k is None:
            top_k = settings.TOP_K_RESULTS

        logger.info(f"Processing LangChain query with top_k={top_k}")

        retriever = ChromaCollectionRetriever(
            collection=collection,
            embedding_model=embedding_model,
            default_k=top_k
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a helpful assistant that answers questions based on the provided context. "
                "Use the context to provide accurate and detailed answers. "
                "If the context doesn't contain relevant information, say so clearly. "
                "Always cite which context section(s) you used in your answer."
            ),
            (
                "human",
                "Context from documents:\n\n{context}\n\n"
                "Question: {question}\n\n"
                "Please provide a detailed answer based on the context above."
            ),
        ])

        answer_chain = prompt | RunnableLambda(_invoke_groq_from_prompt)

        retrieval_chain = (
            {
                "question": RunnablePassthrough(),
                "docs": retriever,
            }
            | RunnableLambda(
                lambda payload: {
                    "question": payload["question"],
                    "docs": payload["docs"],
                    "context": _build_context_from_documents(payload["docs"]),
                    "sources": _extract_sources_from_documents(payload["docs"]),
                }
            )
            | RunnablePassthrough.assign(
                answer=RunnableBranch(
                    (
                        lambda payload: len(payload["docs"]) == 0,
                        RunnableLambda(
                            lambda _: "I don't have any documents indexed yet. Please upload a PDF first."
                        ),
                    ),
                    answer_chain,
                )
            )
        )

        result = retrieval_chain.invoke(question)
        answer = result["answer"]
        sources = result["sources"]

        logger.info(f"Generated LangChain answer with {len(sources)} sources")

        return answer, sources

    except Exception as e:
        logger.error(f"LangChain query failed: {e}", exc_info=True)
        raise
