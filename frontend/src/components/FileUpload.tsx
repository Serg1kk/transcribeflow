// components/FileUpload.tsx
"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { uploadAudio } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Engine {
  id: string;
  name: string;
  models: string[];
  available: boolean;
}

interface FileUploadProps {
  onUploadComplete?: () => void;
}

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [engine, setEngine] = useState("mlx-whisper");
  const [model, setModel] = useState("large-v3-turbo");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Fetch available engines and default settings
  useEffect(() => {
    // Fetch engines
    fetch(`${API_BASE}/api/engines`)
      .then((res) => res.json())
      .then((data) => {
        if (data.engines) {
          setEngines(data.engines);
        }
      })
      .catch(() => {});

    // Fetch default settings
    fetch(`${API_BASE}/api/settings`)
      .then((res) => res.json())
      .then((settings) => {
        if (settings.default_engine) setEngine(settings.default_engine);
        if (settings.default_model) setModel(settings.default_model);
      })
      .catch(() => {});
  }, []);

  // Get models for current engine
  const currentEngine = engines.find((e) => e.id === engine);
  const availableModels = useMemo(
    () => currentEngine?.models || [],
    [currentEngine]
  );

  // Reset model if not available for current engine
  useEffect(() => {
    if (availableModels.length > 0 && !availableModels.includes(model)) {
      setModel(availableModels[0]);
    }
  }, [engine, availableModels, model]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(isAudioFile);
    if (droppedFiles.length > 0) {
      setFiles((prev) => [...prev, ...droppedFiles]);
      setError(null);
    } else {
      setError("Please select audio files (mp3, m4a, wav, ogg, flac, webm)");
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []).filter(isAudioFile);
    if (selectedFiles.length > 0) {
      setFiles((prev) => [...prev, ...selectedFiles]);
      setError(null);
    } else {
      setError("Please select audio files");
    }
    // Reset input so same files can be selected again
    e.target.value = "";
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearAllFiles = useCallback(() => {
    setFiles([]);
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        await uploadAudio(files[i], { engine, model });
        setUploadProgress(((i + 1) / files.length) * 100);
      }
      setFiles([]);
      onUploadComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload error");
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>New Transcription</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drop zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDragging
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-primary/50"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {files.length > 0 ? (
            <div className="space-y-3">
              <div className="max-h-32 overflow-y-auto space-y-1">
                {files.map((file, index) => (
                  <div key={index} className="flex items-center justify-between text-sm bg-muted/50 rounded px-2 py-1">
                    <span className="truncate flex-1 text-left">{file.name}</span>
                    <span className="text-muted-foreground mx-2">
                      {(file.size / 1024 / 1024).toFixed(1)} MB
                    </span>
                    <button
                      onClick={() => removeFile(index)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
              <p className="text-sm text-muted-foreground">
                {files.length} file{files.length > 1 ? "s" : ""} ({(totalSize / 1024 / 1024).toFixed(2)} MB total)
              </p>
              <div className="flex gap-2 justify-center">
                <label>
                  <input
                    type="file"
                    className="hidden"
                    accept=".mp3,.m4a,.wav,.ogg,.flac,.webm"
                    multiple
                    onChange={handleFileSelect}
                  />
                  <Button variant="outline" size="sm" asChild>
                    <span>Add more</span>
                  </Button>
                </label>
                <Button variant="outline" size="sm" onClick={clearAllFiles}>
                  Clear all
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <p>Drag and drop files here or</p>
              <label>
                <input
                  type="file"
                  className="hidden"
                  accept=".mp3,.m4a,.wav,.ogg,.flac,.webm"
                  multiple
                  onChange={handleFileSelect}
                />
                <Button variant="outline" asChild>
                  <span>Select file(s)</span>
                </Button>
              </label>
            </div>
          )}
        </div>

        {/* Settings */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Engine</Label>
            <Select value={engine} onValueChange={setEngine}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {engines.length > 0 ? (
                  engines.map((e) => (
                    <SelectItem key={e.id} value={e.id}>
                      {e.name}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="mlx-whisper">MLX Local</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {availableModels.length > 0 ? (
                  availableModels.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="large-v3-turbo">large-v3-turbo</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {/* Upload button */}
        <Button
          className="w-full"
          disabled={files.length === 0 || isUploading}
          onClick={handleUpload}
        >
          {isUploading
            ? `Adding... ${Math.round(uploadProgress)}%`
            : files.length > 1
            ? `Add ${files.length} files`
            : "Add"}
        </Button>
      </CardContent>
    </Card>
  );
}

function isAudioFile(file: File): boolean {
  const audioExtensions = [".mp3", ".m4a", ".wav", ".ogg", ".flac", ".webm"];
  return audioExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
}
