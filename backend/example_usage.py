"""
Example script demonstrating how to use the RAG Chatbot Backend API
"""
import requests
import json

# Base URL of the API
BASE_URL = "http://localhost:8000"


def check_health():
    """Check if the service is healthy"""
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:")
    print(json.dumps(response.json(), indent=2))
    print()


def upload_pdf(file_path):
    """Upload and index a PDF file"""
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    
    print("Upload Response:")
    print(json.dumps(response.json(), indent=2))
    print()
    return response.json()


def query_document(question, top_k=4):
    """Query the indexed documents"""
    payload = {
        "question": question,
        "top_k": top_k
    }
    response = requests.post(
        f"{BASE_URL}/query",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Query: {question}")
    print("Response:")
    result = response.json()
    print(f"Answer: {result['answer']}")
    print(f"Sources: {result['sources']}")
    print()
    return result


def get_stats():
    """Get collection statistics"""
    response = requests.get(f"{BASE_URL}/stats")
    print("Collection Stats:")
    print(json.dumps(response.json(), indent=2))
    print()


def clear_collection():
    """Clear all documents from the collection"""
    response = requests.delete(f"{BASE_URL}/collection")
    print("Clear Collection:")
    print(json.dumps(response.json(), indent=2))
    print()


if __name__ == "__main__":
    # Example usage flow
    print("=" * 60)
    print("RAG Chatbot Backend - Example Usage")
    print("=" * 60)
    print()
    
    # 1. Check health
    try:
        check_health()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the server is running: python main.py")
        exit(1)
    
    # 2. Get initial stats
    get_stats()
    
    # 3. Upload a PDF (replace with your PDF path)
    # upload_pdf("path/to/your/document.pdf")
    
    # 4. Query the documents
    # query_document("What is the main topic of the document?")
    # query_document("Can you summarize the key points?")
    # query_document("What are the conclusions?", top_k=5)
    
    # 5. Get updated stats
    # get_stats()
    
    # 6. Clear collection (optional)
    # clear_collection()
    
    print("\nExample completed!")
    print("\nUncomment the relevant lines to test with your own PDF files.")
