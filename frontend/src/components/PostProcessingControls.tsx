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
}

export function PostProcessingControls({
  transcriptionId,
  hasCleanedVersion,
  onProcessingComplete,
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
        if (data.length > 0 && !selectedTemplate) {
          setSelectedTemplate(data[0].id);
        }
      } catch (error) {
        console.error("Failed to load templates:", error);
      }
    }
    loadTemplates();
  }, [selectedTemplate]);

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
      await startPostProcessing(transcriptionId, selectedTemplate);
      toast.success("Post-processing started");

      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/postprocess/transcriptions/${transcriptionId}/cleaned`
          );
          if (response.ok) {
            clearInterval(pollInterval);
            setIsProcessing(false);
            toast.success("Post-processing complete!");
            onProcessingComplete();
          }
        } catch {
          // Still processing
        }
      }, 2000);

      // Timeout after 2 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        if (isProcessing) {
          setIsProcessing(false);
          toast.error("Post-processing timed out");
        }
      }, 120000);
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
