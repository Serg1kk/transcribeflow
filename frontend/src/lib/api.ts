// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LLMOperationSummary {
  operation_type: "cleanup" | "insights";
  provider: string;
  model: string;
  template_id: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number | null;
  processing_time_seconds: number;
  created_at: string;
}

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
  compute_device: string | null;  // "cpu" | "mps" | "auto"
  diarization_method: string | null;  // "none" | "fast" | "accurate"
  // Timing breakdown
  processing_time_seconds: number | null;
  transcription_time_seconds: number | null;
  diarization_time_seconds: number | null;
  // LLM operations
  llm_operations: LLMOperationSummary[];
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

// Post-processing types
export interface Template {
  id: string;
  name: string;
  description: string;
  temperature: number;
}

export interface TemplateDetail extends Template {
  system_prompt: string;
}

export interface LLMModel {
  id: string;
  name: string;
  input_price_per_1m: number | null;
  output_price_per_1m: number | null;
}

export interface LLMModelsConfig {
  gemini: { models: LLMModel[] };
  openrouter: { models: LLMModel[] };
}

export interface CleanedTranscript {
  metadata: {
    id: string;
    filename: string;
    cleaned_at: string;
    template: string;
    provider: string;
    model: string;
  };
  speakers: Record<string, { name: string; color: string }>;
  segments: Array<{
    start: number;
    speaker: string;
    text: string;
  }>;
  stats: {
    original_segments: number;
    cleaned_segments: number;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number | null;
    processing_time_seconds: number;
  };
}

// Speaker suggestions types
export interface SpeakerSuggestion {
  speaker_id: string;
  display_name: string;
  name: string | null;
  name_confidence: number;
  name_reason: string | null;
  role: string | null;
  role_confidence: number;
  role_reason: string | null;
  applied: boolean;
}

export interface SpeakerSuggestions {
  created_at: string;
  template: string;
  model: string;
  suggestions: SpeakerSuggestion[];
}

// Post-processing API functions
export async function getTemplates(): Promise<Template[]> {
  const response = await fetch(`${API_BASE}/api/postprocess/templates`);
  if (!response.ok) throw new Error("Failed to fetch templates");
  return response.json();
}

export async function getLLMModels(): Promise<LLMModelsConfig> {
  const response = await fetch(`${API_BASE}/api/postprocess/models`);
  if (!response.ok) throw new Error("Failed to fetch LLM models");
  return response.json();
}

export async function startPostProcessing(
  transcriptionId: string,
  templateId: string,
  provider?: string,
  model?: string
): Promise<{ status: string; transcription_id: string }> {
  const response = await fetch(
    `${API_BASE}/api/postprocess/transcriptions/${transcriptionId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: templateId,
        provider,
        model,
      }),
    }
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to start post-processing");
  }
  return response.json();
}

export async function getCleanedTranscript(
  transcriptionId: string
): Promise<CleanedTranscript> {
  const response = await fetch(
    `${API_BASE}/api/postprocess/transcriptions/${transcriptionId}/cleaned`
  );
  if (!response.ok) throw new Error("Cleaned transcript not found");
  return response.json();
}

export async function checkCleanedExists(
  transcriptionId: string
): Promise<boolean> {
  try {
    const response = await fetch(
      `${API_BASE}/api/postprocess/transcriptions/${transcriptionId}/cleaned`
    );
    return response.ok;
  } catch {
    return false;
  }
}

// Download URLs
export function getOriginalTxtUrl(id: string): string {
  return `${API_BASE}/api/transcribe/${id}/download/txt`;
}

export function getOriginalJsonUrl(id: string): string {
  return `${API_BASE}/api/transcribe/${id}/download/json`;
}

export function getRawApiUrl(id: string): string {
  return `${API_BASE}/api/transcribe/${id}/download/raw`;
}

export function getCleanedTxtUrl(id: string): string {
  return `${API_BASE}/api/transcribe/${id}/download/cleaned/txt`;
}

export function getCleanedJsonUrl(id: string): string {
  return `${API_BASE}/api/transcribe/${id}/download/cleaned/json`;
}

// Copy to clipboard helpers
export async function copyOriginalTxt(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}/transcript`);
  if (!response.ok) throw new Error("Failed to fetch transcript");
  const data: TranscriptData = await response.json();

  const text = data.segments
    .map(seg => {
      const speaker = data.speakers[seg.speaker]?.name || seg.speaker;
      return `[${formatTimestamp(seg.start)}] ${speaker}: ${seg.text}`;
    })
    .join("\n\n");

  await navigator.clipboard.writeText(text);
}

export async function copyOriginalJson(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}/transcript`);
  if (!response.ok) throw new Error("Failed to fetch transcript");
  const data = await response.json();
  await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
}

export async function copyRawApi(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/transcribe/${id}/download/raw`);
  if (!response.ok) throw new Error("Raw API response not available");
  const data = await response.json();
  await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
}

export async function copyCleanedTxt(id: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/postprocess/transcriptions/${id}/cleaned`
  );
  if (!response.ok) throw new Error("Failed to fetch cleaned transcript");
  const data: CleanedTranscript = await response.json();

  const text = data.segments
    .map(seg => {
      const speaker = data.speakers[seg.speaker]?.name || seg.speaker;
      return `[${formatTimestamp(seg.start)}] ${speaker}: ${seg.text}`;
    })
    .join("\n\n");

  await navigator.clipboard.writeText(text);
}

function formatTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

// Speaker suggestions API functions
export async function getSpeakerSuggestions(
  transcriptionId: string
): Promise<SpeakerSuggestions | null> {
  try {
    // Add cache-busting to prevent stale data
    const response = await fetch(
      `${API_BASE}/api/postprocess/transcriptions/${transcriptionId}/suggestions?_t=${Date.now()}`
    );
    if (response.status === 404) {
      return null;
    }
    if (!response.ok) throw new Error("Failed to fetch suggestions");
    return response.json();
  } catch {
    return null;
  }
}

export async function applySpeakerSuggestion(
  transcriptionId: string,
  speakerId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/postprocess/transcriptions/${transcriptionId}/suggestions/${speakerId}/apply`,
    { method: "POST" }
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to apply suggestion");
  }
}

export async function applyAllSpeakerSuggestions(
  transcriptionId: string
): Promise<{ applied: number }> {
  const response = await fetch(
    `${API_BASE}/api/postprocess/transcriptions/${transcriptionId}/suggestions/apply-all`,
    { method: "POST" }
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to apply suggestions");
  }
  return response.json();
}

// AI Insights types
export interface InsightSection {
  id: string;
  title: string;
  description: string;
}

export interface InsightTemplate {
  id: string;
  name: string;
  description: string;
  include_mindmap: boolean;
  sections: InsightSection[];
  temperature: number;
}

export interface InsightMindmap {
  format: string;
  content: string;
}

export interface InsightSectionContent {
  id: string;
  title: string;
  content: string;
}

export interface Insights {
  metadata: {
    id: string;
    transcription_id: string;
    template_id: string;
    template_name: string;
    source: string;
    created_at: string;
    provider: string;
    model: string;
  };
  description: string;
  sections: InsightSectionContent[];
  mindmap: InsightMindmap | null;
  stats: {
    input_tokens: number;
    output_tokens: number;
    cost_usd: number | null;
    processing_time_seconds: number;
  };
}

export interface SourceAvailability {
  original: boolean;
  cleaned: boolean;
}

export interface InsightMetadata {
  template_id: string;
  template_name: string;
  created_at: string;
}

// AI Insights API functions
export async function getInsightTemplates(): Promise<InsightTemplate[]> {
  const response = await fetch(`${API_BASE}/api/insights/templates`);
  if (!response.ok) throw new Error("Failed to fetch insight templates");
  return response.json();
}

export async function getInsightTemplate(templateId: string): Promise<InsightTemplate> {
  const response = await fetch(`${API_BASE}/api/insights/templates/${templateId}`);
  if (!response.ok) throw new Error("Insight template not found");
  return response.json();
}

export async function generateInsights(
  transcriptionId: string,
  templateId: string,
  source: "original" | "cleaned" = "original",
  provider?: string,
  model?: string
): Promise<{ status: string; transcription_id: string }> {
  const response = await fetch(
    `${API_BASE}/api/insights/transcriptions/${transcriptionId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: templateId,
        source,
        provider,
        model,
      }),
    }
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to generate insights");
  }
  return response.json();
}

export async function getInsights(
  transcriptionId: string,
  templateId: string
): Promise<Insights> {
  const response = await fetch(
    `${API_BASE}/api/insights/transcriptions/${transcriptionId}/${templateId}`
  );
  if (!response.ok) throw new Error("Insights not found");
  return response.json();
}

export async function listInsights(
  transcriptionId: string
): Promise<InsightMetadata[]> {
  const response = await fetch(
    `${API_BASE}/api/insights/transcriptions/${transcriptionId}`
  );
  if (!response.ok) throw new Error("Failed to list insights");
  return response.json();
}

export async function checkInsightSources(
  transcriptionId: string
): Promise<SourceAvailability> {
  const response = await fetch(
    `${API_BASE}/api/insights/transcriptions/${transcriptionId}/sources`
  );
  if (!response.ok) throw new Error("Failed to check sources");
  return response.json();
}

export async function checkInsightsExist(
  transcriptionId: string,
  templateId: string
): Promise<boolean> {
  try {
    const response = await fetch(
      `${API_BASE}/api/insights/transcriptions/${transcriptionId}/${templateId}`
    );
    return response.ok;
  } catch {
    return false;
  }
}
