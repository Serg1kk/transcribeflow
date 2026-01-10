// components/TranscriptionQueue.tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import {
  getQueue,
  Transcription,
  updateTranscription,
  startTranscriptions,
  startAllTranscriptions,
  deleteTranscription,
  engineSupportsInitialPrompt,
} from "@/lib/api";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  queued: "Queued",
  processing: "Transcribing...",
  diarizing: "Identifying speakers...",
  completed: "Completed",
  failed: "Failed",
};

interface TranscriptionQueueProps {
  refreshTrigger?: number;
}

type SectionKey = "draft" | "queued" | "inProgress" | "completed";

export function TranscriptionQueue({ refreshTrigger }: TranscriptionQueueProps) {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expandedSections, setExpandedSections] = useState<Record<SectionKey, boolean>>({
    draft: true,
    queued: false,
    inProgress: true,
    completed: false,
  });
  const [isStarting, setIsStarting] = useState(false);

  const fetchQueue = useCallback(async () => {
    try {
      const data = await getQueue();
      setTranscriptions(data);
    } catch (error) {
      console.error("Failed to fetch queue:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, [refreshTrigger, fetchQueue]);

  // Group transcriptions by section
  const drafts = transcriptions.filter((t) => t.status === "draft");
  const queued = transcriptions.filter((t) => t.status === "queued");
  const inProgress = transcriptions.filter((t) =>
    ["processing", "diarizing"].includes(t.status)
  );
  const completed = transcriptions.filter((t) =>
    ["completed", "failed"].includes(t.status)
  );

  const toggleSection = (key: SectionKey) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleStartSelected = async () => {
    if (selectedIds.size === 0) return;
    setIsStarting(true);
    try {
      await startTranscriptions(Array.from(selectedIds));
      setSelectedIds(new Set());
      await fetchQueue();
    } catch (error) {
      console.error("Failed to start:", error);
    } finally {
      setIsStarting(false);
    }
  };

  const handleStartAll = async () => {
    setIsStarting(true);
    try {
      await startAllTranscriptions();
      setSelectedIds(new Set());
      await fetchQueue();
    } catch (error) {
      console.error("Failed to start all:", error);
    } finally {
      setIsStarting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTranscription(id);
      await fetchQueue();
    } catch (error) {
      console.error("Failed to delete:", error);
    }
  };

  const handleClearHistory = async (filterType: "all" | "failed") => {
    if (!confirm(`Delete ${filterType === "all" ? "ALL" : "failed"} transcriptions?`)) {
      return;
    }
    try {
      await fetch(`${API_BASE}/api/transcribe/history/${filterType}`, {
        method: "DELETE",
      });
      await fetchQueue();
    } catch (error) {
      console.error("Failed to delete:", error);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Transcription Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  const hasFailedItems = completed.some((t) => t.status === "failed");

  return (
    <div className="space-y-4">
      {/* Draft Section */}
      <QueueSection
        title="Draft"
        count={drafts.length}
        expanded={expandedSections.draft}
        onToggle={() => toggleSection("draft")}
        actions={
          drafts.length > 0 && (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={selectedIds.size === 0 || isStarting}
                onClick={handleStartSelected}
              >
                {isStarting ? "Starting..." : "Start Selected"}
              </Button>
              <Button
                size="sm"
                disabled={drafts.length === 0 || isStarting}
                onClick={handleStartAll}
              >
                {isStarting ? "Starting..." : "Start All"}
              </Button>
            </div>
          )
        }
      >
        {drafts.length === 0 ? (
          <p className="text-muted-foreground text-sm py-2">
            No files waiting. Drop files to upload.
          </p>
        ) : (
          drafts.map((t) => (
            <DraftItem
              key={t.id}
              transcription={t}
              selected={selectedIds.has(t.id)}
              onToggleSelect={() => toggleSelect(t.id)}
              onDelete={() => handleDelete(t.id)}
              onUpdate={fetchQueue}
            />
          ))
        )}
      </QueueSection>

      {/* Queued Section */}
      <QueueSection
        title="Queued"
        count={queued.length}
        expanded={expandedSections.queued}
        onToggle={() => toggleSection("queued")}
      >
        {queued.map((t) => (
          <QueuedItem key={t.id} transcription={t} />
        ))}
      </QueueSection>

      {/* In Progress Section */}
      <QueueSection
        title="In Progress"
        count={inProgress.length}
        expanded={expandedSections.inProgress}
        onToggle={() => toggleSection("inProgress")}
      >
        {inProgress.map((t) => (
          <InProgressItem key={t.id} transcription={t} />
        ))}
      </QueueSection>

      {/* Completed Section */}
      <QueueSection
        title="Completed"
        count={completed.length}
        expanded={expandedSections.completed}
        onToggle={() => toggleSection("completed")}
        actions={
          completed.length > 0 && (
            <div className="flex gap-2">
              {hasFailedItems && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleClearHistory("failed")}
                >
                  Clear Failed
                </Button>
              )}
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleClearHistory("all")}
              >
                Clear All
              </Button>
            </div>
          )
        }
      >
        {completed.map((t) => (
          <CompletedItem key={t.id} transcription={t} />
        ))}
      </QueueSection>
    </div>
  );
}

// Section wrapper component
function QueueSection({
  title,
  count,
  expanded,
  onToggle,
  actions,
  children,
}: {
  title: string;
  count: number;
  expanded: boolean;
  onToggle: () => void;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="py-3">
        <div className="flex items-center justify-between">
          <button
            onClick={onToggle}
            className="flex items-center gap-2 hover:opacity-70"
          >
            <span className="text-sm">{expanded ? "▼" : "▶"}</span>
            <CardTitle className="text-lg">
              {title} ({count})
            </CardTitle>
          </button>
          {actions}
        </div>
      </CardHeader>
      {expanded && <CardContent className="pt-0 space-y-3">{children}</CardContent>}
    </Card>
  );
}

// Draft item with checkbox and editable context
function DraftItem({
  transcription,
  selected,
  onToggleSelect,
  onDelete,
  onUpdate,
}: {
  transcription: Transcription;
  selected: boolean;
  onToggleSelect: () => void;
  onDelete: () => void;
  onUpdate: () => void;
}) {
  const [prompt, setPrompt] = useState(transcription.initial_prompt || "");
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Local engines use context for transcription + insights, cloud only for insights
  const isLocalEngine = engineSupportsInitialPrompt(transcription.engine);
  const placeholder = isLocalEngine
    ? "Enter context for better transcription and AI insights..."
    : "Enter context for better AI insights...";

  const handleSave = async () => {
    if (prompt === (transcription.initial_prompt || "")) return;
    setIsSaving(true);
    try {
      await updateTranscription(transcription.id, { initial_prompt: prompt });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onUpdate();
    } catch (error) {
      console.error("Failed to save:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const fileSizeMB = transcription.file_size
    ? (transcription.file_size / 1024 / 1024).toFixed(1) + " MB"
    : null;

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelect}
          className="h-4 w-4 rounded border-gray-300"
        />
        <span className="font-medium flex-1">{transcription.filename}</span>
        <span className="text-xs text-muted-foreground">{transcription.engine}/{transcription.model}</span>
        {fileSizeMB && <span className="text-sm text-muted-foreground">{fileSizeMB}</span>}
        <Button variant="ghost" size="sm" onClick={onDelete}>
          🗑️
        </Button>
      </div>
      <div className="flex items-center gap-2 pl-7">
        <Input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onBlur={handleSave}
          placeholder={placeholder}
          className="h-8 text-sm"
        />
        {isSaving && <span className="text-xs text-muted-foreground">Saving...</span>}
        {saved && <span className="text-xs text-green-600">Saved</span>}
      </div>
    </div>
  );
}

// Queued item (read-only)
function QueuedItem({ transcription }: { transcription: Transcription }) {
  const fileSizeMB = transcription.file_size
    ? (transcription.file_size / 1024 / 1024).toFixed(1) + " MB"
    : null;

  return (
    <div className="border rounded-lg p-3 space-y-1">
      <div className="flex items-center justify-between">
        <span className="font-medium">{transcription.filename}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">{transcription.engine}/{transcription.model}</span>
          {fileSizeMB && <span className="text-sm text-muted-foreground">{fileSizeMB}</span>}
          <Badge variant="secondary">{STATUS_LABELS[transcription.status]}</Badge>
        </div>
      </div>
      {transcription.initial_prompt && (
        <p className="text-sm text-muted-foreground">
          Initial prompt: &quot;{transcription.initial_prompt}&quot;
        </p>
      )}
    </div>
  );
}

// In Progress item with progress bar
function InProgressItem({ transcription }: { transcription: Transcription }) {
  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-medium">{transcription.filename}</span>
          <span className="text-xs text-muted-foreground">{transcription.engine}/{transcription.model}</span>
        </div>
        <Badge>{STATUS_LABELS[transcription.status]} {Math.round(transcription.progress)}%</Badge>
      </div>
      <Progress value={transcription.progress} className="h-2" />
      {transcription.initial_prompt && (
        <p className="text-sm text-muted-foreground">
          Initial prompt: &quot;{transcription.initial_prompt}&quot;
        </p>
      )}
    </div>
  );
}

// Completed item
function CompletedItem({ transcription }: { transcription: Transcription }) {
  const isCompleted = transcription.status === "completed";
  const isFailed = transcription.status === "failed";

  const formatTime = (seconds: number | null) => {
    if (!seconds) return null;
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const fileSizeMB = transcription.file_size
    ? (transcription.file_size / 1024 / 1024).toFixed(1) + " MB"
    : null;

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <Link
              href={`/transcription/${transcription.id}`}
              className="font-medium hover:underline"
            >
              {transcription.filename}
            </Link>
          ) : (
            <span className="font-medium">{transcription.filename}</span>
          )}
        </div>
        <Badge variant={isFailed ? "destructive" : "outline"}>
          {isFailed ? "Failed" : "Completed"}
        </Badge>
      </div>

      {isFailed && transcription.error_message && (
        <div className="text-sm text-red-600 bg-red-50 rounded p-2">
          {transcription.error_message}
        </div>
      )}

      {transcription.initial_prompt && (
        <p className="text-sm text-muted-foreground">
          Initial prompt: &quot;{transcription.initial_prompt}&quot;
        </p>
      )}

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground bg-muted/50 rounded px-2 py-1">
        {/* Engine/Model info */}
        {transcription.engine === "mlx-whisper" ? (
          <>
            <span>{transcription.model}</span>
            {transcription.compute_device && (
              <span className="uppercase">{transcription.compute_device === "mps" ? "GPU" : transcription.compute_device}</span>
            )}
          </>
        ) : (
          <span>{transcription.engine}</span>
        )}
        {fileSizeMB && <span>{fileSizeMB}</span>}
        {transcription.duration_seconds && <span>{formatDuration(transcription.duration_seconds)}</span>}
        {/* Timing info */}
        {isCompleted && transcription.processing_time_seconds && (
          <>
            <span className="text-muted-foreground/50">|</span>
            <span>Total: {formatTime(transcription.processing_time_seconds)}</span>
            {/* Show ASR/Diarization breakdown only for local engine */}
            {transcription.engine === "mlx-whisper" && (
              <>
                {transcription.transcription_time_seconds && (
                  <span>ASR: {formatTime(transcription.transcription_time_seconds)}</span>
                )}
                {transcription.diarization_time_seconds && transcription.diarization_method !== "none" && (
                  <span>
                    Diarization ({transcription.compute_device === "mps" ? "GPU" : "CPU"}): {formatTime(transcription.diarization_time_seconds)}
                  </span>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
