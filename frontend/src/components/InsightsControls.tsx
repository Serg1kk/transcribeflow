// components/InsightsControls.tsx
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
  getInsightTemplates,
  generateInsights,
  checkInsightSources,
  InsightTemplate,
  SourceAvailability,
} from "@/lib/api";

interface InsightsControlsProps {
  transcriptionId: string;
  hasInsights: boolean;
  onGenerationComplete: (templateId: string) => void;
}

export function InsightsControls({
  transcriptionId,
  hasInsights,
  onGenerationComplete,
}: InsightsControlsProps) {
  const [templates, setTemplates] = useState<InsightTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [sources, setSources] = useState<SourceAvailability | null>(null);
  const [selectedSource, setSelectedSource] = useState<"original" | "cleaned">("original");
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [templatesData, sourcesData] = await Promise.all([
          getInsightTemplates(),
          checkInsightSources(transcriptionId),
        ]);
        setTemplates(templatesData);
        setSources(sourcesData);

        if (templatesData.length > 0 && !selectedTemplate) {
          setSelectedTemplate(templatesData[0].id);
        }

        // Default to cleaned if available
        if (sourcesData.cleaned) {
          setSelectedSource("cleaned");
        }
      } catch (error) {
        console.error("Failed to load insights data:", error);
      }
    }
    load();
  }, [transcriptionId, selectedTemplate]);

  async function handleGenerate() {
    if (hasInsights && !showConfirm) {
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
      await generateInsights(transcriptionId, selectedTemplate, selectedSource);
      toast.success("Generating insights...");

      // Poll for completion
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      let pollCount = 0;
      const maxPolls = 60;

      const pollInterval = setInterval(async () => {
        pollCount++;

        try {
          // Check for insights file
          const response = await fetch(
            `${API_BASE}/api/insights/transcriptions/${transcriptionId}/${selectedTemplate}?_t=${Date.now()}`
          );

          if (response.ok) {
            const data = await response.json();
            if (data.metadata?.created_at >= startTime) {
              clearInterval(pollInterval);
              setIsProcessing(false);
              toast.success("Insights generated!");
              onGenerationComplete(selectedTemplate);
              return;
            }
          }

          // Check for failure via operations
          const opsResponse = await fetch(
            `${API_BASE}/api/postprocess/operations?transcription_id=${transcriptionId}&limit=1&_t=${Date.now()}`
          );
          if (opsResponse.ok) {
            const ops = await opsResponse.json();
            if (ops.length > 0) {
              const latestOp = ops[0];
              if (
                latestOp.created_at >= startTime &&
                latestOp.status === "failed" &&
                latestOp.template_id === selectedTemplate
              ) {
                clearInterval(pollInterval);
                setIsProcessing(false);
                toast.error(`Failed: ${latestOp.error_message || "Unknown error"}`);
                return;
              }
            }
          }

          if (pollCount >= maxPolls) {
            clearInterval(pollInterval);
            setIsProcessing(false);
            toast.error("Generation timed out");
          }
        } catch {
          // Network error, keep polling
        }
      }, 2000);
    } catch (error) {
      setIsProcessing(false);
      toast.error(
        error instanceof Error ? error.message : "Failed to generate insights"
      );
    }
  }

  function handleCancel() {
    setShowConfirm(false);
  }

  const showSourceSelect = sources?.cleaned;

  return (
    <div className="flex items-center gap-3 flex-wrap">
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

      {showSourceSelect && (
        <Select
          value={selectedSource}
          onValueChange={(v) => setSelectedSource(v as "original" | "cleaned")}
          disabled={isProcessing}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="cleaned">Cleaned</SelectItem>
            <SelectItem value="original">Original</SelectItem>
          </SelectContent>
        </Select>
      )}

      {showConfirm ? (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Replace existing?
          </span>
          <Button size="sm" onClick={handleGenerate}>
            Yes
          </Button>
          <Button size="sm" variant="outline" onClick={handleCancel}>
            No
          </Button>
        </div>
      ) : (
        <Button
          onClick={handleGenerate}
          disabled={isProcessing || !selectedTemplate}
        >
          {isProcessing ? (
            <>
              <span className="animate-spin mr-2">&#8987;</span>
              Generating...
            </>
          ) : hasInsights ? (
            "Re-generate AI Insights"
          ) : (
            "Generate AI Insights"
          )}
        </Button>
      )}
    </div>
  );
}
