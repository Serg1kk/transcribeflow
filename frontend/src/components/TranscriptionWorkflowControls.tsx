"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Check, Loader2 } from "lucide-react";
import { updateTranscription, type Transcription } from "@/lib/api";

interface TranscriptionWorkflowControlsProps {
  transcription: Pick<Transcription, "id" | "workflow_status" | "workflow_comment">;
  onUpdated?: (transcription: Transcription) => void;
  compact?: boolean;
  showStatusRow?: boolean;
  showComment?: boolean;
}

export function TranscriptionWorkflowControls({
  transcription,
  onUpdated,
  compact = false,
  showStatusRow = true,
  showComment = true,
}: TranscriptionWorkflowControlsProps) {
  const [workflowStatus, setWorkflowStatus] = useState<"pending" | "processed">(
    transcription.workflow_status || "pending"
  );
  const [workflowComment, setWorkflowComment] = useState(transcription.workflow_comment || "");
  const [isSaving, setIsSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    setWorkflowStatus(transcription.workflow_status || "pending");
    setWorkflowComment(transcription.workflow_comment || "");
  }, [transcription.id, transcription.workflow_status, transcription.workflow_comment]);

  const commentDirty = useMemo(() => {
    return workflowComment !== (transcription.workflow_comment || "");
  }, [transcription.workflow_comment, workflowComment]);

  const flashSaved = () => {
    setJustSaved(true);
    window.setTimeout(() => setJustSaved(false), 350);
  };

  const persist = async (nextStatus: "pending" | "processed", nextComment: string) => {
    setIsSaving(true);
    try {
      const updated = await updateTranscription(transcription.id, {
        workflow_status: nextStatus,
        workflow_comment: nextComment,
      });
      setWorkflowStatus(updated.workflow_status);
      setWorkflowComment(updated.workflow_comment || "");
      onUpdated?.(updated);
      flashSaved();
      return updated;
    } catch (error) {
      console.error("Failed to save workflow fields:", error);
      throw error;
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleStatus = async () => {
    const previousStatus = workflowStatus;
    const nextStatus = workflowStatus === "processed" ? "pending" : "processed";
    setWorkflowStatus(nextStatus);
    try {
      await persist(nextStatus, workflowComment);
    } catch {
      setWorkflowStatus(previousStatus);
    }
  };

  const handleSaveComment = async () => {
    try {
      await persist(workflowStatus, workflowComment);
    } catch {
      // keep local text for retry
    }
  };

  const statusRow = showStatusRow ? (
    <div className={`flex items-center ${compact ? "justify-end" : "justify-between"} gap-2 flex-wrap`}>
      {!compact && <span className="text-sm font-medium">Processing status</span>}
      <div className="flex items-center gap-2">
        {workflowStatus === "processed" && (
          <Badge className="border-green-600 bg-green-600 text-white hover:bg-green-600">
            Processed
          </Badge>
        )}

        <Button
          size="sm"
          variant="outline"
          className={workflowStatus === "processed"
            ? "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
            : "border-green-200 bg-green-50 text-green-900 hover:bg-green-100 hover:text-green-950"
          }
          onClick={handleToggleStatus}
          disabled={isSaving}
        >
          {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          {workflowStatus === "processed" ? "Unprocess" : "Process"}
        </Button>
      </div>
    </div>
  ) : null;

  const commentRow = showComment ? (
    <div className="flex items-start gap-2">
      <textarea
        value={workflowComment}
        onChange={(e) => setWorkflowComment(e.target.value)}
        placeholder="Comment for this transcription..."
        rows={compact ? 3 : 4}
        className={`min-h-[72px] w-full flex-1 rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors duration-200 ${
          justSaved ? "border-green-500" : "border-input"
        }`}
      />

      {commentDirty && (
        <Button
          variant="ghost"
          size="icon"
          className="mt-1 h-8 w-8 text-primary"
          onClick={handleSaveComment}
          disabled={isSaving}
          title="Save comment"
        >
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Check className="h-4 w-4" />
          )}
        </Button>
      )}
    </div>
  ) : null;

  if (showStatusRow && !showComment) {
    return statusRow;
  }

  if (!showStatusRow && showComment) {
    return commentRow;
  }

  return <div className="space-y-3">{statusRow}{commentRow}</div>;
}
