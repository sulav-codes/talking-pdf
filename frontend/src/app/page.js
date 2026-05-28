"use client";

import { useEffect, useState } from "react";
import { FileText, MessageSquare } from "lucide-react";
import FileUpload from "@/components/FileUpload";
import ChatInterface from "@/components/ChatInterface";
import StatsPanel from "@/components/StatsPanel";
import ThemeToggle from "@/components/ThemeToggle";
import FeatureCards from "@/components/FeatureCards";
import Image from "next/image";

export default function Home() {
  const activeDocumentKey = "talking-pdf-active-document";
  const activeTabKey = "talking-pdf-active-tab";
  const uploadIdsKey = "talking-pdf-upload-ids";
  const [activeDocument, setActiveDocument] = useState(() => {
    if (typeof window === "undefined") {
      return null;
    }

    const storedDocument = window.localStorage.getItem(activeDocumentKey);
    if (!storedDocument) {
      return null;
    }

    try {
      const parsed = JSON.parse(storedDocument);
      if (parsed?.filename && parsed?.uploadId) {
        return parsed;
      }
    } catch (error) {
      console.warn("Failed to restore active document", error);
    }

    return null;
  });
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window === "undefined") {
      return "upload";
    }

    const storedTab = window.localStorage.getItem(activeTabKey);
    return storedTab === "upload" || storedTab === "chat"
      ? storedTab
      : "upload";
  });

  useEffect(() => {
    if (activeDocument) {
      window.localStorage.setItem(
        activeDocumentKey,
        JSON.stringify(activeDocument),
      );
    } else {
      window.localStorage.removeItem(activeDocumentKey);
    }
  }, [activeDocument]);

  useEffect(() => {
    if (!activeDocument?.uploadId) {
      return;
    }

    try {
      const storedIds = window.localStorage.getItem(uploadIdsKey);
      const parsedIds = storedIds ? JSON.parse(storedIds) : [];
      const uploadIds = Array.isArray(parsedIds) ? parsedIds : [];
      if (!uploadIds.includes(activeDocument.uploadId)) {
        uploadIds.push(activeDocument.uploadId);
        window.localStorage.setItem(uploadIdsKey, JSON.stringify(uploadIds));
      }
    } catch (error) {
      console.warn("Failed to reconcile upload ids", error);
    }
  }, [activeDocument]);

  useEffect(() => {
    window.localStorage.setItem(activeTabKey, activeTab);
  }, [activeTab]);

  const handleUploadSuccess = (data) => {
    if (data.chunks_indexed > 0) {
      setActiveDocument({
        filename: data.filename,
        uploadId: data.upload_id,
      });
      setActiveTab("chat");

      try {
        const storedIds = window.localStorage.getItem(uploadIdsKey);
        const parsedIds = storedIds ? JSON.parse(storedIds) : [];
        const uploadIds = Array.isArray(parsedIds) ? parsedIds : [];
        if (!uploadIds.includes(data.upload_id)) {
          uploadIds.push(data.upload_id);
          window.localStorage.setItem(uploadIdsKey, JSON.stringify(uploadIds));
        }
      } catch (error) {
        console.warn("Failed to persist upload id", error);
      }
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Image
                src="/logo.svg"
                alt="Talking PDF Logo"
                width={48}
                height={48}
              />
              <div>
                <h1 className="text-2xl font-bold text-[#16385A] dark:text-[#80C5E4]">
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
                <div className={activeTab === "upload" ? "block" : "hidden"}>
                  <div className="mb-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                      Upload Your Documents
                    </h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Upload PDF files to start asking questions. Your documents
                      are processed locally with free embeddings and
                      lightning-fast LLM responses.
                    </p>
                  </div>
                  <FileUpload
                    onUploadSuccess={handleUploadSuccess}
                    lastUploaded={activeDocument}
                  />
                </div>
                <div className={activeTab === "chat" ? "block" : "hidden"}>
                  <div className="h-150">
                    <ChatInterface
                      disabled={!activeDocument}
                      documentName={activeDocument?.filename}
                      uploadId={activeDocument?.uploadId}
                    />
                  </div>
                </div>
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
                    • <strong>Pinecone</strong> - Vector database + Auto
                    Embeddings (FREE)
                  </li>
                  <li>
                    • <strong>Groq Llama 3.1</strong> - Ultra-fast LLM (FREE)
                  </li>
                </ul>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  How It Works
                </h3>
                <ol className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li>1. Upload your PDF documents</li>
                  <li>2. Documents are chunked & embedded by Pinecone</li>
                  <li>3. Ask questions in natural language</li>
                  <li>4. Get instant AI-powered answers</li>
                </ol>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <StatsPanel
              activeDocument={activeDocument}
              onClearActiveDocument={() => setActiveDocument(null)}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-12 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-600 dark:text-gray-400">
            Built with
            <br />
            Next.js • FastAPI • Pinecone • Groq LLM • HuggingFace • Supabase
            Bucket • Deployed on Vercel & Render.
            <br />
            <br />© {new Date().getFullYear()} Talking PDF. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
