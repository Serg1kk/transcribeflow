// components/TranscriptComparison.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { CleanedTranscript, TranscriptData } from "@/lib/api";

interface TranscriptComparisonProps {
  original: TranscriptData;
  cleaned: CleanedTranscript;
}

export function TranscriptComparison({
  original,
  cleaned,
}: TranscriptComparisonProps) {
  const [syncScroll, setSyncScroll] = useState(true);
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  const isScrolling = useRef(false);

  // Sync scroll between panels
  useEffect(() => {
    if (!syncScroll) return;

    const handleScroll = (source: HTMLDivElement, target: HTMLDivElement) => {
      if (isScrolling.current) return;
      isScrolling.current = true;

      const scrollRatio =
        source.scrollTop / (source.scrollHeight - source.clientHeight);
      target.scrollTop =
        scrollRatio * (target.scrollHeight - target.clientHeight);

      requestAnimationFrame(() => {
        isScrolling.current = false;
      });
    };

    const leftEl = leftRef.current;
    const rightEl = rightRef.current;

    if (!leftEl || !rightEl) return;

    const onLeftScroll = () => handleScroll(leftEl, rightEl);
    const onRightScroll = () => handleScroll(rightEl, leftEl);

    leftEl.addEventListener("scroll", onLeftScroll);
    rightEl.addEventListener("scroll", onRightScroll);

    return () => {
      leftEl.removeEventListener("scroll", onLeftScroll);
      rightEl.removeEventListener("scroll", onRightScroll);
    };
  }, [syncScroll]);

  function formatTimestamp(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, "0")}:${minutes
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }

  function formatTokens(tokens: number): string {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  }

  return (
    <div className="space-y-4">
      {/* Header with stats */}
      <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={syncScroll}
              onChange={(e) => setSyncScroll(e.target.checked)}
              className="rounded"
            />
            Sync scroll
          </label>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>
            Cleaned with <strong>{cleaned.metadata.template}</strong>
          </span>
          <span>{cleaned.metadata.model}</span>
          <span>
            {formatTokens(cleaned.stats.input_tokens)}/
            {formatTokens(cleaned.stats.output_tokens)} tokens
          </span>
          {cleaned.stats.cost_usd !== null && (
            <span className="font-medium">
              ${cleaned.stats.cost_usd.toFixed(3)}
            </span>
          )}
        </div>
      </div>

      {/* Side-by-side panels */}
      <div className="grid grid-cols-2 gap-4">
        {/* Original */}
        <div className="space-y-2">
          <h3 className="font-medium text-sm text-muted-foreground">
            Original ({original.segments.length} segments)
          </h3>
          <div
            ref={leftRef}
            className="h-[600px] overflow-y-auto border rounded-lg p-4 space-y-3"
          >
            {original.segments.map((segment, index) => {
              const speaker = original.speakers[segment.speaker];
              return (
                <div key={index} className="flex gap-2 text-sm">
                  <span className="text-muted-foreground shrink-0 w-20">
                    [{formatTimestamp(segment.start)}]
                  </span>
                  <span
                    className="font-medium shrink-0 w-24"
                    style={{ color: speaker?.color }}
                  >
                    {speaker?.name || segment.speaker}:
                  </span>
                  <span className="text-muted-foreground">{segment.text}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cleaned */}
        <div className="space-y-2">
          <h3 className="font-medium text-sm text-muted-foreground">
            Cleaned ({cleaned.stats.cleaned_segments} segments)
          </h3>
          <div
            ref={rightRef}
            className="h-[600px] overflow-y-auto border rounded-lg p-4 space-y-3"
          >
            {cleaned.segments.map((segment, index) => {
              const speaker = cleaned.speakers[segment.speaker];
              return (
                <div key={index} className="flex gap-2 text-sm">
                  <span className="text-muted-foreground shrink-0 w-20">
                    [{formatTimestamp(segment.start)}]
                  </span>
                  <span
                    className="font-medium shrink-0 w-24"
                    style={{ color: speaker?.color }}
                  >
                    {speaker?.name || segment.speaker}:
                  </span>
                  <span>{segment.text}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
