// components/TranscriptPanel.tsx
"use client";

import { useRef, forwardRef, useImperativeHandle } from "react";
import { Button } from "@/components/ui/button";
import { Copy, FileText, Braces, FileJson } from "lucide-react";
import { TranscriptData, CleanedTranscript } from "@/lib/api";

interface TranscriptPanelProps {
  type: "original" | "cleaned";
  data: TranscriptData | CleanedTranscript;
  segmentCount: number;
  engine?: string; // For showing Raw API button
  onCopyTxt: () => void;
  onDownloadTxt: () => void;
  onCopyJson?: () => void;
  onDownloadJson?: () => void;
  onCopyRaw?: () => void;
  onDownloadRaw?: () => void;
  onVisibleTimestampChange?: (timestamp: number) => void;
}

export interface TranscriptPanelRef {
  scrollToTimestamp: (timestamp: number) => void;
  getContainer: () => HTMLDivElement | null;
}

export const TranscriptPanel = forwardRef<TranscriptPanelRef, TranscriptPanelProps>(
  function TranscriptPanel(
    {
      type,
      data,
      segmentCount,
      engine,
      onCopyTxt,
      onDownloadTxt,
      onCopyJson,
      onDownloadJson,
      onCopyRaw,
      onDownloadRaw,
      onVisibleTimestampChange,
    },
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const segmentRefs = useRef<Map<number, HTMLDivElement>>(new Map());

    useImperativeHandle(ref, () => ({
      scrollToTimestamp: (timestamp: number) => {
        const segments = "segments" in data ? data.segments : [];
        // Binary search for nearest timestamp
        let left = 0;
        let right = segments.length - 1;
        let nearest = 0;

        while (left <= right) {
          const mid = Math.floor((left + right) / 2);
          const midTime = segments[mid].start;

          if (midTime === timestamp) {
            nearest = mid;
            break;
          } else if (midTime < timestamp) {
            nearest = mid;
            left = mid + 1;
          } else {
            right = mid - 1;
          }
        }

        const element = segmentRefs.current.get(nearest);
        if (element) {
          element.scrollIntoView({ block: "start", behavior: "auto" });
        }
      },
      getContainer: () => containerRef.current,
    }));

    function formatTimestamp(seconds: number): string {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const secs = Math.floor(seconds % 60);
      return `${hours.toString().padStart(2, "0")}:${minutes
        .toString()
        .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    }

    const handleScroll = () => {
      if (!onVisibleTimestampChange || !containerRef.current) return;

      const container = containerRef.current;
      const containerTop = container.getBoundingClientRect().top;

      // Find first visible segment
      let firstVisibleTimestamp: number | null = null;
      const segments = "segments" in data ? data.segments : [];

      for (let i = 0; i < segments.length; i++) {
        const element = segmentRefs.current.get(i);
        if (element) {
          const rect = element.getBoundingClientRect();
          if (rect.top >= containerTop - 10) {
            firstVisibleTimestamp = segments[i].start;
            break;
          }
        }
      }

      if (firstVisibleTimestamp !== null) {
        onVisibleTimestampChange(firstVisibleTimestamp);
      }
    };

    const segments = "segments" in data ? data.segments : [];
    const speakers = "speakers" in data ? data.speakers : {};
    const isCloud = engine && engine !== "mlx-whisper";
    const title = type === "original" ? "Original" : "Cleaned";

    return (
      <div className="space-y-2">
        {/* Header with buttons */}
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-sm text-muted-foreground">
            {title} ({segmentCount} segments)
          </h3>
          <div className="flex items-center gap-1">
            {/* TXT group */}
            <span className="text-xs text-muted-foreground mr-1">TXT</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onCopyTxt}
              title="Copy as text"
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onDownloadTxt}
              title="Download .txt"
            >
              <FileText className="h-3.5 w-3.5" />
            </Button>

            {/* JSON group - only for original */}
            {type === "original" && onCopyJson && onDownloadJson && (
              <>
                <div className="w-px h-4 bg-border mx-1" />
                <span className="text-xs text-muted-foreground mr-1">JSON</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onCopyJson}
                  title="Copy JSON"
                >
                  <Copy className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onDownloadJson}
                  title="Download .json"
                >
                  <Braces className="h-3.5 w-3.5" />
                </Button>
              </>
            )}

            {/* Raw API - only for cloud engines */}
            {type === "original" && isCloud && onCopyRaw && onDownloadRaw && (
              <>
                <div className="w-px h-4 bg-border mx-1" />
                <span className="text-xs text-muted-foreground mr-1">Raw</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onCopyRaw}
                  title="Copy raw API response"
                >
                  <Copy className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onDownloadRaw}
                  title="Download raw API response"
                >
                  <FileJson className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Scrollable content */}
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="h-[600px] overflow-y-auto border rounded-lg p-4 space-y-3"
        >
          {segments.map((segment, index) => {
            const speaker = speakers[segment.speaker];
            return (
              <div
                key={index}
                ref={(el) => {
                  if (el) segmentRefs.current.set(index, el);
                }}
                data-timestamp={segment.start}
                className="flex gap-2 text-sm"
              >
                <span className="text-muted-foreground shrink-0 w-20">
                  [{formatTimestamp(segment.start)}]
                </span>
                <span
                  className="font-medium shrink-0 w-28 min-w-20"
                  style={{ color: speaker?.color, overflowWrap: "anywhere" }}
                  title={speaker?.name || segment.speaker}
                >
                  {speaker?.name || segment.speaker}:
                </span>
                <span className={type === "original" ? "text-muted-foreground" : ""}>
                  {segment.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }
);
