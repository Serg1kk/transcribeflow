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

    // Wait for SVG to be properly laid out before initializing Markmap
    // D3 zoom requires the SVG to have computed dimensions
    const initMarkmap = () => {
      if (!svgRef.current) return;

      const rect = svgRef.current.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        // SVG not ready yet, retry after a short delay
        requestAnimationFrame(initMarkmap);
        return;
      }

      const transformer = new Transformer();
      const { root } = transformer.transform(markdown);

      if (markmapRef.current) {
        markmapRef.current.setData(root);
      } else {
        try {
          markmapRef.current = Markmap.create(svgRef.current, {
            autoFit: true,
            duration: 500,
            maxWidth: 300,
          }, root);
        } catch (error) {
          console.warn("Markmap init error, retrying:", error);
          // Retry once more after a delay
          setTimeout(initMarkmap, 100);
          return;
        }
      }

      setIsReady(true);
    };

    // Use requestAnimationFrame to ensure DOM is ready
    requestAnimationFrame(initMarkmap);

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
