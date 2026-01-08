// components/FileUpload.tsx
"use client";

import { useState, useCallback } from "react";
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

const ENGINES = [
  { value: "mlx-whisper", label: "MLX Whisper (recommended)" },
];

const MODELS = [
  { value: "large-v2", label: "large-v2 (default)" },
  { value: "large-v3-turbo", label: "large-v3-turbo" },
];

interface FileUploadProps {
  onUploadComplete?: () => void;
}

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [engine, setEngine] = useState("mlx-whisper");
  const [model, setModel] = useState("large-v2");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isAudioFile(droppedFile)) {
      setFile(droppedFile);
      setError(null);
    } else {
      setError("Please select an audio file (mp3, m4a, wav, ogg, flac, webm)");
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isAudioFile(selectedFile)) {
      setFile(selectedFile);
      setError(null);
    } else {
      setError("Please select an audio file");
    }
  }, []);

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      await uploadAudio(file, { engine, model });
      setFile(null);
      onUploadComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload error");
    } finally {
      setIsUploading(false);
    }
  };

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
          {file ? (
            <div className="space-y-2">
              <p className="font-medium">{file.name}</p>
              <p className="text-sm text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <Button variant="outline" size="sm" onClick={() => setFile(null)}>
                Remove
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <p>Drag and drop a file here or</p>
              <label>
                <input
                  type="file"
                  className="hidden"
                  accept=".mp3,.m4a,.wav,.ogg,.flac,.webm"
                  onChange={handleFileSelect}
                />
                <Button variant="outline" asChild>
                  <span>Select file</span>
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
                {ENGINES.map((e) => (
                  <SelectItem key={e.value} value={e.value}>
                    {e.label}
                  </SelectItem>
                ))}
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
                {MODELS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
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
          disabled={!file || isUploading}
          onClick={handleUpload}
        >
          {isUploading ? "Uploading..." : "Start Transcription"}
        </Button>
      </CardContent>
    </Card>
  );
}

function isAudioFile(file: File): boolean {
  const audioExtensions = [".mp3", ".m4a", ".wav", ".ogg", ".flac", ".webm"];
  return audioExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
}
