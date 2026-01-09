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
import {
  getTranscriptionDetail,
  getTranscriptData,
  getCleanedTranscript,
  checkCleanedExists,
  TranscriptionDetail,
  TranscriptData,
  CleanedTranscript,
} from "@/lib/api";

export default function TranscriptionPage() {
  const params = useParams();
  const id = params.id as string;

  const [transcription, setTranscription] = useState<TranscriptionDetail | null>(null);
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  const [cleanedTranscript, setCleanedTranscript] = useState<CleanedTranscript | null>(null);
  const [hasCleanedVersion, setHasCleanedVersion] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
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
  };

  const handleProcessingComplete = async () => {
    try {
      const cleaned = await getCleanedTranscript(id);
      setCleanedTranscript(cleaned);
      setHasCleanedVersion(true);
      setShowComparison(true);
    } catch (err) {
      console.error("Failed to load cleaned transcript:", err);
    }
  };

  return (
    <main className="container mx-auto py-8 px-4 max-w-4xl">
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
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">LLM Post-Processing</h3>
              {hasCleanedVersion && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowComparison(!showComparison)}
                >
                  {showComparison ? "Hide Comparison" : "Show Comparison"}
                </Button>
              )}
            </div>
            <PostProcessingControls
              transcriptionId={id}
              hasCleanedVersion={hasCleanedVersion}
              onProcessingComplete={handleProcessingComplete}
            />
          </div>
        </CardContent>
      </Card>

      {/* Comparison View or Transcript */}
      {showComparison && cleanedTranscript ? (
        <Card>
          <CardHeader>
            <CardTitle>Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <TranscriptComparison
              original={transcript}
              cleaned={cleanedTranscript}
            />
          </CardContent>
        </Card>
      ) : (
        /* Transcript */
      <Card>
        <CardHeader>
          <CardTitle>Transcript</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {transcript.segments.map((segment, index) => {
              const speaker = transcript.speakers[segment.speaker];
              return (
                <div key={index} className="flex gap-4">
                  <span className="text-muted-foreground text-sm w-20 shrink-0">
                    [{formatTimestamp(segment.start)}]
                  </span>
                  <span
                    className="font-medium w-24 shrink-0"
                    style={{ color: speaker?.color }}
                  >
                    {speaker?.name || segment.speaker}:
                  </span>
                  <span>{segment.text}</span>
                </div>
              );
            })}
          </div>

          {/* Download buttons */}
          <div className="flex gap-4 mt-6 pt-6 border-t">
            <Button
              variant="outline"
              onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/transcribe/${id}/download/txt`, '_blank')}
            >
              Download .txt
            </Button>
            <Button
              variant="outline"
              onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/transcribe/${id}/download/json`, '_blank')}
            >
              Download .json
            </Button>
            <Button
              variant="outline"
              onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/transcribe/${id}/download/raw`, '_blank')}
            >
              Download Raw API Response
            </Button>
          </div>
        </CardContent>
      </Card>
      )}
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

function formatTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}
