# RAG Chatbot Backend

A professional RAG (Retrieval Augmented Generation) chatbot backend for querying PDF documents using OpenAI embeddings and GPT models.

## Features

- 📄 **PDF Upload & Indexing**: Upload PDF files and automatically index them with vector embeddings
- 🔍 **Semantic Search**: Query your documents using natural language
- 🤖 **AI-Powered Answers**: Get accurate answers powered by GPT-4o-mini
- 💾 **Persistent Storage**: ChromaDB with persistent storage for your document embeddings
- 🔒 **Input Validation**: Comprehensive request validation and error handling
- 📊 **Health & Stats**: Monitor collection statistics and service health
- 🌐 **CORS Support**: Ready for frontend integration

## Tech Stack

- **FastAPI**: Modern, fast web framework
- **ChromaDB**: Vector database for embeddings
- **OpenAI**: Embeddings (text-embedding-3-small) and Chat (gpt-4o-mini)
- **PyPDF2**: PDF text extraction
- **Pydantic**: Data validation

## Installation

1. **Clone the repository** (if applicable)

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
   Create a `.env` file in the backend directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
CHROMA_PERSIST_DIR=./chroma_db
UPLOAD_DIR=../uploads
```

4. **Run the server**:

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload
```

## API Endpoints

### Health Check

```http
GET /health
```

Returns service status and collection statistics.

### Upload PDF

```http
POST /upload
Content-Type: multipart/form-data

file: <PDF file>
```

Upload and index a PDF file.

**Response**:

```json
{
  "message": "File uploaded and indexed successfully",
  "filename": "document.pdf",
  "chunks_indexed": 42
}
```

### Query Documents

```http
POST /query
Content-Type: application/json

{
  "question": "What is the main topic?",
  "top_k": 4
}
```

Query indexed documents with a question.

**Response**:

```json
{
  "answer": "The main topic is...",
  "sources": ["document.pdf"]
}
```

### Get Statistics

```http
GET /stats
```

Get collection statistics.

### Clear Collection

```http
DELETE /collection
```

Clear all indexed documents.

## Configuration

Edit [config.py](config.py) to customize:

- **Chunk Size**: Default 1000 characters
- **Chunk Overlap**: Default 200 characters
- **Top K Results**: Default 4 context chunks
- **Max File Size**: Default 10MB
- **CORS Origins**: Add your frontend URLs
- **OpenAI Models**: Change embedding or chat models

## Project Structure

```
backend/
├── main.py           # FastAPI application and endpoints
├── rag.py            # RAG implementation (indexing & querying)
├── db.py             # ChromaDB configuration
├── utils.py          # Text extraction and chunking utilities
├── config.py         # Configuration management
├── requirements.txt  # Python dependencies
├── .env              # Environment variables (create this)
└── README.md         # This file
```

## Smart Chunking

The system uses intelligent text chunking that:

- Respects sentence boundaries
- Maintains context with overlapping chunks
- Handles multi-page documents efficiently
- Batch processes embeddings for better performance

## Error Handling

The API includes comprehensive error handling for:

- Invalid file types
- File size limits
- Empty or corrupted PDFs
- OpenAI API errors
- Database errors

## Logging

All operations are logged with timestamps for debugging and monitoring.

## Security Considerations

- API keys are loaded from environment variables
- File upload size limits enforced
- File type validation (PDF only)
- CORS configuration for allowed origins

## Development

To contribute or extend:

1. Add new endpoints in [main.py](main.py)
2. Extend RAG functionality in [rag.py](rag.py)
3. Add utility functions in [utils.py](utils.py)
4. Update configuration in [config.py](config.py)

## License

MIT License

## Support

For issues or questions, please open an issue in the repository.
