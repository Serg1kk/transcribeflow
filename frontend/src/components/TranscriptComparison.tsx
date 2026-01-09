// components/TranscriptComparison.tsx
"use client";

import { useState, useRef } from "react";
import { CleanedTranscript, TranscriptData } from "@/lib/api";
import {
  TranscriptPanel,
  TranscriptPanelRef,
} from "@/components/TranscriptPanel";
import * as api from "@/lib/api";

interface TranscriptComparisonProps {
  original: TranscriptData;
  cleaned: CleanedTranscript;
  transcriptionId: string;
  engine: string;
}

export function TranscriptComparison({
  original,
  cleaned,
  transcriptionId,
  engine,
}: TranscriptComparisonProps) {
  const [syncScroll, setSyncScroll] = useState(true);
  const leftRef = useRef<TranscriptPanelRef>(null);
  const rightRef = useRef<TranscriptPanelRef>(null);
  const isScrolling = useRef(false);

  function formatTokens(tokens: number): string {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  }

  const handleLeftTimestampChange = (timestamp: number) => {
    if (!syncScroll || isScrolling.current) return;
    isScrolling.current = true;
    rightRef.current?.scrollToTimestamp(timestamp);
    setTimeout(() => {
      isScrolling.current = false;
    }, 100);
  };

  const handleRightTimestampChange = (timestamp: number) => {
    if (!syncScroll || isScrolling.current) return;
    isScrolling.current = true;
    leftRef.current?.scrollToTimestamp(timestamp);
    setTimeout(() => {
      isScrolling.current = false;
    }, 100);
  };

  // Copy/Download handlers for Original
  const handleCopyOriginalTxt = async () => {
    try {
      await api.copyOriginalTxt(transcriptionId);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadOriginalTxt = () => {
    window.open(api.getOriginalTxtUrl(transcriptionId), "_blank");
  };

  const handleCopyOriginalJson = async () => {
    try {
      await api.copyOriginalJson(transcriptionId);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadOriginalJson = () => {
    window.open(api.getOriginalJsonUrl(transcriptionId), "_blank");
  };

  const handleCopyRaw = async () => {
    try {
      await api.copyRawApi(transcriptionId);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadRaw = () => {
    window.open(api.getRawApiUrl(transcriptionId), "_blank");
  };

  // Copy/Download handlers for Cleaned
  const handleCopyCleanedTxt = async () => {
    try {
      await api.copyCleanedTxt(transcriptionId);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadCleanedTxt = () => {
    window.open(api.getCleanedTxtUrl(transcriptionId), "_blank");
  };

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
        <TranscriptPanel
          ref={leftRef}
          type="original"
          data={original}
          segmentCount={original.segments.length}
          engine={engine}
          onCopyTxt={handleCopyOriginalTxt}
          onDownloadTxt={handleDownloadOriginalTxt}
          onCopyJson={handleCopyOriginalJson}
          onDownloadJson={handleDownloadOriginalJson}
          onCopyRaw={handleCopyRaw}
          onDownloadRaw={handleDownloadRaw}
          onVisibleTimestampChange={handleLeftTimestampChange}
        />

        <TranscriptPanel
          ref={rightRef}
          type="cleaned"
          data={cleaned}
          segmentCount={cleaned.stats.cleaned_segments}
          onCopyTxt={handleCopyCleanedTxt}
          onDownloadTxt={handleDownloadCleanedTxt}
          onVisibleTimestampChange={handleRightTimestampChange}
        />
      </div>
    </div>
  );
}
