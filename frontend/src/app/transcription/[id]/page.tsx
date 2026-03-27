// app/transcription/[id]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useIntl } from "react-intl";
import { toast } from "sonner";
import { Header } from "@/components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SpeakerEditor } from "@/components/SpeakerEditor";
import { PostProcessingControls } from "@/components/PostProcessingControls";
import { TranscriptComparison } from "@/components/TranscriptComparison";
import { TranscriptPanel } from "@/components/TranscriptPanel";
import { InsightsControls } from "@/components/InsightsControls";
import { InsightsPanel } from "@/components/InsightsPanel";
import {
  getTranscriptionDetail,
  getTranscriptData,
  getCleanedTranscript,
  checkCleanedExists,
  getInsights,
  listInsights,
  identifySpeakers,
  TranscriptionDetail,
  TranscriptData,
  CleanedTranscript,
  Insights,
} from "@/lib/api";
import * as api from "@/lib/api";

type ViewMode = "cleaned" | "original" | "comparison";

export default function TranscriptionPage() {
  const params = useParams();
  const id = params.id as string;
  const intl = useIntl();

  const [transcription, setTranscription] = useState<TranscriptionDetail | null>(null);
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  const [cleanedTranscript, setCleanedTranscript] = useState<CleanedTranscript | null>(null);
  const [hasCleanedVersion, setHasCleanedVersion] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("original");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestionsKey, setSuggestionsKey] = useState(0);

  // AI Insights state
  const [insights, setInsights] = useState<Insights | null>(null);
  const [hasInsights, setHasInsights] = useState(false);

  // Template sync state
  const [cleaningTemplateId, setCleaningTemplateId] = useState<string>("");

  // Identify speakers state
  const [isIdentifyingSpeakers, setIsIdentifyingSpeakers] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [detail, data] = await Promise.all([
          getTranscriptionDetail(id),
          getTranscriptData(id),
        ]);
        setTranscription(detail);
        setTranscript(data);

        // Check if cleaned version exists
        const cleanedExists = await checkCleanedExists(id);
        setHasCleanedVersion(cleanedExists);

        if (cleanedExists) {
          const cleaned = await getCleanedTranscript(id);
          setCleanedTranscript(cleaned);
          setViewMode("cleaned"); // Default to cleaned if exists
        }

        // Load AI Insights
        try {
          const insightsList = await listInsights(id);
          if (insightsList.length > 0) {
            setHasInsights(true);
            const latestInsights = await getInsights(id, insightsList[0].template_id);
            setInsights(latestInsights);
          }
        } catch (insightErr) {
          console.error("Failed to load insights:", insightErr);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error loading");
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, [id]);

  if (isLoading) {
    return (
      <main className="container mx-auto py-8 px-4 max-w-4xl">
        <p>{intl.formatMessage({ id: "status.loading" })}</p>
      </main>
    );
  }

  if (error || !transcription || !transcript) {
    return (
      <main className="container mx-auto py-8 px-4 max-w-4xl">
        <p className="text-destructive">{error || intl.formatMessage({ id: "transcription.notFound" })}</p>
        <Link href="/" className="text-primary hover:underline">
          ← Back
        </Link>
      </main>
    );
  }

  const handleSpeakersUpdate = (
    newSpeakers: Record<string, { name: string; color: string }>
  ) => {
    setTranscript((prev) =>
      prev ? { ...prev, speakers: newSpeakers } : prev
    );
    // Also update cleaned transcript speakers
    if (cleanedTranscript) {
      setCleanedTranscript((prev) =>
        prev ? { ...prev, speakers: newSpeakers } : prev
      );
    }
  };

  const handleProcessingComplete = async () => {
    try {
      // Small delay to ensure all files are written (suggestions.json may be written after cleaned.json)
      await new Promise((resolve) => setTimeout(resolve, 500));
      const cleaned = await getCleanedTranscript(id);
      setCleanedTranscript(cleaned);
      setHasCleanedVersion(true);
      setViewMode("cleaned");
      // Trigger SpeakerEditor to refetch suggestions
      setSuggestionsKey((prev) => prev + 1);
    } catch (err) {
      console.error("Failed to load cleaned transcript:", err);
    }
  };

  // AI Insights handlers
  const handleInsightsComplete = async (templateId: string) => {
    try {
      const insightsData = await getInsights(id, templateId);
      setInsights(insightsData);
      setHasInsights(true);
    } catch (err) {
      console.error("Failed to load insights:", err);
    }
  };

  // Check if this is a cloud engine (not local mlx-whisper)
  const isCloudEngine = transcription?.engine !== "mlx-whisper";

  // Identify speakers handler
  const handleIdentifySpeakers = async () => {
    setIsIdentifyingSpeakers(true);
    try {
      const startTime = new Date().toISOString();
      await identifySpeakers(id);

      // Poll for completion
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      let pollCount = 0;
      const maxPolls = 300;

      const pollInterval = setInterval(async () => {
        pollCount++;
        try {
          const opsResponse = await fetch(
            `${API_BASE}/api/postprocess/operations?transcription_id=${id}&limit=1&_t=${Date.now()}`
          );
          if (opsResponse.ok) {
            const ops = await opsResponse.json();
            if (ops.length > 0) {
              const latestOp = ops[0];
              if (latestOp.created_at >= startTime && latestOp.template_id === "identify-speakers") {
                if (latestOp.status === "success") {
                  clearInterval(pollInterval);
                  setIsIdentifyingSpeakers(false);
                  setSuggestionsKey((prev) => prev + 1);
                  return;
                } else if (latestOp.status === "failed") {
                  clearInterval(pollInterval);
                  setIsIdentifyingSpeakers(false);
                  return;
                }
              }
            }
          }
          if (pollCount >= maxPolls) {
            clearInterval(pollInterval);
            setIsIdentifyingSpeakers(false);
          }
        } catch {
          // Network error, keep polling
        }
      }, 2000);
    } catch {
      setIsIdentifyingSpeakers(false);
    }
  };

  // Copy/Download handlers
  const handleCopyOriginalTxt = async () => {
    try {
      await api.copyOriginalTxt(id);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadOriginalTxt = () => {
    window.open(api.getOriginalTxtUrl(id), "_blank");
  };

  const handleCopyOriginalJson = async () => {
    try {
      await api.copyOriginalJson(id);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadOriginalJson = () => {
    window.open(api.getOriginalJsonUrl(id), "_blank");
  };

  const handleCopyRaw = async () => {
    try {
      await api.copyRawApi(id);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadRaw = () => {
    window.open(api.getRawApiUrl(id), "_blank");
  };

  const handleCopyCleanedTxt = async () => {
    try {
      await api.copyCleanedTxt(id);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  };

  const handleDownloadCleanedTxt = () => {
    window.open(api.getCleanedTxtUrl(id), "_blank");
  };

  const handleDownloadAll = async () => {
    if (!insights) return;

    const templateId = insights.metadata.template_id;
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Helper function to download file without "Keep from" prompt
    const downloadFile = async (url: string, delay: number = 0) => {
      if (delay > 0) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
      
      // Create invisible link and trigger download
      const a = document.createElement("a");
      a.href = url;
      a.download = ""; // Force download
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    };

    try {
      // 1. Download insights MD
      await downloadFile(`${API_BASE}/api/insights/transcriptions/${id}/download/insights-md?template_id=${templateId}`);

      // 2. Download mindmap MD (if available) - delay 500ms
      if (insights.mindmap) {
        await downloadFile(`${API_BASE}/api/insights/transcriptions/${id}/download/mindmap-md?template_id=${templateId}`, 500);
      }

      // 3. Download transcript - delay 1000ms
      await downloadFile(api.getOriginalTxtUrl(id), 1000);

      toast.success("Downloading all files...");
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Failed to download files");
    }
  };

  return (
    <main className="container mx-auto py-8 px-4 max-w-6xl">
      <Header showSettings={false} showBack={true} />

      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Badge variant="outline">Completed</Badge>
              {transcription.filename}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 text-sm text-muted-foreground mb-6">
            <span>
              {intl.formatMessage({ id: "transcription.meta.duration" })} {formatDuration(transcript.metadata.duration_seconds)}
            </span>
            <span>{intl.formatMessage({ id: "transcription.meta.speakers" })} {transcript.stats.speakers_count}</span>
            <span>{intl.formatMessage({ id: "transcription.meta.language" })} {transcript.metadata.language}</span>
          </div>

          {/* Speaker Editor */}
          <SpeakerEditor
            key={suggestionsKey}
            transcriptionId={id}
            speakers={transcript.speakers}
            onUpdate={handleSpeakersUpdate}
          />

          {/* Identify Speakers button — only for cloud engines */}
          {isCloudEngine && (
            <div className="mt-3">
              <Button
                onClick={handleIdentifySpeakers}
                disabled={isIdentifyingSpeakers}
                variant="outline"
                size="sm"
              >
                {isIdentifyingSpeakers ? (
                  <>
                    <span className="animate-spin mr-2">⏳</span>
                    Identifying...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                    Identify Speakers
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Post-Processing Controls */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="text-lg font-medium mb-2">{intl.formatMessage({ id: "transcription.postProcessing.title" })}</h3>

            {/* Step 1 */}
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-sm font-medium">1</span>
                <span className="font-medium">{intl.formatMessage({ id: "transcription.postProcessing.cleanup.title" })}</span>
                <span className="text-xs text-muted-foreground">(optional)</span>
              </div>
              <p className="text-sm text-muted-foreground ml-8 mb-3">
                Fixes ASR errors, removes repetitions, merges fragmented speech, identifies speakers
              </p>
              <div className="ml-8">
                <PostProcessingControls
                  transcriptionId={id}
                  hasCleanedVersion={hasCleanedVersion}
                  onProcessingComplete={handleProcessingComplete}
                  onTemplateChange={setCleaningTemplateId}
                  usedTemplateId={cleanedTranscript?.metadata?.template}
                />
              </div>
            </div>

            {/* Step 2 */}
            <div className="pt-4 border-t border-dashed">
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-sm font-medium">2</span>
                <span className="font-medium">{intl.formatMessage({ id: "transcription.postProcessing.insights.title" })}</span>
              </div>
              <p className="text-sm text-muted-foreground ml-8 mb-3">
                Extracts key decisions, action items, creates structured summary and mindmap based on meeting type
              </p>
              <div className="ml-8">
                <InsightsControls
                  key={`insights-${hasCleanedVersion}`}
                  transcriptionId={id}
                  hasInsights={hasInsights}
                  onGenerationComplete={handleInsightsComplete}
                  suggestedTemplateId={cleaningTemplateId}
                  usedTemplateId={insights?.metadata?.template_id}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Insights Card */}
      {insights && (
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{intl.formatMessage({ id: "transcription.postProcessing.insights.title" })}</CardTitle>
              {/* Download All button */}
              <Button
                variant="default"
                size="sm"
                onClick={handleDownloadAll}
                className="ml-auto"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <InsightsPanel
              insights={insights}
              filename={transcription.filename}
              transcriptionId={id}
            />
          </CardContent>
        </Card>
      )}

      {/* Transcript View Card */}
      <Card>
        <CardHeader>
          <CardTitle>Transcript</CardTitle>
          {/* Tabs - only show if cleaned exists */}
          {hasCleanedVersion && (
            <div className="flex justify-center pt-2">
              <div className="inline-flex gap-1 p-1.5 bg-muted rounded-xl border">
                <Button
                  variant={viewMode === "cleaned" ? "default" : "ghost"}
                  size="default"
                  onClick={() => setViewMode("cleaned")}
                  className={viewMode === "cleaned" ? "shadow-sm" : "hover:bg-background/50"}
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {intl.formatMessage({ id: "transcription.tabs.cleaned" })}
                </Button>
                <Button
                  variant={viewMode === "original" ? "default" : "ghost"}
                  size="default"
                  onClick={() => setViewMode("original")}
                  className={viewMode === "original" ? "shadow-sm" : "hover:bg-background/50"}
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {intl.formatMessage({ id: "transcription.tabs.original" })}
                </Button>
                <Button
                  variant={viewMode === "comparison" ? "default" : "ghost"}
                  size="default"
                  onClick={() => setViewMode("comparison")}
                  className={viewMode === "comparison" ? "shadow-sm" : "hover:bg-background/50"}
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  {intl.formatMessage({ id: "transcription.tabs.comparison" })}
                </Button>
              </div>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {viewMode === "comparison" && cleanedTranscript ? (
            <TranscriptComparison
              original={transcript}
              cleaned={cleanedTranscript}
              transcriptionId={id}
              engine={transcription.engine}
            />
          ) : viewMode === "cleaned" && cleanedTranscript ? (
            <TranscriptPanel
              type="cleaned"
              data={cleanedTranscript}
              segmentCount={cleanedTranscript.stats.cleaned_segments}
              onCopyTxt={handleCopyCleanedTxt}
              onDownloadTxt={handleDownloadCleanedTxt}
            />
          ) : (
            <TranscriptPanel
              type="original"
              data={transcript}
              segmentCount={transcript.segments.length}
              engine={transcription.engine}
              onCopyTxt={handleCopyOriginalTxt}
              onDownloadTxt={handleDownloadOriginalTxt}
              onCopyJson={handleCopyOriginalJson}
              onDownloadJson={handleDownloadOriginalJson}
              onCopyRaw={handleCopyRaw}
              onDownloadRaw={handleDownloadRaw}
            />
          )}
        </CardContent>
      </Card>
    </main>
  );
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}
