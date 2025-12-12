/**
 * API service for communicating with the RAG backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.details = details;
  }
}

class APIService {
  /**
   * Handle fetch errors with proper error messages
   */
  static async handleResponse(response) {
    if (!response.ok) {
      let errorMessage = "Request failed";
      let errorDetails = null;

      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
        errorDetails = error;
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    return response.json();
  }

  /**
   * Handle network errors
   */
  static handleNetworkError(error) {
    if (error instanceof APIError) {
      throw error;
    }

    if (error.name === "TypeError" && error.message.includes("fetch")) {
      throw new APIError(
        "Cannot connect to server. Please ensure the backend is running on " +
          API_BASE_URL,
        0,
        { originalError: error.message }
      );
    }

    throw new APIError(error.message || "An unexpected error occurred", 0, {
      originalError: error.message,
    });
  }

  /**
   * Upload a PDF file
   */
  static async uploadPDF(file) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      return await this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  /**
   * Query the RAG system
   */
  static async query(question, topK = 4) {
    try {
      const response = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, top_k: topK }),
      });

      return await this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  /**
   * Get health status
   */
  static async getHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  /**
   * Get collection statistics
   */
  static async getStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/stats`);
      return await this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }

  /**
   * Clear all documents
   */
  static async clearCollection() {
    try {
      const response = await fetch(`${API_BASE_URL}/collection`, {
        method: "DELETE",
      });

      return await this.handleResponse(response);
    } catch (error) {
      this.handleNetworkError(error);
    }
  }
}

export default APIService;
export { APIError };
