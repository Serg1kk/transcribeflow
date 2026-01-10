// components/InsightsPanel.tsx
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MindmapViewer } from "@/components/MindmapViewer";
import { Insights, InsightTemplate } from "@/lib/api";

interface InsightsPanelProps {
  insights: Insights;
  templates: InsightTemplate[];
  onRegenerate: (templateId: string) => void;
  isRegenerating: boolean;
  filename?: string;
}

type TabType = "mindmap" | "insights";

export function InsightsPanel({
  insights,
  templates,
  onRegenerate,
  isRegenerating,
  filename,
}: InsightsPanelProps) {
  const hasMindmap = insights.mindmap !== null;
  const [activeTab, setActiveTab] = useState<TabType>(hasMindmap ? "mindmap" : "insights");
  const [selectedTemplate, setSelectedTemplate] = useState(insights.metadata.template_id);

  const handleRegenerate = () => {
    onRegenerate(selectedTemplate);
  };

  // Build markdown from all insights sections
  const buildInsightsMarkdown = () => {
    let md = `# ${insights.metadata.template_name} Insights\n\n`;
    if (insights.description) {
      md += `*${insights.description}*\n\n`;
    }
    for (const section of insights.sections) {
      md += `## ${section.title}\n\n${section.content}\n\n`;
    }
    return md.trim();
  };

  const exportName = filename?.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9-_]/g, "_") || "insights";

  async function handleCopyInsightsMarkdown() {
    try {
      await navigator.clipboard.writeText(buildInsightsMarkdown());
      toast.success("Insights copied!");
    } catch {
      toast.error("Failed to copy");
    }
  }

  function handleDownloadInsightsMarkdown() {
    const blob = new Blob([buildInsightsMarkdown()], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `insights-${exportName}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const formatCost = (cost: number | null) => {
    if (cost === null) return "N/A";
    return `$${cost.toFixed(4)}`;
  };

  const formatTokens = (tokens: number) => {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  return (
    <div className="space-y-4">
      {/* Stats header */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground border-b pb-4 flex-wrap">
        <Badge variant="outline">{insights.metadata.template_name}</Badge>
        <span>•</span>
        <span>{insights.metadata.model}</span>
        <span>•</span>
        <span>
          {formatTokens(insights.stats.input_tokens)} in / {formatTokens(insights.stats.output_tokens)} out
        </span>
        <span>•</span>
        <span>{formatCost(insights.stats.cost_usd)}</span>
        <span>•</span>
        <span>{insights.stats.processing_time_seconds.toFixed(1)}s</span>
      </div>

      {/* Description */}
      {insights.description && (
        <p className="text-muted-foreground italic">{insights.description}</p>
      )}

      {/* Tabs */}
      {hasMindmap && (
        <div className="flex justify-center">
          <div className="inline-flex gap-1 p-1.5 bg-muted rounded-xl border">
            <Button
              variant={activeTab === "mindmap" ? "default" : "ghost"}
              size="default"
              onClick={() => setActiveTab("mindmap")}
              className={activeTab === "mindmap" ? "shadow-sm" : "hover:bg-background/50"}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
              </svg>
              Mindmap
            </Button>
            <Button
              variant={activeTab === "insights" ? "default" : "ghost"}
              size="default"
              onClick={() => setActiveTab("insights")}
              className={activeTab === "insights" ? "shadow-sm" : "hover:bg-background/50"}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Insights
            </Button>
          </div>
        </div>
      )}

      {/* Tab content */}
      {activeTab === "mindmap" && insights.mindmap ? (
        <MindmapViewer markdown={insights.mindmap.content} filename={filename} />
      ) : (
        <div className="space-y-6">
          {insights.sections.map((section) => (
            <div key={section.id} className="space-y-2">
              <h4 className="font-semibold text-lg">{section.title}</h4>
              <div className="prose dark:prose-invert max-w-none">
                <ReactMarkdown>{section.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {/* Copy/Download buttons */}
          <div className="flex flex-wrap gap-2 pt-4 border-t">
            <Button variant="outline" size="sm" onClick={handleCopyInsightsMarkdown}>
              Copy Markdown
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownloadInsightsMarkdown}>
              Download .md
            </Button>
          </div>
        </div>
      )}

      {/* Re-generate controls */}
      <div className="flex items-center gap-3 pt-4 border-t">
        <Select
          value={selectedTemplate}
          onValueChange={setSelectedTemplate}
          disabled={isRegenerating}
        >
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {templates.map((template) => (
              <SelectItem key={template.id} value={template.id}>
                {template.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          onClick={handleRegenerate}
          disabled={isRegenerating}
        >
          {isRegenerating ? (
            <>
              <span className="animate-spin mr-2">&#8987;</span>
              Regenerating...
            </>
          ) : (
            "Re-generate"
          )}
        </Button>
      </div>
    </div>
  );
}
