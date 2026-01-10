// components/MindmapViewer.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

interface MindmapViewerProps {
  markdown: string;
  className?: string;
}

export function MindmapViewer({ markdown, className = "" }: MindmapViewerProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const markmapRef = useRef<Markmap | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!svgRef.current || !markdown) return;

    const transformer = new Transformer();
    const { root } = transformer.transform(markdown);

    if (markmapRef.current) {
      markmapRef.current.setData(root);
    } else {
      markmapRef.current = Markmap.create(svgRef.current, {
        autoFit: true,
        duration: 500,
        maxWidth: 300,
      }, root);
    }

    setIsReady(true);

    return () => {
      // Cleanup if needed
    };
  }, [markdown]);

  async function handleCopyMarkdown() {
    try {
      await navigator.clipboard.writeText(markdown);
      toast.success("Markdown copied!");
    } catch {
      toast.error("Failed to copy");
    }
  }

  async function handleCopyJson() {
    try {
      const json = JSON.stringify({ format: "markdown", content: markdown }, null, 2);
      await navigator.clipboard.writeText(json);
      toast.success("JSON copied!");
    } catch {
      toast.error("Failed to copy");
    }
  }

  function handleDownloadMarkdown() {
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mindmap.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className={className}>
      <div className="border rounded-lg bg-white dark:bg-gray-900 p-4 min-h-[400px] overflow-hidden">
        <svg
          ref={svgRef}
          className="w-full h-[400px]"
          style={{ minWidth: "100%" }}
        />
      </div>

      {isReady && (
        <div className="flex gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={handleCopyMarkdown}>
            Copy Markdown
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopyJson}>
            Copy JSON
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadMarkdown}>
            Download .md
          </Button>
        </div>
      )}
    </div>
  );
}
