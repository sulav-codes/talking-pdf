"""
Test script to verify all components work correctly
Run this after setting up your environment
"""
import sys
from pathlib import Path


def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    try:
        import fastapi
        import uvicorn
        import chromadb
        import groq
        from sentence_transformers import SentenceTransformer
        from PyPDF2 import PdfReader
        from dotenv import load_dotenv
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("Run: pip install sentence-transformers groq")
        return False


def test_env_variables():
    """Test environment variables"""
    print("\nTesting environment variables...")
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            print("✗ GROQ_API_KEY not set in .env file")
            print("  Update your .env file with a valid Groq API key")
            return False
        
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            print("⚠ HF_TOKEN not set (optional but recommended)")
        
        print("✓ Environment variables configured")
        return True
    except Exception as e:
        print(f"✗ Environment check failed: {e}")
        return False


def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    try:
        from config import settings
        print(f"  - API Title: {settings.API_TITLE}")
        print(f"  - Embedding Model: {settings.EMBEDDING_MODEL}")
        print(f"  - Chat Model: {settings.CHAT_MODEL}")
        print(f"  - Collection Name: {settings.COLLECTION_NAME}")
        print(f"  - Upload Dir: {settings.UPLOAD_DIR}")
        print("✓ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False


def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    try:
        from db import collection, get_collection_stats
        stats = get_collection_stats()
        print(f"  - Collection: {stats['name']}")
        print(f"  - Document count: {stats['document_count']}")
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False


def test_utilities():
    """Test utility functions"""
    print("\nTesting utilities...")
    try:
        from utils import chunk_text, clean_text
        
        # Test chunking
        sample_text = "This is a test. " * 100
        chunks = chunk_text(sample_text, chunk_size=200, chunk_overlap=50)
        print(f"  - Created {len(chunks)} chunks from sample text")
        
        # Test cleaning
        dirty_text = "  Multiple   spaces\n\n\n\nand   newlines  "
        clean = clean_text(dirty_text)
        print(f"  - Text cleaning works")
        
        print("✓ Utilities working correctly")
        return True
    except Exception as e:
        print(f"✗ Utilities test failed: {e}")
        return False


def test_groq_connection():
    """Test Groq API connection"""
    print("\nTesting Groq connection...")
    try:
        from groq import Groq
        from config import settings
        
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Try a simple chat completion
        response = client.chat.completions.create(
            model=settings.CHAT_MODEL,
            messages=[{"role": "user", "content": "Say 'test successful' in exactly 2 words."}],
            max_tokens=10
        )
        
        print(f"  - Model response: {response.choices[0].message.content}")
        print("✓ Groq connection successful (INSANELY FAST!)")
        return True
    except Exception as e:
        print(f"✗ Groq connection failed: {e}")
        print("  Check your API key and internet connection")
        return False


def test_embedding_model():
    """Test HuggingFace embedding model"""
    print("\nTesting HuggingFace embedding model...")
    try:
        from sentence_transformers import SentenceTransformer
        from config import settings
        
        print(f"  - Loading model: {settings.EMBEDDING_MODEL}")
        model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            trust_remote_code=True,
            token=settings.HF_TOKEN if settings.HF_TOKEN else None
        )
        
        # Test encoding
        embedding = model.encode("test", show_progress_bar=False)
        
        print(f"  - Embedding dimension: {len(embedding)}")
        print("✓ HuggingFace embedding model loaded (LOCAL & FREE!)")
        return True
    except Exception as e:
        print(f"✗ Embedding model failed: {e}")
        print("  Model will be downloaded on first use")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("RAG Chatbot Backend - System Test")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_env_variables,
        test_config,
        test_database,
        test_utilities,
        test_embedding_model,
        test_groq_connection,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Unexpected error in {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("\n✓ All tests passed! System is ready.")
        print("\nYou can now start the server with:")
        print("  python main.py")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
