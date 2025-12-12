/**
 * API service for communicating with the RAG backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIService {
  /**
   * Upload a PDF file
   */
  static async uploadPDF(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  }

  /**
   * Query the RAG system
   */
  static async query(question, topK = 4) {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question, top_k: topK }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Query failed");
    }

    return response.json();
  }

  /**
   * Get health status
   */
  static async getHealth() {
    const response = await fetch(`${API_BASE_URL}/health`);

    if (!response.ok) {
      throw new Error("Health check failed");
    }

    return response.json();
  }

  /**
   * Get collection statistics
   */
  static async getStats() {
    const response = await fetch(`${API_BASE_URL}/stats`);

    if (!response.ok) {
      throw new Error("Failed to fetch stats");
    }

    return response.json();
  }

  /**
   * Clear all documents
   */
  static async clearCollection() {
    const response = await fetch(`${API_BASE_URL}/collection`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to clear collection");
    }

    return response.json();
  }
}

export default APIService;
