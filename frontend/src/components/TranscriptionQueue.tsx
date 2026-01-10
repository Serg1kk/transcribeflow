// components/TranscriptionQueue.tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { useIntl } from "react-intl";
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

interface TranscriptionQueueProps {
  refreshTrigger?: number;
}

type SectionKey = "draft" | "queued" | "inProgress" | "completed";

export function TranscriptionQueue({ refreshTrigger }: TranscriptionQueueProps) {
  const intl = useIntl();
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

  const STATUS_LABELS: Record<string, string> = {
    draft: intl.formatMessage({ id: "queue.section.draft" }),
    queued: intl.formatMessage({ id: "queue.section.queued" }),
    processing: intl.formatMessage({ id: "status.transcribing" }),
    diarizing: intl.formatMessage({ id: "status.diarizing" }),
    completed: intl.formatMessage({ id: "status.completed" }),
    failed: intl.formatMessage({ id: "status.failed" }),
  };

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
    const typeLabel = filterType === "all" ? "ALL" : "failed";
    if (!confirm(intl.formatMessage({ id: "queue.confirm.delete" }, { type: typeLabel }))) {
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
          <CardTitle>{intl.formatMessage({ id: "queue.title" })}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">{intl.formatMessage({ id: "status.processing" })}</p>
        </CardContent>
      </Card>
    );
  }

  const hasFailedItems = completed.some((t) => t.status === "failed");

  return (
    <div className="space-y-4">
      {/* Draft Section */}
      <QueueSection
        title={intl.formatMessage({ id: "queue.section.draft" })}
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
                {isStarting ? intl.formatMessage({ id: "queue.button.starting" }) : intl.formatMessage({ id: "queue.button.startSelected" })}
              </Button>
              <Button
                size="sm"
                disabled={drafts.length === 0 || isStarting}
                onClick={handleStartAll}
              >
                {isStarting ? intl.formatMessage({ id: "queue.button.starting" }) : intl.formatMessage({ id: "queue.button.startAll" })}
              </Button>
            </div>
          )
        }
      >
        {drafts.length === 0 ? (
          <p className="text-muted-foreground text-sm py-2">
            {intl.formatMessage({ id: "queue.empty" })}
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
        title={intl.formatMessage({ id: "queue.section.queued" })}
        count={queued.length}
        expanded={expandedSections.queued}
        onToggle={() => toggleSection("queued")}
      >
        {queued.map((t) => (
          <QueuedItem key={t.id} transcription={t} statusLabels={STATUS_LABELS} />
        ))}
      </QueueSection>

      {/* In Progress Section */}
      <QueueSection
        title={intl.formatMessage({ id: "queue.section.inProgress" })}
        count={inProgress.length}
        expanded={expandedSections.inProgress}
        onToggle={() => toggleSection("inProgress")}
      >
        {inProgress.map((t) => (
          <InProgressItem key={t.id} transcription={t} statusLabels={STATUS_LABELS} />
        ))}
      </QueueSection>

      {/* Completed Section */}
      <QueueSection
        title={intl.formatMessage({ id: "queue.section.completed" })}
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
                  {intl.formatMessage({ id: "queue.button.clearFailed" })}
                </Button>
              )}
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleClearHistory("all")}
              >
                {intl.formatMessage({ id: "queue.button.clearAll" })}
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
function QueuedItem({ transcription, statusLabels }: { transcription: Transcription; statusLabels: Record<string, string> }) {
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
          <Badge variant="secondary">{statusLabels[transcription.status]}</Badge>
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
function InProgressItem({ transcription, statusLabels }: { transcription: Transcription; statusLabels: Record<string, string> }) {
  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-medium">{transcription.filename}</span>
          <span className="text-xs text-muted-foreground">{transcription.engine}/{transcription.model}</span>
        </div>
        <Badge>{statusLabels[transcription.status]} {Math.round(transcription.progress)}%</Badge>
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
  const intl = useIntl();
  const isCompleted = transcription.status === "completed";
  const isFailed = transcription.status === "failed";

  // Format time as "1h 23m 45s" (skip hours if < 1h, skip minutes if < 1m)
  const formatTime = (seconds: number | null) => {
    if (!seconds) return null;
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.round(seconds % 60);

    if (hours > 0) {
      return `${hours}h ${mins}m ${secs}s`;
    } else if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  // Format duration for file (same format as formatTime)
  const formatDuration = (seconds: number | null) => {
    return formatTime(seconds);
  };

  const fileSizeMB = transcription.file_size
    ? (transcription.file_size / 1024 / 1024).toFixed(1) + " MB"
    : null;

  // Get LLM operations by type (latest only for display, but count all for cost)
  const cleanupOps = transcription.llm_operations?.filter(op => op.operation_type === "cleanup") || [];
  const insightsOps = transcription.llm_operations?.filter(op => op.operation_type === "insights") || [];
  const latestCleanup = cleanupOps[0]; // Already sorted desc by created_at
  const latestInsights = insightsOps[0];

  // Calculate totals
  const totalLLMCost = transcription.llm_operations?.reduce((sum, op) => sum + (op.cost_usd || 0), 0) || 0;
  const totalLLMTime = transcription.llm_operations?.reduce((sum, op) => sum + op.processing_time_seconds, 0) || 0;
  const totalTime = (transcription.processing_time_seconds || 0) + totalLLMTime;

  const formatCost = (cost: number | null) => {
    if (!cost) return null;
    return `$${cost.toFixed(4)}`;
  };

  const formatTokens = (input: number, output: number) => {
    const formatK = (n: number) => n >= 1000 ? `${(n/1000).toFixed(1)}k` : n.toString();
    return `${formatK(input)}→${formatK(output)}`;
  };

  return (
    <div className="border rounded-lg p-3 space-y-2">
      {/* Header: filename + size + duration + badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
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
          <span className="text-xs text-muted-foreground">
            {fileSizeMB && <span>{fileSizeMB}</span>}
            {fileSizeMB && transcription.duration_seconds && <span> • </span>}
            {transcription.duration_seconds && <span>{formatDuration(transcription.duration_seconds)}</span>}
          </span>
        </div>
        <Badge variant={isFailed ? "destructive" : "outline"}>
          {isFailed ? intl.formatMessage({ id: "status.failed" }) : intl.formatMessage({ id: "status.completed" })}
        </Badge>
      </div>

      {/* Error message for failed */}
      {isFailed && transcription.error_message && (
        <div className="text-sm text-red-600 bg-red-50 rounded p-2">
          {transcription.error_message}
        </div>
      )}

      {/* Context (formerly Initial prompt) */}
      {transcription.initial_prompt && (
        <p className="text-sm text-muted-foreground">
          Context: &quot;{transcription.initial_prompt}&quot;
        </p>
      )}

      {/* Processing section */}
      {isCompleted && (
        <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2 space-y-1 font-mono">
          {/* ASR */}
          <div className="flex justify-between">
            <span>
              <span className="text-green-600">✓</span> ASR: {transcription.model} (GPU)
            </span>
            <span>{formatTime(transcription.transcription_time_seconds)}</span>
          </div>

          {/* Diarization */}
          <div className="flex justify-between">
            {transcription.diarization_method && transcription.diarization_method !== "none" ? (
              <>
                <span>
                  <span className="text-green-600">✓</span> Diarization: {transcription.diarization_method === "fast" ? "Fast" : "Accurate"} ({transcription.compute_device === "cpu" ? "CPU" : "GPU"})
                </span>
                <span>{formatTime(transcription.diarization_time_seconds)}</span>
              </>
            ) : (
              <>
                <span><span className="text-muted-foreground/50">○</span> Diarization: not run</span>
                <span></span>
              </>
            )}
          </div>

          {/* Clean */}
          <div className="flex justify-between">
            {latestCleanup ? (
              <>
                <span>
                  <span className="text-green-600">✓</span> Clean ({latestCleanup.template_id}): {latestCleanup.model} ({formatTokens(latestCleanup.input_tokens, latestCleanup.output_tokens)})
                  {cleanupOps.length > 1 && <span className="text-muted-foreground/60"> *</span>}
                </span>
                <span>{formatTime(latestCleanup.processing_time_seconds)} • {formatCost(latestCleanup.cost_usd)}</span>
              </>
            ) : (
              <>
                <span><span className="text-muted-foreground/50">○</span> Clean: not run</span>
                <span></span>
              </>
            )}
          </div>

          {/* AI Insights */}
          <div className="flex justify-between">
            {latestInsights ? (
              <>
                <span>
                  <span className="text-green-600">✓</span> AI Insights ({latestInsights.template_id}): {latestInsights.model} ({formatTokens(latestInsights.input_tokens, latestInsights.output_tokens)})
                  {insightsOps.length > 1 && <span className="text-muted-foreground/60"> *</span>}
                </span>
                <span>{formatTime(latestInsights.processing_time_seconds)} • {formatCost(latestInsights.cost_usd)}</span>
              </>
            ) : (
              <>
                <span><span className="text-muted-foreground/50">○</span> AI Insights: not run</span>
                <span></span>
              </>
            )}
          </div>

          {/* Separator and Total */}
          <div className="border-t border-muted-foreground/20 pt-1 mt-1 flex justify-between font-semibold">
            <span>Total</span>
            <span>
              {formatTime(totalTime)}
              {totalLLMCost > 0 && <span> • {formatCost(totalLLMCost)}</span>}
            </span>
          </div>

          {/* Note about multiple runs */}
          {(cleanupOps.length > 1 || insightsOps.length > 1) && (
            <div className="text-[10px] text-muted-foreground/60 pt-1">
              * Shows latest run only. Total cost includes all {cleanupOps.length + insightsOps.length} operations.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
