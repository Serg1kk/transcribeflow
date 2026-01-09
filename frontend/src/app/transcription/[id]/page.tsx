// app/transcription/[id]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SpeakerEditor } from "@/components/SpeakerEditor";
import { PostProcessingControls } from "@/components/PostProcessingControls";
import { TranscriptComparison } from "@/components/TranscriptComparison";
import { TranscriptPanel } from "@/components/TranscriptPanel";
import {
  getTranscriptionDetail,
  getTranscriptData,
  getCleanedTranscript,
  checkCleanedExists,
  TranscriptionDetail,
  TranscriptData,
  CleanedTranscript,
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
      const cleaned = await getCleanedTranscript(id);
      setCleanedTranscript(cleaned);
      setHasCleanedVersion(true);
      setViewMode("cleaned");
    } catch (err) {
      console.error("Failed to load cleaned transcript:", err);
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
      <Link href="/" className="text-primary hover:underline mb-4 inline-block">
        ← Back
      </Link>

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
        </CardContent>
      </Card>

      {/* Transcript View Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Transcript</CardTitle>
            {/* Tabs - only show if cleaned exists */}
            {hasCleanedVersion && (
              <div className="flex gap-1 p-1 bg-muted rounded-lg">
                <Button
                  variant={viewMode === "cleaned" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("cleaned")}
                >
                  Cleaned
                </Button>
                <Button
                  variant={viewMode === "original" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("original")}
                >
                  Original
                </Button>
                <Button
                  variant={viewMode === "comparison" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("comparison")}
                >
                  Comparison
                </Button>
              </div>
            )}
          </div>
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
