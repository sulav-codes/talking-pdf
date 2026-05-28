"use client";

import { useEffect, useState } from "react";
import { Send, Loader2, FileText } from "lucide-react";
import APIService from "@/lib/api";

function renderTextWithBold(text, keyPrefix) {
  const segments = text.split(/(\*\*[^*]+\*\*)/g);

  return segments.map((segment, index) => {
    const isBold = segment.startsWith("**") && segment.endsWith("**");
    if (!isBold) {
      return <span key={`${keyPrefix}-text-${index}`}>{segment}</span>;
    }

    return (
      <strong key={`${keyPrefix}-bold-${index}`} className="font-semibold">
        {segment.slice(2, -2)}
      </strong>
    );
  });
}

function renderAssistantContent(content) {
  const tokens = String(content || "")
    .split(/(\[Context\s+\d+\])/g)
    .filter(Boolean);
  const nodes = [];

  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    const contextMatch = token.match(/^\[Context\s+(\d+)\]$/);

    if (contextMatch) {
      const contextNumber = contextMatch[1];
      const nextToken = tokens[i + 1] || "";
      const isNextAlsoContext = /^\[Context\s+\d+\]$/.test(nextToken);
      const contextText = isNextAlsoContext ? "" : nextToken.trim();

      nodes.push(
        <div
          key={`context-${contextNumber}-${i}`}
          className="mt-3 rounded-md border border-gray-300 dark:border-gray-600 bg-white/60 dark:bg-gray-900/30 p-3"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300 mb-1">
            Context {contextNumber}
          </p>
          <p className="text-sm whitespace-pre-wrap">
            {renderTextWithBold(contextText, `context-${contextNumber}-${i}`)}
          </p>
        </div>,
      );

      if (!isNextAlsoContext) {
        i += 1;
      }
      continue;
    }

    if (token.trim()) {
      nodes.push(
        <p key={`plain-${i}`} className="text-sm whitespace-pre-wrap">
          {renderTextWithBold(token, `plain-${i}`)}
        </p>,
      );
    }
  }

  if (nodes.length === 0) {
    return <p className="text-sm">No answer returned from the backend.</p>;
  }

  return <div className="space-y-2">{nodes}</div>;
}

export default function ChatInterface({ disabled, documentName, uploadId }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const isReady = Boolean(uploadId) && !disabled;
  const storageKey = uploadId ? `talking-pdf-chat:${uploadId}` : null;

  useEffect(() => {
    if (!storageKey) {
      setMessages([]);
      setQuestion("");
      return;
    }

    const storedMessages = window.localStorage.getItem(storageKey);
    if (storedMessages) {
      try {
        const parsed = JSON.parse(storedMessages);
        setMessages(Array.isArray(parsed) ? parsed : []);
      } catch (error) {
        console.warn("Failed to restore chat history", error);
        setMessages([]);
      }
    } else {
      setMessages([]);
    }

    setQuestion("");
  }, [storageKey, uploadId]);

  useEffect(() => {
    if (!storageKey) {
      return;
    }

    window.localStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages, storageKey]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userMessage = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const data = await APIService.query(question, 4, "direct", uploadId);
      const assistantMessage = {
        role: "assistant",
        content: data.answer || "No answer returned from the backend.",
        sources: Array.isArray(data.sources) ? data.sources : [],
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
              {documentName
                ? `Ask questions about ${documentName}`
                : "Upload a PDF and start asking questions about your documents"}
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
                {message.role === "assistant" ? (
                  renderAssistantContent(message.content)
                ) : (
                  <p className="text-sm whitespace-pre-wrap">
                    {message.content}
                  </p>
                )}
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
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              !isReady
                ? "Upload a PDF first..."
                : "Ask a question about your documents..."
            }
            disabled={!isReady || loading}
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!isReady || loading || !question.trim()}
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
