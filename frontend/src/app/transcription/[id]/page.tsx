// app/transcription/[id]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
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
  getInsightTemplates,
  generateInsights,
  checkInsightSources,
  TranscriptionDetail,
  TranscriptData,
  CleanedTranscript,
  Insights,
  InsightTemplate,
} from "@/lib/api";
import * as api from "@/lib/api";

type ViewMode = "cleaned" | "original" | "comparison";

export default function TranscriptionPage() {
  const params = useParams();
  const id = params.id as string;

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
  const [insightTemplates, setInsightTemplates] = useState<InsightTemplate[]>([]);
  const [hasInsights, setHasInsights] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

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
          const templates = await getInsightTemplates();
          setInsightTemplates(templates);

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
        <p>Loading...</p>
      </main>
    );
  }

  if (error || !transcription || !transcript) {
    return (
      <main className="container mx-auto py-8 px-4 max-w-4xl">
        <p className="text-destructive">{error || "Transcription not found"}</p>
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

  const handleInsightsRegenerate = async (templateId: string) => {
    setIsRegenerating(true);
    try {
      const sources = await checkInsightSources(id);
      const source = sources.cleaned ? "cleaned" : "original";
      await generateInsights(id, templateId, source);

      // Poll for completion
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const startTime = new Date().toISOString();
      let pollCount = 0;
      const maxPolls = 60;

      const pollInterval = setInterval(async () => {
        pollCount++;
        try {
          const response = await fetch(
            `${API_BASE}/api/insights/transcriptions/${id}/${templateId}?_t=${Date.now()}`
          );
          if (response.ok) {
            const data = await response.json();
            if (data.metadata?.created_at >= startTime) {
              clearInterval(pollInterval);
              setInsights(data);
              setIsRegenerating(false);
              return;
            }
          }
          if (pollCount >= maxPolls) {
            clearInterval(pollInterval);
            setIsRegenerating(false);
          }
        } catch {
          // Keep polling
        }
      }, 2000);
    } catch (err) {
      console.error("Failed to regenerate insights:", err);
      setIsRegenerating(false);
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
              Duration: {formatDuration(transcript.metadata.duration_seconds)}
            </span>
            <span>Speakers: {transcript.stats.speakers_count}</span>
            <span>Language: {transcript.metadata.language}</span>
          </div>

          {/* Speaker Editor */}
          <SpeakerEditor
            key={suggestionsKey}
            transcriptionId={id}
            speakers={transcript.speakers}
            onUpdate={handleSpeakersUpdate}
          />

          {/* Post-Processing Controls */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="text-lg font-medium mb-4">LLM Post-Processing</h3>
            <PostProcessingControls
              transcriptionId={id}
              hasCleanedVersion={hasCleanedVersion}
              onProcessingComplete={handleProcessingComplete}
            />
          </div>

          {/* AI Insights Controls */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="text-lg font-medium mb-4">AI Insights</h3>
            <InsightsControls
              key={`insights-${hasCleanedVersion}`}
              transcriptionId={id}
              hasInsights={hasInsights}
              onGenerationComplete={handleInsightsComplete}
            />
          </div>
        </CardContent>
      </Card>

      {/* AI Insights Card */}
      {insights && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>AI Insights</CardTitle>
          </CardHeader>
          <CardContent>
            <InsightsPanel
              insights={insights}
              templates={insightTemplates}
              onRegenerate={handleInsightsRegenerate}
              isRegenerating={isRegenerating}
              filename={transcription.filename}
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
                  Cleaned
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
                  Original
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
                  Comparison
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
