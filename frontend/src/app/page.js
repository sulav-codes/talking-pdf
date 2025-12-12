"use client";

import { useState } from "react";
import { FileText, MessageSquare } from "lucide-react";
import FileUpload from "@/components/FileUpload";
import ChatInterface from "@/components/ChatInterface";
import StatsPanel from "@/components/StatsPanel";
import ThemeToggle from "@/components/ThemeToggle";
import FeatureCards from "@/components/FeatureCards";

export default function Home() {
  const [hasDocuments, setHasDocuments] = useState(false);
  const [activeTab, setActiveTab] = useState("upload");

  const handleUploadSuccess = (data) => {
    if (data.chunks_indexed > 0) {
      setHasDocuments(true);
      setActiveTab("chat");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Talking PDF
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Free • Fast • Private RAG Chatbot
                </p>
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Feature Cards */}
        <div className="mb-8">
          <FeatureCards />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Tab Navigation */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="flex border-b border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setActiveTab("upload")}
                  className={`flex-1 px-6 py-4 text-sm font-medium transition-colors flex items-center justify-center space-x-2 ${
                    activeTab === "upload"
                      ? "bg-blue-50 dark:bg-blue-950/20 text-blue-700 dark:text-blue-400 border-b-2 border-blue-600"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  <span>Upload PDF</span>
                </button>
                <button
                  onClick={() => setActiveTab("chat")}
                  className={`flex-1 px-6 py-4 text-sm font-medium transition-colors flex items-center justify-center space-x-2 ${
                    activeTab === "chat"
                      ? "bg-blue-50 dark:bg-blue-950/20 text-blue-700 dark:text-blue-400 border-b-2 border-blue-600"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                  }`}
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Chat</span>
                </button>
              </div>

              {/* Tab Content */}
              <div className="p-6">
                {activeTab === "upload" ? (
                  <div>
                    <div className="mb-6">
                      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                        Upload Your Documents
                      </h2>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Upload PDF files to start asking questions. Your
                        documents are processed locally with free embeddings and
                        lightning-fast LLM responses.
                      </p>
                    </div>
                    <FileUpload onUploadSuccess={handleUploadSuccess} />
                  </div>
                ) : (
                  <div className="h-[600px]">
                    <ChatInterface disabled={!hasDocuments} />
                  </div>
                )}
              </div>
            </div>

            {/* Info Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center space-x-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>Powered By</span>
                </h3>
                <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li>
                    • <strong>Nomic Embed</strong> - Local embeddings (FREE)
                  </li>
                  <li>
                    • <strong>Groq Llama 3.1</strong> - Ultra-fast LLM (FREE)
                  </li>
                  <li>
                    • <strong>ChromaDB</strong> - Vector database
                  </li>
                </ul>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  How It Works
                </h3>
                <ol className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li>1. Upload your PDF documents</li>
                  <li>2. Documents are chunked & embedded locally</li>
                  <li>3. Ask questions in natural language</li>
                  <li>4. Get instant AI-powered answers</li>
                </ol>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <StatsPanel />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-12 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-600 dark:text-gray-400">
            Built with Next.js • FastAPI • HuggingFace • Groq
          </p>
        </div>
      </footer>
    </div>
  );
}
