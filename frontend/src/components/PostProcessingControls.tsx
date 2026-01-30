// components/PostProcessingControls.tsx
"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getTemplates,
  startPostProcessing,
  Template,
} from "@/lib/api";

interface PostProcessingControlsProps {
  transcriptionId: string;
  hasCleanedVersion: boolean;
  onProcessingComplete: () => void;
  onTemplateChange?: (templateId: string) => void;
  usedTemplateId?: string; // Template that was previously used for cleanup
}

export function PostProcessingControls({
  transcriptionId,
  hasCleanedVersion,
  onProcessingComplete,
  onTemplateChange,
  usedTemplateId,
}: PostProcessingControlsProps) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    async function loadTemplates() {
      try {
        const data = await getTemplates();
        setTemplates(data);
        // If we have a previously used template, use that; otherwise use first template
        if (data.length > 0 && !selectedTemplate) {
          const templateToUse = usedTemplateId && data.find(t => t.id === usedTemplateId)
            ? usedTemplateId
            : data[0].id;
          setSelectedTemplate(templateToUse);
        }
      } catch (error) {
        console.error("Failed to load templates:", error);
      }
    }
    loadTemplates();
  }, [selectedTemplate, usedTemplateId]);

  // Notify parent when template selection changes
  useEffect(() => {
    if (selectedTemplate && onTemplateChange) {
      onTemplateChange(selectedTemplate);
    }
  }, [selectedTemplate, onTemplateChange]);

  async function handleProcess() {
    // If there's already a cleaned version, ask for confirmation
    if (hasCleanedVersion && !showConfirm) {
      setShowConfirm(true);
      return;
    }

    if (!selectedTemplate) {
      toast.error("Please select a template");
      return;
    }

    setIsProcessing(true);
    setShowConfirm(false);

    try {
      const startTime = new Date().toISOString();
      await startPostProcessing(transcriptionId, selectedTemplate);
      toast.success("Post-processing started");

      // Poll for completion or failure by checking operation status
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      let pollCount = 0;
      const maxPolls = 500; // ~16 minutes at 2s intervals (covers Gemini 15min timeout + retries)

      const pollInterval = setInterval(async () => {
        pollCount++;

        try {
          // Check operation status (not file existence - file might be from previous run)
          const opsResponse = await fetch(
            `${API_BASE}/api/postprocess/operations?transcription_id=${transcriptionId}&limit=1&_t=${Date.now()}`
          );
          if (opsResponse.ok) {
            const ops = await opsResponse.json();
            if (ops.length > 0) {
              const latestOp = ops[0];
              // Only consider operations created after we started
              if (latestOp.created_at >= startTime) {
                if (latestOp.status === "success") {
                  clearInterval(pollInterval);
                  setIsProcessing(false);
                  toast.success("Post-processing complete!");
                  onProcessingComplete();
                  return;
                } else if (latestOp.status === "failed") {
                  clearInterval(pollInterval);
                  setIsProcessing(false);
                  toast.error(`Post-processing failed: ${latestOp.error_message || "Unknown error"}`);
                  return;
                }
                // status is "processing" - keep polling
              }
            }
          }

          // Timeout check
          if (pollCount >= maxPolls) {
            clearInterval(pollInterval);
            setIsProcessing(false);
            toast.error("Post-processing timed out");
          }
        } catch {
          // Network error, keep polling
        }
      }, 2000);
    } catch (error) {
      setIsProcessing(false);
      toast.error(
        error instanceof Error ? error.message : "Post-processing failed"
      );
    }
  }

  function handleCancel() {
    setShowConfirm(false);
  }

  return (
    <div className="flex items-center gap-3">
      {/* Done indicator */}
      {hasCleanedVersion && (
        <span className="text-green-600 flex items-center gap-1" title="Cleanup completed">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </span>
      )}

      <Select
        value={selectedTemplate}
        onValueChange={setSelectedTemplate}
        disabled={isProcessing}
      >
        <SelectTrigger className="w-48">
          <SelectValue placeholder="Select template" />
        </SelectTrigger>
        <SelectContent>
          {templates.map((template) => (
            <SelectItem key={template.id} value={template.id}>
              {template.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {showConfirm ? (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Replace existing?
          </span>
          <Button size="sm" onClick={handleProcess}>
            Yes
          </Button>
          <Button size="sm" variant="outline" onClick={handleCancel}>
            No
          </Button>
        </div>
      ) : (
        <Button
          onClick={handleProcess}
          disabled={isProcessing || !selectedTemplate}
          variant={hasCleanedVersion ? "outline" : "default"}
        >
          {isProcessing ? (
            <>
              <span className="animate-spin mr-2">&#8987;</span>
              Processing...
            </>
          ) : hasCleanedVersion ? (
            "Re-clean with LLM"
          ) : (
            "Clean with LLM"
          )}
        </Button>
      )}
    </div>
  );
}
