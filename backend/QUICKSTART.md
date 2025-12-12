# Quick Start Guide

## Setup (5 minutes)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Test Setup

```bash
python test_setup.py
```

This will verify:

- ✓ All packages installed
- ✓ Environment configured
- ✓ Database initialized
- ✓ OpenAI connection working

### 4. Start Server

```bash
python main.py
```

Or with auto-reload:

```bash
uvicorn main:app --reload
```

Server will be running at: `http://localhost:8000`

## Usage

### Option 1: Interactive API Docs

Open your browser: `http://localhost:8000/docs`

Try the endpoints directly in the browser!

### Option 2: Python Client

```python
import requests

# Upload a PDF
with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/upload", files=files)
    print(response.json())

# Ask a question
payload = {"question": "What is this document about?"}
response = requests.post("http://localhost:8000/query", json=payload)
print(response.json()["answer"])
```

### Option 3: cURL

```bash
# Upload PDF
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf"

# Query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this about?"}'

# Health check
curl http://localhost:8000/health
```

## Next Steps

1. Upload your PDF files via `/upload` endpoint
2. Ask questions via `/query` endpoint
3. Monitor stats via `/stats` endpoint
4. View logs in the console

## Troubleshooting

**Import errors?**

```bash
pip install -r requirements.txt
```

**OpenAI API errors?**

- Check your API key in `.env`
- Verify you have credits in your OpenAI account
- Check internet connection

**Database errors?**

- Delete `chroma_db/` folder and restart
- Check disk space

**Port already in use?**

```bash
uvicorn main:app --port 8001
```

## Features Overview

- ✅ Upload multiple PDFs
- ✅ Smart text chunking with overlap
- ✅ Semantic search with vector embeddings
- ✅ GPT-powered answers with sources
- ✅ Persistent storage (survives restarts)
- ✅ CORS enabled for frontend integration
- ✅ Comprehensive error handling
- ✅ Request validation
- ✅ Health monitoring

## Performance Tips

- **Batch uploads**: Process multiple PDFs at once
- **Adjust chunk size**: Edit `config.py` for larger/smaller chunks
- **Increase top_k**: Get more context for complex questions
- **Cache**: ChromaDB automatically caches queries

## API Endpoints Summary

| Endpoint      | Method | Description            |
| ------------- | ------ | ---------------------- |
| `/health`     | GET    | Service health & stats |
| `/upload`     | POST   | Upload & index PDF     |
| `/query`      | POST   | Ask questions          |
| `/stats`      | GET    | Collection statistics  |
| `/collection` | DELETE | Clear all documents    |

## Configuration

Edit `config.py` to customize:

- Chunk size and overlap
- Number of results (top_k)
- File size limits
- OpenAI models
- CORS origins

Enjoy your RAG Chatbot! 🚀
