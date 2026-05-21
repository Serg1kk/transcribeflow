'use client';

import { useEffect, useRef, forwardRef, useImperativeHandle, useState } from "react";
import { useIntl } from "react-intl";
import { Button } from "@/components/ui/button";
import { Copy, FileText, Braces, FileJson, Pause, Play, Square } from "lucide-react";
import { TranscriptData, CleanedTranscript, getOriginalAudioUrl } from "@/lib/api";

interface TranscriptPanelProps {
  type: "original" | "cleaned";
  transcriptionId: string;
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
      transcriptionId,
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
    const intl = useIntl();
    const containerRef = useRef<HTMLDivElement>(null);
    const segmentRefs = useRef<Map<number, HTMLDivElement>>(new Map());
    const audioRef = useRef<HTMLAudioElement>(null);
    const audioUrl = getOriginalAudioUrl(transcriptionId);
    const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);

    useEffect(() => {
      const audio = audioRef.current;
      return () => {
        audio?.pause();
      };
    }, []);

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
    const title = type === "original"
      ? intl.formatMessage({ id: 'transcription.panel.title.original' })
      : intl.formatMessage({ id: 'transcription.panel.title.cleaned' });

    // Speaker filter state
    const [filterSpeaker, setFilterSpeaker] = useState<string | null>(null);

    const ensureAudioMetadata = async (audio: HTMLAudioElement) => {
      if (audio.readyState >= 1) return;

      await new Promise<void>((resolve, reject) => {
        const handleLoaded = () => {
          cleanup();
          resolve();
        };
        const handleError = () => {
          cleanup();
          reject(audio.error || new Error("Failed to load audio metadata"));
        };
        const cleanup = () => {
          audio.removeEventListener("loadedmetadata", handleLoaded);
          audio.removeEventListener("error", handleError);
        };

        audio.addEventListener("loadedmetadata", handleLoaded);
        audio.addEventListener("error", handleError);
        audio.load();
      });
    };

    const seekAudioTo = async (audio: HTMLAudioElement, targetTime: number) => {
      const safeTarget = Math.max(0, targetTime);

      if (Math.abs(audio.currentTime - safeTarget) < 0.25) {
        return;
      }

      await new Promise<void>((resolve, reject) => {
        const handleSeeked = () => {
          cleanup();
          resolve();
        };
        const handleError = () => {
          cleanup();
          reject(audio.error || new Error("Failed to seek audio"));
        };
        const cleanup = () => {
          audio.removeEventListener("seeked", handleSeeked);
          audio.removeEventListener("error", handleError);
        };

        audio.addEventListener("seeked", handleSeeked, { once: true });
        audio.addEventListener("error", handleError, { once: true });

        if (typeof audio.fastSeek === "function") {
          audio.fastSeek(safeTarget);
        } else {
          audio.currentTime = safeTarget;
        }

        window.setTimeout(() => {
          cleanup();
          resolve();
        }, 1200);
      });
    };

    const handlePlayToggle = async (segmentStart: number, index: number) => {
      const audio = audioRef.current;
      if (!audio) return;

      if (activeSegmentIndex === index && !audio.paused) {
        audio.pause();
        return;
      }

      try {
        await ensureAudioMetadata(audio);
        audio.pause();
        await seekAudioTo(audio, segmentStart);
        await audio.play();
        setActiveSegmentIndex(index);
        setIsPlaying(true);
      } catch (error) {
        console.error("Failed to play audio:", error);
      }
    };

    const handleStop = (segmentStart: number) => {
      const audio = audioRef.current;
      if (!audio) return;

      audio.pause();
      audio.currentTime = segmentStart;
      setIsPlaying(false);
      setActiveSegmentIndex(null);
    };

    // Calculate speaker stats by character count
    const speakerCharCount: Record<string, number> = {};
    let totalChars = 0;
    for (const seg of segments) {
      const len = seg.text.length;
      speakerCharCount[seg.speaker] = (speakerCharCount[seg.speaker] || 0) + len;
      totalChars += len;
    }
    const speakerStats = Object.entries(speakerCharCount)
      .sort(([, a], [, b]) => b - a)
      .map(([speakerId, chars]) => {
        const speaker = speakers[speakerId];
        return {
          id: speakerId,
          name: speaker?.name || speakerId,
          color: speaker?.color || undefined,
          pct: totalChars > 0 ? Math.round((chars / totalChars) * 100) : 0,
        };
      });

    const toggleFilter = (speakerId: string) => {
      setFilterSpeaker(prev => prev === speakerId ? null : speakerId);
    };

    return (
      <div className="space-y-2">
        {/* Header with buttons */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap">
            <h3 className="font-medium text-sm text-muted-foreground">
              {intl.formatMessage({ id: 'transcription.panel.segments' }, { title, count: segmentCount })}
            </h3>
            {/* Speaker stats */}
            {speakerStats.length > 1 && (
              <div className="flex items-center gap-2 text-xs">
                {speakerStats.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => toggleFilter(s.id)}
                    className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded transition-colors cursor-pointer border ${
                      filterSpeaker === s.id
                        ? "bg-muted border-foreground/20"
                        : "border-transparent hover:bg-muted/50"
                    }`}
                    title={`Filter: ${s.name} (${s.pct}%)`}
                  >
                    <span
                      className="inline-block w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: s.color || '#888' }}
                    />
                    <span style={{ color: s.color }}>{s.name}</span>
                    <span className="text-muted-foreground">{s.pct}%</span>
                  </button>
                ))}
                {filterSpeaker && (
                  <button
                    onClick={() => setFilterSpeaker(null)}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded transition-colors cursor-pointer border border-transparent hover:bg-muted/50 text-muted-foreground"
                    title="Show all speakers"
                  >
                    ✕ All
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1">
            {/* TXT group */}
            <span className="text-xs text-muted-foreground mr-1">{intl.formatMessage({ id: 'transcription.export.txt' })}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onCopyTxt}
              title={intl.formatMessage({ id: 'transcription.export.copyText' })}
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onDownloadTxt}
              title={intl.formatMessage({ id: 'transcription.export.downloadTxt' })}
            >
              <FileText className="h-3.5 w-3.5" />
            </Button>

            {/* JSON group - only for original */}
            {type === "original" && onCopyJson && onDownloadJson && (
              <>
                <div className="w-px h-4 bg-border mx-1" />
                <span className="text-xs text-muted-foreground mr-1">{intl.formatMessage({ id: 'transcription.export.json' })}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onCopyJson}
                  title={intl.formatMessage({ id: 'transcription.export.copyJson' })}
                >
                  <Copy className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onDownloadJson}
                  title={intl.formatMessage({ id: 'transcription.export.downloadJson' })}
                >
                  <Braces className="h-3.5 w-3.5" />
                </Button>
              </>
            )}

            {/* Raw API - only for cloud engines */}
            {type === "original" && isCloud && onCopyRaw && onDownloadRaw && (
              <>
                <div className="w-px h-4 bg-border mx-1" />
                <span className="text-xs text-muted-foreground mr-1">{intl.formatMessage({ id: 'transcription.export.raw' })}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onCopyRaw}
                  title={intl.formatMessage({ id: 'transcription.export.copyRaw' })}
                >
                  <Copy className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onDownloadRaw}
                  title={intl.formatMessage({ id: 'transcription.export.downloadRaw' })}
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
          <audio
            ref={audioRef}
            src={audioUrl}
            preload="none"
            onPause={() => setIsPlaying(false)}
            onPlay={() => setIsPlaying(true)}
            onEnded={() => {
              setIsPlaying(false);
              setActiveSegmentIndex(null);
            }}
          />
          {segments.map((segment, index) => {
            const speaker = speakers[segment.speaker];
            if (filterSpeaker && segment.speaker !== filterSpeaker) return null;

            const isActive = activeSegmentIndex === index;
            const isActiveAndPlaying = isActive && isPlaying;

            return (
              <div
                key={index}
                ref={(el) => {
                  if (el) segmentRefs.current.set(index, el);
                }}
                data-timestamp={segment.start}
                className={`flex gap-2 text-sm items-start rounded-md px-2 py-1 ${isActive ? "bg-muted/50" : ""}`}
              >
                <div className="shrink-0 w-16 flex items-center gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => handlePlayToggle(segment.start, index)}
                    title={isActiveAndPlaying ? "Pause audio" : `Play from ${formatTimestamp(segment.start)}`}
                  >
                    {isActiveAndPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                  </Button>
                  {isActive && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => handleStop(segment.start)}
                      title="Stop audio"
                    >
                      <Square className="h-3 w-3" />
                    </Button>
                  )}
                </div>
                <span className="text-muted-foreground shrink-0 w-20 pt-1">
                  [{formatTimestamp(segment.start)}]
                </span>
                <span
                  className="font-medium shrink-0 w-28 min-w-20 pt-1"
                  style={{ color: speaker?.color, overflowWrap: "anywhere" }}
                  title={speaker?.name || segment.speaker}
                >
                  {speaker?.name || segment.speaker}:
                </span>
                <span className={`${type === "original" ? "text-muted-foreground" : ""} pt-1`}>
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
