"use client";

import { useState } from "react";
import { Send, Loader2, FileText } from "lucide-react";
import APIService from "@/lib/api";

export default function ChatInterface({ disabled }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [engine, setEngine] = useState("direct");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userMessage = {
      role: "user",
      content: question,
      mode: "single",
      selectedEngine: engine,
    };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const data = await APIService.query(question, 4, engine);
      const assistantMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        engine: data.engine,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: "error",
        content: error.message || "Failed to get response. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!question.trim() || loading) return;

    const userMessage = {
      role: "user",
      content: question,
      mode: "compare",
    };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const data = await APIService.compareQuery(question, 4);

      const directMessage = {
        role: "assistant",
        content: data.direct.answer,
        sources: data.direct.sources,
        engine: "direct",
      };

      const langchainMessage = {
        role: "assistant",
        content: data.langchain.answer,
        sources: data.langchain.sources,
        engine: "langchain",
      };

      setMessages((prev) => [...prev, directMessage, langchainMessage]);
    } catch (error) {
      const errorMessage = {
        role: "error",
        content:
          error.message || "Failed to compare responses. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              No messages yet
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 max-w-sm">
              Upload a PDF and start asking questions about your documents
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : message.role === "error"
                      ? "bg-red-50 dark:bg-red-950/20 text-red-900 dark:text-red-200 border border-red-200 dark:border-red-900"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                }`}
              >
                {message.role === "assistant" && message.engine && (
                  <div className="mb-2">
                    <span className="text-[10px] uppercase tracking-wide font-semibold bg-white/70 dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1 rounded">
                      {message.engine}
                    </span>
                  </div>
                )}
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
                    <p className="text-xs font-semibold mb-2 text-gray-700 dark:text-gray-300 flex items-center space-x-1">
                      <FileText className="w-3 h-3" />
                      <span>Sources:</span>
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {message.sources.map((source, idx) => {
                        // Parse source to separate filename and pages
                        const match = source.match(/^(.+?)\s*\((.+?)\)$/);
                        const filename = match ? match[1] : source;
                        const pages = match ? match[2] : null;

                        return (
                          <div
                            key={idx}
                            className="text-xs bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 flex items-center space-x-1.5"
                          >
                            <FileText className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                            <span className="font-medium">{filename}</span>
                            {pages && (
                              <span className="text-blue-600 dark:text-blue-400 font-semibold">
                                {pages}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 flex items-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin text-gray-600 dark:text-gray-400" />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Thinking...
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
            Engine
          </label>
          <select
            value={engine}
            onChange={(e) => setEngine(e.target.value)}
            disabled={disabled || loading}
            className="text-sm px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-900"
          >
            <option value="direct">Direct</option>
            <option value="langchain">LangChain</option>
          </select>
          <button
            type="button"
            onClick={handleCompare}
            disabled={disabled || loading || !question.trim()}
            className="text-sm px-4 py-2 rounded-lg border border-blue-300 text-blue-700 dark:text-blue-300 dark:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Compare Both
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              disabled
                ? "Upload a PDF first..."
                : "Ask a question about your documents..."
            }
            disabled={disabled || loading}
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={disabled || loading || !question.trim()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors flex items-center space-x-2 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Send className="w-5 h-5" />
                <span>Send</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
