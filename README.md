# 📄 Talking PDF

A modern, full-stack RAG (Retrieval Augmented Generation) application that lets you chat with your PDF documents using AI. Upload PDFs, ask questions, and get accurate answers powered by OpenAI's GPT models.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Next.js](https://img.shields.io/badge/next.js-16.0-black.svg)

## ✨ Features

- 📤 **PDF Upload & Processing**: Upload PDF files and automatically extract and index content
- 🤖 **AI-Powered Chat**: Ask questions in natural language and get accurate, context-aware answers
- 🔍 **Semantic Search**: Advanced vector-based search using OpenAI embeddings
- 💾 **Persistent Storage**: Documents are indexed once and stored persistently using ChromaDB
- 🎨 **Modern UI**: Clean, responsive interface with dark mode support
- ⚡ **Fast & Free**: Optimized for speed with cost-effective AI models
- 🔒 **Privacy-First**: Process documents locally with secure API integration
- 📊 **Real-time Stats**: Monitor collection statistics and system health

## 🏗️ Tech Stack

### Backend

- **FastAPI**: High-performance async web framework
- **ChromaDB**: Vector database for embeddings storage
- **OpenAI API**: GPT-4o-mini for chat, text-embedding-3-small for embeddings
- **PyPDF2**: PDF text extraction
- **Pydantic**: Request/response validation

### Frontend

- **Next.js 16**: React framework with App Router
- **React 19**: Modern React with hooks
- **Tailwind CSS 4**: Utility-first styling
- **Lucide Icons**: Beautiful, consistent icons

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd talking-pdf
   ```

2. **Set up the Backend**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**

   Create a `.env` file in the `backend` directory:

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   CHROMA_PERSIST_DIR=./chroma_db
   UPLOAD_DIR=./uploads
   ```

4. **Set up the Frontend**
   ```bash
   cd ../frontend
   npm install
   ```

### Running the Application

1. **Start the Backend** (from the `backend` directory)

   ```bash
   python main.py
   ```

   Backend will run on `http://localhost:8000`

2. **Start the Frontend** (from the `frontend` directory)

   ```bash
   npm run dev
   ```

   Frontend will run on `http://localhost:3000`

3. **Open your browser** and navigate to `http://localhost:3000`

## 📖 Usage

1. **Upload a PDF**

   - Click on the "Upload PDF" tab
   - Select a PDF file from your computer
   - Wait for the file to be processed and indexed

2. **Start Chatting**

   - Switch to the "Chat" tab
   - Type your question about the document
   - Get AI-powered answers with source references

3. **Monitor Stats**
   - View document statistics in the sidebar
   - Check the number of indexed documents and chunks
   - Monitor system health

## 🔌 API Endpoints

### Backend API

- `GET /health` - Health check and collection statistics
- `POST /upload` - Upload and index a PDF file
- `POST /query` - Query documents with a question
- `DELETE /clear` - Clear all indexed documents

For detailed API documentation, visit `http://localhost:8000/docs` when the backend is running.

## 📁 Project Structure

```
talking-pdf/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── rag.py               # RAG logic (indexing & querying)
│   ├── db.py                # ChromaDB operations
│   ├── config.py            # Configuration settings
│   ├── utils.py             # Utility functions
│   ├── requirements.txt     # Python dependencies
│   ├── chroma_db/           # ChromaDB persistent storage
│   └── uploads/             # Uploaded PDF files
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.js      # Main page component
    │   │   ├── layout.js    # Root layout
    │   │   └── globals.css  # Global styles
    │   ├── components/
    │   │   ├── ChatInterface.jsx    # Chat UI
    │   │   ├── FileUpload.jsx       # File upload UI
    │   │   ├── StatsPanel.jsx       # Statistics display
    │   │   ├── FeatureCards.jsx     # Feature highlights
    │   │   └── ThemeToggle.jsx      # Dark mode toggle
    │   └── lib/
    │       └── api.js       # API client functions
    ├── package.json         # Node dependencies
    └── next.config.mjs      # Next.js configuration
```

## 🔧 Configuration

### Backend Configuration (`backend/config.py`)

Key settings:

- `OPENAI_API_KEY`: Your OpenAI API key
- `CHROMA_PERSIST_DIR`: ChromaDB storage directory
- `CHUNK_SIZE`: Text chunk size for embeddings (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200)
- `DEFAULT_TOP_K`: Number of context chunks to retrieve (default: 4)

### Frontend Configuration

The frontend automatically connects to the backend at `http://localhost:8000`. Modify [`api.js`](frontend/src/lib/api.js) to change the API base URL.

## 🧪 Testing

### Backend Tests

```bash
cd backend
python test_setup.py
```

### Example Usage

```bash
cd backend
python example_usage.py
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for powerful AI models
- [ChromaDB](https://www.trychroma.com/) for vector database
- [FastAPI](https://fastapi.tiangolo.com/) for backend framework
- [Next.js](https://nextjs.org/) for frontend framework

## 📧 Support

For support, please open an issue in the repository or contact the maintainers.

---

Made with ❤️ using AI and modern web technologies
