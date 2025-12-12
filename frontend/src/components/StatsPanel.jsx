"use client";

import { Database, FileText, Trash2, Loader2, AlertCircle } from "lucide-react";
import { useState, useEffect } from "react";
import APIService from "@/lib/api";

export default function StatsPanel() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    try {
      setError(null);
      const data = await APIService.getStats();
      setStats(data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
      setError(error.message || "Failed to fetch stats");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    if (
      !confirm(
        "Are you sure you want to clear all documents? This action cannot be undone."
      )
    ) {
      return;
    }

    setClearing(true);
    try {
      setError(null);
      await APIService.clearCollection();
      await fetchStats();
    } catch (error) {
      console.error("Failed to clear collection:", error);
      setError(error.message || "Failed to clear collection");
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-center p-6">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start space-x-3 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-900 dark:text-red-200">
              Connection Error
            </p>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">
              {error}
            </p>
            <button
              onClick={fetchStats}
              className="mt-2 px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded-md"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center space-x-2">
          <Database className="w-5 h-5" />
          <span>Collection Stats</span>
        </h2>
        <button
          onClick={handleClear}
          disabled={clearing || stats?.document_count === 0}
          className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white rounded-md font-medium transition-colors flex items-center space-x-1.5 disabled:cursor-not-allowed"
        >
          {clearing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Clearing...</span>
            </>
          ) : (
            <>
              <Trash2 className="w-4 h-4" />
              <span>Clear All</span>
            </>
          )}
        </button>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-900">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/40 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Total Chunks
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats?.document_count || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
            Collection Name
          </p>
          <p className="text-sm font-mono text-gray-900 dark:text-gray-100">
            {stats?.name}
          </p>
        </div>

        {stats?.persist_directory && (
          <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
              Storage Location
            </p>
            <p className="text-sm font-mono text-gray-900 dark:text-gray-100 break-all">
              {stats.persist_directory}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
