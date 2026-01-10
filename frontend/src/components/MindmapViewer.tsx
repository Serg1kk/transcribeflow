// components/MindmapViewer.tsx
"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

interface MindmapViewerProps {
  markdown: string;
  className?: string;
  filename?: string;  // Original audio filename for export naming
}

export function MindmapViewer({ markdown, className = "", filename = "mindmap" }: MindmapViewerProps) {
  // Clean filename for export (remove extension, sanitize)
  const exportName = filename.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9-_]/g, "_");
  const svgRef = useRef<SVGSVGElement>(null);
  const fullscreenSvgRef = useRef<SVGSVGElement>(null);
  const markmapRef = useRef<Markmap | null>(null);
  const fullscreenMarkmapRef = useRef<Markmap | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoom, setZoom] = useState(1);

  const initMarkmapOnSvg = useCallback((svgElement: SVGSVGElement, markmapRefObj: React.MutableRefObject<Markmap | null>) => {
    const rect = svgElement.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) {
      requestAnimationFrame(() => initMarkmapOnSvg(svgElement, markmapRefObj));
      return;
    }

    const transformer = new Transformer();
    const { root } = transformer.transform(markdown);

    if (markmapRefObj.current) {
      markmapRefObj.current.setData(root);
    } else {
      try {
        markmapRefObj.current = Markmap.create(svgElement, {
          autoFit: true,
          duration: 500,
          maxWidth: 300,
        }, root);
      } catch (error) {
        console.warn("Markmap init error, retrying:", error);
        setTimeout(() => initMarkmapOnSvg(svgElement, markmapRefObj), 100);
        return;
      }
    }
  }, [markdown]);

  useEffect(() => {
    if (!svgRef.current || !markdown) return;
    requestAnimationFrame(() => {
      if (svgRef.current) {
        initMarkmapOnSvg(svgRef.current, markmapRef);
        setIsReady(true);
      }
    });

    // Cleanup when component unmounts (e.g., switching tabs)
    return () => {
      if (markmapRef.current) {
        try {
          markmapRef.current.destroy();
        } catch {
          // Ignore cleanup errors
        }
        markmapRef.current = null;
      }
    };
  }, [markdown, initMarkmapOnSvg]);

  // Initialize fullscreen markmap when opened, cleanup when closed
  useEffect(() => {
    if (isFullscreen && fullscreenSvgRef.current && markdown) {
      fullscreenMarkmapRef.current = null; // Reset to create new instance
      requestAnimationFrame(() => {
        if (fullscreenSvgRef.current) {
          initMarkmapOnSvg(fullscreenSvgRef.current, fullscreenMarkmapRef);
        }
      });
    }

    // Cleanup when closing fullscreen
    return () => {
      if (fullscreenMarkmapRef.current) {
        try {
          fullscreenMarkmapRef.current.destroy();
        } catch {
          // Ignore cleanup errors
        }
        fullscreenMarkmapRef.current = null;
      }
    };
  }, [isFullscreen, markdown, initMarkmapOnSvg]);

  // Handle Escape key for fullscreen
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isFullscreen]);

  const handleZoomIn = () => {
    const mm = isFullscreen ? fullscreenMarkmapRef.current : markmapRef.current;
    if (mm) {
      const newZoom = Math.min(zoom * 1.3, 5);
      setZoom(newZoom);
      mm.rescale(newZoom);
    }
  };

  const handleZoomOut = () => {
    const mm = isFullscreen ? fullscreenMarkmapRef.current : markmapRef.current;
    if (mm) {
      const newZoom = Math.max(zoom / 1.3, 0.2);
      setZoom(newZoom);
      mm.rescale(newZoom);
    }
  };

  const handleFit = () => {
    const mm = isFullscreen ? fullscreenMarkmapRef.current : markmapRef.current;
    if (mm) {
      setZoom(1);
      mm.fit();
    }
  };

  async function handleCopyMarkdown() {
    try {
      await navigator.clipboard.writeText(markdown);
      toast.success("Markdown copied!");
    } catch {
      toast.error("Failed to copy");
    }
  }

  function handleDownloadMarkdown() {
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mindmap-${exportName}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function svgToPng(svgElement: SVGSVGElement): Promise<Blob> {
    // Clone SVG to avoid modifying the original
    const clonedSvg = svgElement.cloneNode(true) as SVGSVGElement;

    // Set explicit dimensions
    const rect = svgElement.getBoundingClientRect();
    clonedSvg.setAttribute("width", String(rect.width));
    clonedSvg.setAttribute("height", String(rect.height));

    // Add white background
    const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bgRect.setAttribute("width", "100%");
    bgRect.setAttribute("height", "100%");
    bgRect.setAttribute("fill", "white");
    clonedSvg.insertBefore(bgRect, clonedSvg.firstChild);

    // Serialize with proper encoding
    const svgData = new XMLSerializer().serializeToString(clonedSvg);
    const encodedSvg = encodeURIComponent(svgData);
    const dataUrl = `data:image/svg+xml;charset=utf-8,${encodedSvg}`;

    return new Promise((resolve, reject) => {
      const img = new window.Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        const canvas = document.createElement("canvas");
        const scale = 2; // Higher resolution
        canvas.width = rect.width * scale;
        canvas.height = rect.height * scale;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Failed to get canvas context"));
          return;
        }
        ctx.scale(scale, scale);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          if (blob) resolve(blob);
          else reject(new Error("Failed to create blob"));
        }, "image/png");
      };
      img.onerror = () => reject(new Error("Failed to load SVG"));
      img.src = dataUrl;
    });
  }

  async function handleDownloadPng() {
    const mm = isFullscreen ? fullscreenMarkmapRef.current : markmapRef.current;
    const svgElement = isFullscreen ? fullscreenSvgRef.current : svgRef.current;
    if (!svgElement || !mm) return;
    try {
      // Fit to show full content before export
      mm.fit();
      // Wait for animation to complete
      await new Promise(resolve => setTimeout(resolve, 600));

      const blob = await svgToPng(svgElement);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mindmap-${exportName}.png`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PNG downloaded!");
    } catch {
      toast.error("Failed to export PNG");
    }
  }

  async function handleCopyPng() {
    const mm = isFullscreen ? fullscreenMarkmapRef.current : markmapRef.current;
    const svgElement = isFullscreen ? fullscreenSvgRef.current : svgRef.current;
    if (!svgElement || !mm) return;
    try {
      // Fit to show full content before export
      mm.fit();
      // Wait for animation to complete
      await new Promise(resolve => setTimeout(resolve, 600));

      const blob = await svgToPng(svgElement);
      await navigator.clipboard.write([
        new ClipboardItem({ "image/png": blob })
      ]);
      toast.success("PNG copied to clipboard!");
    } catch {
      toast.error("Failed to copy PNG");
    }
  }

  return (
    <div className={className}>
      <div className="relative border rounded-lg bg-white dark:bg-gray-900 p-4 min-h-[400px] overflow-hidden">
        {/* Zoom controls - top left */}
        <div className="absolute top-2 left-2 z-10 flex gap-1">
          <Button variant="outline" size="sm" onClick={handleZoomOut} className="w-8 h-8 p-0">
            -
          </Button>
          <Button variant="outline" size="sm" onClick={handleFit} className="h-8 px-2 text-xs">
            Fit
          </Button>
          <Button variant="outline" size="sm" onClick={handleZoomIn} className="w-8 h-8 p-0">
            +
          </Button>
        </div>

        {/* Fullscreen button - top right */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsFullscreen(true)}
          className="absolute top-2 right-2 z-10"
        >
          Fullscreen
        </Button>

        <svg
          ref={svgRef}
          className="w-full h-[400px]"
          style={{ minWidth: "100%" }}
        />
      </div>

      {isReady && (
        <div className="flex flex-wrap gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={handleCopyPng}>
            Copy PNG
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadPng}>
            Download PNG
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopyMarkdown}>
            Copy Markdown
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadMarkdown}>
            Download .md
          </Button>
        </div>
      )}

      {/* Fullscreen modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-white dark:bg-gray-900 flex flex-col">
          {/* Header with controls */}
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleZoomOut} className="w-8 h-8 p-0">
                -
              </Button>
              <Button variant="outline" size="sm" onClick={handleFit} className="h-8 px-2">
                Fit
              </Button>
              <Button variant="outline" size="sm" onClick={handleZoomIn} className="w-8 h-8 p-0">
                +
              </Button>
            </div>
            <span className="text-sm text-muted-foreground">Press Escape to exit</span>
            <Button variant="outline" size="sm" onClick={() => setIsFullscreen(false)}>
              Close
            </Button>
          </div>

          {/* Fullscreen SVG */}
          <div className="flex-1 overflow-hidden p-4">
            <svg
              ref={fullscreenSvgRef}
              className="w-full h-full"
              style={{ minWidth: "100%", minHeight: "100%" }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
