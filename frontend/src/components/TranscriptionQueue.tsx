// components/TranscriptionQueue.tsx
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { getQueue, Transcription } from "@/lib/api";
import Link from "next/link";

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  processing: "Transcribing...",
  diarizing: "Identifying speakers...",
  completed: "Completed",
  failed: "Error",
};

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  queued: "secondary",
  processing: "default",
  diarizing: "default",
  completed: "outline",
  failed: "destructive",
};

interface TranscriptionQueueProps {
  refreshTrigger?: number;
}

export function TranscriptionQueue({ refreshTrigger }: TranscriptionQueueProps) {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchQueue() {
      try {
        const data = await getQueue();
        setTranscriptions(data);
      } catch (error) {
        console.error("Failed to fetch queue:", error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchQueue();

    // Poll for updates every 5 seconds if there are active tasks
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, [refreshTrigger]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Transcription Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  if (transcriptions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Transcription Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No transcriptions yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transcription Queue</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {transcriptions.map((t) => (
            <TranscriptionItem key={t.id} transcription={t} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function TranscriptionItem({ transcription }: { transcription: Transcription }) {
  const isActive = ["processing", "diarizing"].includes(transcription.status);
  const isCompleted = transcription.status === "completed";

  return (
    <div className="border rounded-lg p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <Link
              href={`/transcription/${transcription.id}`}
              className="font-medium hover:underline"
            >
              {transcription.filename}
            </Link>
          ) : (
            <span className="font-medium">{transcription.filename}</span>
          )}
        </div>
        <Badge variant={STATUS_VARIANTS[transcription.status]}>
          {STATUS_LABELS[transcription.status]}
        </Badge>
      </div>

      {isActive && (
        <Progress value={transcription.progress} className="h-2" />
      )}

      <div className="flex gap-4 text-sm text-muted-foreground">
        <span>{transcription.engine}</span>
        <span>{transcription.model}</span>
        <span>
          {new Date(transcription.created_at).toLocaleString()}
        </span>
      </div>
    </div>
  );
}
