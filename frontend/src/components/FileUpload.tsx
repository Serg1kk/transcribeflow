'use client';

import { useState, useCallback, useEffect, useMemo } from "react";
import { useIntl } from "react-intl";
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
import { formatTranscriptionModelLabel } from "@/lib/transcriptionModels";

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
  const intl = useIntl();
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [engine, setEngine] = useState("mlx-whisper");
  const [model, setModel] = useState("large-v3-turbo");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [elevenlabsKeytermsEnabled, setElevenlabsKeytermsEnabled] = useState(false);
  const [elevenlabsKeytermsText, setElevenlabsKeytermsText] = useState("");
  const [elevenlabsEntityDetectionEnabled, setElevenlabsEntityDetectionEnabled] = useState(false);
  const [elevenlabsDetectionScope, setElevenlabsDetectionScope] = useState("all");
  const [elevenlabsDetectionCustomText, setElevenlabsDetectionCustomText] = useState("");
  const [elevenlabsEntityRedactionEnabled, setElevenlabsEntityRedactionEnabled] = useState(false);
  const [elevenlabsRedactionScope, setElevenlabsRedactionScope] = useState("same_as_detection");
  const [elevenlabsRedactionCustomText, setElevenlabsRedactionCustomText] = useState("");
  const [elevenlabsRedactionMode, setElevenlabsRedactionMode] = useState("enumerated_entity_type");

  useEffect(() => {
    fetch(`${API_BASE}/api/engines`)
      .then((res) => res.json())
      .then((data) => {
        if (data.engines) {
          setEngines(data.engines);
        }
      })
      .catch(() => {});

    fetch(`${API_BASE}/api/settings`)
      .then((res) => res.json())
      .then((settings) => {
        if (settings.default_engine) setEngine(settings.default_engine);
        if (settings.default_model) setModel(settings.default_model);
      })
      .catch(() => {});
  }, []);

  const currentEngine = engines.find((e) => e.id === engine);
  const availableModels = useMemo(
    () => currentEngine?.models || [],
    [currentEngine]
  );
  const isElevenLabs = engine === "elevenlabs";

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
      setError(intl.formatMessage({ id: 'upload.error.invalidType' }));
    }
  }, [intl]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []).filter(isAudioFile);
    if (selectedFiles.length > 0) {
      setFiles((prev) => [...prev, ...selectedFiles]);
      setError(null);
    } else {
      setError(intl.formatMessage({ id: 'upload.error.noFiles' }));
    }
    e.target.value = "";
  }, [intl]);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearAllFiles = useCallback(() => {
    setFiles([]);
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;

    const requestModel = isElevenLabs ? "scribe_v2" : model;
    const keyterms = elevenlabsKeytermsEnabled
      ? parseTextareaList(elevenlabsKeytermsText)
      : [];
    const entityDetection = isElevenLabs && elevenlabsEntityDetectionEnabled
      ? resolveEntitySelection(elevenlabsDetectionScope, elevenlabsDetectionCustomText)
      : [];
    const entityRedaction = isElevenLabs && elevenlabsEntityRedactionEnabled
      ? (elevenlabsRedactionScope === "same_as_detection"
          ? entityDetection
          : resolveEntitySelection(elevenlabsRedactionScope, elevenlabsRedactionCustomText))
      : [];

    if (isElevenLabs && elevenlabsKeytermsEnabled && keyterms.length === 0) {
      setError(intl.formatMessage({ id: 'upload.elevenlabs.error.keytermsRequired' }));
      return;
    }

    if (isElevenLabs && elevenlabsEntityDetectionEnabled && entityDetection.length === 0) {
      setError(intl.formatMessage({ id: 'upload.elevenlabs.error.entityDetectionRequired' }));
      return;
    }

    if (isElevenLabs && elevenlabsEntityRedactionEnabled) {
      if (!elevenlabsEntityDetectionEnabled || entityDetection.length === 0) {
        setError(intl.formatMessage({ id: 'upload.elevenlabs.error.redactionNeedsDetection' }));
        return;
      }
      if (entityRedaction.length === 0) {
        setError(intl.formatMessage({ id: 'upload.elevenlabs.error.entityRedactionRequired' }));
        return;
      }
    }

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        await uploadAudio(files[i], {
          engine,
          model: requestModel,
          elevenlabsKeyterms: isElevenLabs && elevenlabsKeytermsEnabled ? keyterms : undefined,
          elevenlabsEntityDetection: isElevenLabs && elevenlabsEntityDetectionEnabled ? entityDetection : undefined,
          elevenlabsEntityRedaction: isElevenLabs && elevenlabsEntityRedactionEnabled ? entityRedaction : undefined,
          elevenlabsEntityRedactionMode: isElevenLabs && elevenlabsEntityRedactionEnabled ? elevenlabsRedactionMode : undefined,
        });
        setUploadProgress(((i + 1) / files.length) * 100);
      }
      setFiles([]);
      onUploadComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : intl.formatMessage({ id: 'error.uploadFailed' }));
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);
  const totalSizeMB = (totalSize / 1024 / 1024).toFixed(2);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{intl.formatMessage({ id: 'upload.title' })}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
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
                      {(file.size / 1024 / 1024).toFixed(1)} {intl.formatMessage({ id: 'units.mb' })}
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
                {intl.formatMessage({ id: 'upload.files.total' }, { count: files.length, size: totalSizeMB })}
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
                    <span>{intl.formatMessage({ id: 'button.addMore' })}</span>
                  </Button>
                </label>
                <Button variant="outline" size="sm" onClick={clearAllFiles}>
                  {intl.formatMessage({ id: 'button.clearAll' })}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <p>{intl.formatMessage({ id: 'upload.dropzone.hint' })}</p>
              <label>
                <input
                  type="file"
                  className="hidden"
                  accept=".mp3,.m4a,.wav,.ogg,.flac,.webm"
                  multiple
                  onChange={handleFileSelect}
                />
                <Button variant="outline" asChild>
                  <span>{intl.formatMessage({ id: 'upload.dropzone.button' })}</span>
                </Button>
              </label>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>{intl.formatMessage({ id: 'label.engine' })}</Label>
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
                  <SelectItem value="mlx-whisper">{intl.formatMessage({ id: 'upload.fallback.engine' })}</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>{intl.formatMessage({ id: 'label.model' })}</Label>
            <Select value={isElevenLabs ? 'scribe_v2' : model} onValueChange={setModel}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {availableModels.length > 0 ? (
                  availableModels.map((m) => (
                    <SelectItem key={m} value={m}>
                      {formatTranscriptionModelLabel(m)}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="large-v3-turbo">{intl.formatMessage({ id: 'upload.fallback.model' })}</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        {isElevenLabs && (
          <div className="space-y-4 rounded-lg border p-4 bg-muted/20">
            <div className="space-y-1">
              <p className="text-sm font-medium">
                {intl.formatMessage({ id: 'upload.elevenlabs.title' })}
              </p>
              <p className="text-xs text-muted-foreground">
                {intl.formatMessage({ id: 'upload.elevenlabs.description' })}
              </p>
            </div>

            <div className="space-y-3 rounded-md border bg-background p-3">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={elevenlabsKeytermsEnabled}
                  onChange={(e) => setElevenlabsKeytermsEnabled(e.target.checked)}
                />
                <div className="space-y-1">
                  <p className="text-sm font-medium">
                    {intl.formatMessage({ id: 'upload.elevenlabs.keyterms.label' })}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {intl.formatMessage({ id: 'upload.elevenlabs.keyterms.help' })}
                  </p>
                </div>
              </label>

              {elevenlabsKeytermsEnabled && (
                <div className="space-y-2 pl-7">
                  <textarea
                    value={elevenlabsKeytermsText}
                    onChange={(e) => setElevenlabsKeytermsText(e.target.value)}
                    placeholder={intl.formatMessage({ id: 'upload.elevenlabs.keyterms.placeholder' })}
                    rows={5}
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    {intl.formatMessage({ id: 'upload.elevenlabs.keyterms.constraints' })}
                  </p>
                </div>
              )}
            </div>

            <div className="space-y-3 rounded-md border bg-background p-3">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={elevenlabsEntityDetectionEnabled}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setElevenlabsEntityDetectionEnabled(checked);
                    if (!checked) {
                      setElevenlabsEntityRedactionEnabled(false);
                    }
                  }}
                />
                <div className="space-y-1">
                  <p className="text-sm font-medium">
                    {intl.formatMessage({ id: 'upload.elevenlabs.entityDetection.label' })}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {intl.formatMessage({ id: 'upload.elevenlabs.entityDetection.help' })}
                  </p>
                </div>
              </label>

              {elevenlabsEntityDetectionEnabled && (
                <div className="space-y-3 pl-7">
                  <div className="space-y-2">
                    <Label>{intl.formatMessage({ id: 'upload.elevenlabs.entityDetection.scope' })}</Label>
                    <Select value={elevenlabsDetectionScope} onValueChange={setElevenlabsDetectionScope}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">all</SelectItem>
                        <SelectItem value="pii">pii</SelectItem>
                        <SelectItem value="phi">phi</SelectItem>
                        <SelectItem value="pci">pci</SelectItem>
                        <SelectItem value="other">other</SelectItem>
                        <SelectItem value="offensive_language">offensive_language</SelectItem>
                        <SelectItem value="custom">custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {elevenlabsDetectionScope === "custom" && (
                    <div className="space-y-2">
                      <textarea
                        value={elevenlabsDetectionCustomText}
                        onChange={(e) => setElevenlabsDetectionCustomText(e.target.value)}
                        placeholder={intl.formatMessage({ id: 'upload.elevenlabs.entityDetection.placeholder' })}
                        rows={4}
                        className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      />
                      <p className="text-xs text-muted-foreground">
                        {intl.formatMessage({ id: 'upload.elevenlabs.entityDetection.customHelp' })}
                      </p>
                    </div>
                  )}

                  <div className="space-y-3 rounded-md border p-3 bg-muted/10">
                    <label className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4"
                        checked={elevenlabsEntityRedactionEnabled}
                        onChange={(e) => setElevenlabsEntityRedactionEnabled(e.target.checked)}
                      />
                      <div className="space-y-1">
                        <p className="text-sm font-medium">
                          {intl.formatMessage({ id: 'upload.elevenlabs.redaction.label' })}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {intl.formatMessage({ id: 'upload.elevenlabs.redaction.help' })}
                        </p>
                      </div>
                    </label>

                    {elevenlabsEntityRedactionEnabled && (
                      <div className="space-y-3 pl-7">
                        <div className="space-y-2">
                          <Label>{intl.formatMessage({ id: 'upload.elevenlabs.redaction.scope' })}</Label>
                          <Select value={elevenlabsRedactionScope} onValueChange={setElevenlabsRedactionScope}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="same_as_detection">same_as_detection</SelectItem>
                              <SelectItem value="all">all</SelectItem>
                              <SelectItem value="pii">pii</SelectItem>
                              <SelectItem value="phi">phi</SelectItem>
                              <SelectItem value="pci">pci</SelectItem>
                              <SelectItem value="other">other</SelectItem>
                              <SelectItem value="offensive_language">offensive_language</SelectItem>
                              <SelectItem value="custom">custom</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {elevenlabsRedactionScope === "custom" && (
                          <div className="space-y-2">
                            <textarea
                              value={elevenlabsRedactionCustomText}
                              onChange={(e) => setElevenlabsRedactionCustomText(e.target.value)}
                              placeholder={intl.formatMessage({ id: 'upload.elevenlabs.redaction.placeholder' })}
                              rows={4}
                              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                            />
                            <p className="text-xs text-muted-foreground">
                              {intl.formatMessage({ id: 'upload.elevenlabs.redaction.customHelp' })}
                            </p>
                          </div>
                        )}

                        <div className="space-y-2">
                          <Label>{intl.formatMessage({ id: 'upload.elevenlabs.redaction.mode' })}</Label>
                          <Select value={elevenlabsRedactionMode} onValueChange={setElevenlabsRedactionMode}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="enumerated_entity_type">enumerated_entity_type</SelectItem>
                              <SelectItem value="entity_type">entity_type</SelectItem>
                              <SelectItem value="redacted">redacted</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <Button
          className="w-full"
          disabled={files.length === 0 || isUploading}
          onClick={handleUpload}
        >
          {isUploading
            ? intl.formatMessage({ id: 'upload.button.adding' }, { progress: Math.round(uploadProgress) })
            : files.length > 1
            ? intl.formatMessage({ id: 'upload.button.addFiles' }, { count: files.length })
            : intl.formatMessage({ id: 'button.add' })}
        </Button>
      </CardContent>
    </Card>
  );
}

function isAudioFile(file: File): boolean {
  const audioExtensions = [".mp3", ".m4a", ".wav", ".ogg", ".flac", ".webm"];
  return audioExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
}

function parseTextareaList(value: string): string[] {
  return Array.from(
    new Set(
      value
        .replace(/\n/g, ",")
        .split(",")
        .map((item) => item.trim().replace(/\s+/g, " "))
        .filter(Boolean)
    )
  );
}

function resolveEntitySelection(scope: string, customValue: string): string[] {
  if (scope === "custom") {
    return parseTextareaList(customValue);
  }
  return scope ? [scope] : [];
}
