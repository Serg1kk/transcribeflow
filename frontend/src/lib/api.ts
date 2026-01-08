// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Transcription {
  id: string;
  filename: string;
  status: "draft" | "queued" | "processing" | "diarizing" | "completed" | "failed";
  engine: string;
  model: string;
  language: string | null;
  initial_prompt: string | null;
  created_at: string;
  progress: number;
  error_message: string | null;
  file_size: number | null;
  duration_seconds: number | null;
  // Timing breakdown
  processing_time_seconds: number | null;
  transcription_time_seconds: number | null;
  diarization_time_seconds: number | null;
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

export async function updateTranscription(
  id: string,
  data: { initial_prompt?: string }
): Promise<Transcription> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to update transcription");
  return response.json();
}

export async function startTranscriptions(ids: string[]): Promise<{ started: number; failed: number }> {
  const response = await fetch(`${API_BASE}/api/transcribe/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!response.ok) throw new Error("Failed to start transcriptions");
  return response.json();
}

export async function startAllTranscriptions(): Promise<{ started: number; failed: number }> {
  const response = await fetch(`${API_BASE}/api/transcribe/start-all`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to start all transcriptions");
  return response.json();
}

export async function deleteTranscription(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete transcription");
}

// Engine capabilities
export interface EngineCapabilities {
  supports_initial_prompt: boolean;
  supports_timestamps: boolean;
  supports_word_timestamps: boolean;
}

export interface EngineInfo {
  name: string;
  display_name: string;
  description: string;
}

export interface EngineCapabilitiesResponse {
  name: string;
  display_name: string;
  capabilities: EngineCapabilities;
}

// Cache for engine capabilities
const capabilitiesCache: Record<string, EngineCapabilities> = {};

export async function getEngineCapabilities(engineName: string): Promise<EngineCapabilities> {
  if (capabilitiesCache[engineName]) {
    return capabilitiesCache[engineName];
  }

  const response = await fetch(`${API_BASE}/api/engines/${engineName}/capabilities`);
  if (!response.ok) {
    // Return default capabilities if engine not found
    return {
      supports_initial_prompt: false,
      supports_timestamps: true,
      supports_word_timestamps: true,
    };
  }

  const data: EngineCapabilitiesResponse = await response.json();
  capabilitiesCache[engineName] = data.capabilities;
  return data.capabilities;
}

export function engineSupportsInitialPrompt(engineName: string): boolean {
  // For now, we know mlx-whisper supports it
  // This can be made async if needed
  return engineName === "mlx-whisper";
}
