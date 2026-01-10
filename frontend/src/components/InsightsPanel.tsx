// components/InsightsPanel.tsx
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
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
}

type TabType = "mindmap" | "insights";

export function InsightsPanel({
  insights,
  templates,
  onRegenerate,
  isRegenerating,
}: InsightsPanelProps) {
  const hasMindmap = insights.mindmap !== null;
  const [activeTab, setActiveTab] = useState<TabType>(hasMindmap ? "mindmap" : "insights");
  const [selectedTemplate, setSelectedTemplate] = useState(insights.metadata.template_id);

  const handleRegenerate = () => {
    onRegenerate(selectedTemplate);
  };

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
        <div className="flex gap-1 p-1 bg-muted rounded-lg w-fit">
          <Button
            variant={activeTab === "mindmap" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("mindmap")}
          >
            Mindmap
          </Button>
          <Button
            variant={activeTab === "insights" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("insights")}
          >
            Insights
          </Button>
        </div>
      )}

      {/* Tab content */}
      {activeTab === "mindmap" && insights.mindmap ? (
        <MindmapViewer markdown={insights.mindmap.content} />
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
