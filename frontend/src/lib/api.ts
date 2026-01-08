// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Transcription {
  id: string;
  filename: string;
  status: "queued" | "processing" | "diarizing" | "completed" | "failed";
  engine: string;
  model: string;
  language: string | null;
  created_at: string;
  progress: number;
}

export async function uploadAudio(
  file: File,
  options: {
    engine?: string;
    model?: string;
    language?: string;
    minSpeakers?: number;
    maxSpeakers?: number;
  } = {}
): Promise<Transcription> {
  const formData = new FormData();
  formData.append("file", file);

  if (options.engine) formData.append("engine", options.engine);
  if (options.model) formData.append("model", options.model);
  if (options.language) formData.append("language", options.language);
  if (options.minSpeakers) formData.append("min_speakers", String(options.minSpeakers));
  if (options.maxSpeakers) formData.append("max_speakers", String(options.maxSpeakers));

  const response = await fetch(`${API_BASE}/api/transcribe/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
}

export async function getQueue(): Promise<Transcription[]> {
  const response = await fetch(`${API_BASE}/api/transcribe/queue`);
  if (!response.ok) throw new Error("Failed to fetch queue");
  return response.json();
}

export async function getTranscription(id: string): Promise<Transcription> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}`);
  if (!response.ok) throw new Error("Transcription not found");
  return response.json();
}

export interface TranscriptionDetail extends Transcription {
  output_dir: string | null;
  duration_seconds: number | null;
  speakers_count: number | null;
  language_detected: string | null;
  speaker_names: Record<string, string> | null;
}

export interface TranscriptData {
  metadata: {
    id: string;
    filename: string;
    duration_seconds: number;
    created_at: string;
    engine: string;
    model: string;
    language: string;
  };
  speakers: Record<string, { name: string; color: string }>;
  segments: Array<{
    start: number;
    end: number;
    text: string;
    speaker: string;
    confidence: number;
  }>;
  stats: {
    total_words: number;
    speakers_count: number;
    language_detected: string;
    processing_time_seconds: number;
  };
}

export async function getTranscriptionDetail(id: string): Promise<TranscriptionDetail> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}`);
  if (!response.ok) throw new Error("Transcription not found");
  return response.json();
}

export async function getTranscriptData(id: string): Promise<TranscriptData> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}/transcript`);
  if (!response.ok) throw new Error("Transcript not found");
  return response.json();
}

export async function updateSpeakerNames(
  id: string,
  speakerNames: Record<string, string>
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}/speakers`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speaker_names: speakerNames }),
  });
  if (!response.ok) throw new Error("Failed to update speaker names");
}
