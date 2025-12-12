"use client";

import { useState, useRef } from "react";
import {
  Upload,
  File,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import APIService from "@/lib/api";

export default function FileUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState(""); // "uploading", "processing", "indexing"
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === "application/pdf") {
      setFile(droppedFile);
      setUploadStatus(null);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUploadStatus(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setUploadStatus(null);
    setUploadProgress(0);
    setUploadStage("uploading");

    try {
      // Create XMLHttpRequest for upload progress tracking
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append("file", file);

      // Track upload progress
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          setUploadProgress(Math.round(percentComplete));
        }
      });

      // Handle state changes
      xhr.addEventListener("readystatechange", () => {
        if (xhr.readyState === XMLHttpRequest.HEADERS_RECEIVED) {
          setUploadStage("processing");
          setUploadProgress(100);
        }
      });

      const uploadPromise = new Promise((resolve, reject) => {
        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const data = JSON.parse(xhr.responseText);
              resolve(data);
            } catch (e) {
              reject(new Error("Invalid response format"));
            }
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              reject(new Error(error.detail || "Upload failed"));
            } catch (e) {
              reject(new Error(`Upload failed: ${xhr.statusText}`));
            }
          }
        });

        xhr.addEventListener("error", () => {
          reject(new Error("Network error occurred"));
        });

        xhr.open("POST", (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/upload");
        xhr.send(formData);
      });

      setUploadStage("indexing");
      const data = await uploadPromise;

      setUploadStatus({
        type: "success",
        message: `Indexed ${data.chunks_indexed} chunks successfully!`,
      });

      if (onUploadSuccess) {
        onUploadSuccess(data);
      }

      // Clear file after successful upload
      setTimeout(() => {
        setFile(null);
        setUploadStatus(null);
        setUploadProgress(0);
        setUploadStage("");
      }, 3000);
    } catch (error) {
      setUploadStatus({
        type: "error",
        message: error.message || "Upload failed",
      });
    } finally {
      setUploading(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setUploadStatus(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="w-full">
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 transition-all ${
          dragActive
            ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20"
            : "border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
          id="file-upload"
        />

        {!file ? (
          <label
            htmlFor="file-upload"
            className="flex flex-col items-center justify-center cursor-pointer"
          >
            <Upload className="w-12 h-12 text-gray-400 mb-3" />
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              <span className="font-semibold text-blue-600 dark:text-blue-400">
                Click to upload
              </span>{" "}
              or drag and drop
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500">
              PDF files only (max 10MB)
            </p>
          </label>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <File className="w-8 h-8 text-blue-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <button
                onClick={removeFile}
                className="ml-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                disabled={uploading}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>
                    {uploadStage === "uploading" && `Uploading... ${uploadProgress}%`}
                    {uploadStage === "processing" && "Processing PDF..."}
                    {uploadStage === "indexing" && "Indexing chunks..."}
                  </span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  <span>Upload & Index PDF</span>
                </>
              )}
            </button>

            {/* Progress Bar */}
            {uploading && (
              <div className="space-y-2">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      uploadStage === "uploading"
                        ? "bg-blue-600"
                        : uploadStage === "processing"
                        ? "bg-yellow-500"
                        : "bg-green-500"
                    }`}
                    style={{
                      width: uploadStage === "uploading" ? `${uploadProgress}%` : "100%",
                    }}
                  >
                    {(uploadStage === "processing" || uploadStage === "indexing") && (
                      <div className="h-full w-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
                    )}
                  </div>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 text-center">
                  {uploadStage === "uploading" && `Uploading file: ${uploadProgress}%`}
                  {uploadStage === "processing" && "Extracting text from PDF..."}
                  {uploadStage === "indexing" && "Creating embeddings and indexing..."}
                </p>
              </div>
            )}
          </div>
        )}

        {uploadStatus && (
          <div
            className={`mt-4 p-4 rounded-lg flex items-start space-x-3 ${
              uploadStatus.type === "success"
                ? "bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900"
                : "bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900"
            }`}
          >
            {uploadStatus.type === "success" ? (
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            )}
            <p
              className={`text-sm ${
                uploadStatus.type === "success"
                  ? "text-green-800 dark:text-green-200"
                  : "text-red-800 dark:text-red-200"
              }`}
            >
              {uploadStatus.message}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
