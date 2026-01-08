// app/settings/page.tsx
"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Engine {
  id: string;
  name: string;
  models: string[];
  available: boolean;
}

const LLM_PROVIDERS = [
  { value: "gemini", label: "Google Gemini" },
  { value: "openrouter", label: "OpenRouter" },
];

interface Settings {
  default_engine: string;
  default_model: string;
  diarization_enabled: boolean;
  min_speakers: number;
  max_speakers: number;
  // Whisper Anti-Hallucination
  whisper_no_speech_threshold: number;
  whisper_logprob_threshold: number;
  whisper_compression_ratio_threshold: number;
  whisper_hallucination_silence_threshold: number | null;
  whisper_condition_on_previous_text: boolean;
  whisper_initial_prompt: string | null;
  // LLM & API
  default_llm_provider: string;
  has_hf_token: boolean;
  has_assemblyai_key: boolean;
  has_elevenlabs_key: boolean;
  has_deepgram_key: boolean;
  has_yandex_key: boolean;
  has_gemini_key: boolean;
  has_openrouter_key: boolean;
  features: Record<string, { status: string; description: string }>;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  // Form state
  const [defaultModel, setDefaultModel] = useState("");
  const [defaultEngine, setDefaultEngine] = useState("");
  const [diarizationEnabled, setDiarizationEnabled] = useState(false);
  const [minSpeakers, setMinSpeakers] = useState(2);
  const [maxSpeakers, setMaxSpeakers] = useState(6);
  const [defaultLlmProvider, setDefaultLlmProvider] = useState("");

  // Whisper Anti-Hallucination state
  const [noSpeechThreshold, setNoSpeechThreshold] = useState(0.6);
  const [logprobThreshold, setLogprobThreshold] = useState(-1.0);
  const [compressionRatioThreshold, setCompressionRatioThreshold] = useState(2.4);
  const [hallucinationSilenceThreshold, setHallucinationSilenceThreshold] = useState<number | null>(2.0);
  const [conditionOnPreviousText, setConditionOnPreviousText] = useState(true);
  const [initialPrompt, setInitialPrompt] = useState("");

  // API Keys (for input)
  const [hfToken, setHfToken] = useState("");
  const [assemblyaiKey, setAssemblyaiKey] = useState("");
  const [deepgramKey, setDeepgramKey] = useState("");
  const [elevenlabsKey, setElevenlabsKey] = useState("");
  const [yandexKey, setYandexKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [openrouterKey, setOpenrouterKey] = useState("");

  useEffect(() => {
    fetchSettings();
    fetchEngines();
  }, []);

  async function fetchSettings() {
    try {
      const res = await fetch(`${API_BASE}/api/settings`);
      const data = await res.json();
      setSettings(data);
      // Set form values
      setDefaultModel(data.default_model);
      setDefaultEngine(data.default_engine);
      setDiarizationEnabled(data.diarization_enabled);
      setMinSpeakers(data.min_speakers);
      setMaxSpeakers(data.max_speakers);
      setDefaultLlmProvider(data.default_llm_provider);
      // Whisper settings
      setNoSpeechThreshold(data.whisper_no_speech_threshold);
      setLogprobThreshold(data.whisper_logprob_threshold);
      setCompressionRatioThreshold(data.whisper_compression_ratio_threshold);
      setHallucinationSilenceThreshold(data.whisper_hallucination_silence_threshold);
      setConditionOnPreviousText(data.whisper_condition_on_previous_text);
      setInitialPrompt(data.whisper_initial_prompt || "");
    } catch (error) {
      console.error("Failed to fetch settings:", error);
    }
  }

  async function fetchEngines() {
    try {
      const res = await fetch(`${API_BASE}/api/engines`);
      const data = await res.json();
      if (data.engines) {
        setEngines(data.engines);
      }
    } catch (error) {
      console.error("Failed to fetch engines:", error);
    }
  }

  // Get models for current engine
  const currentEngine = engines.find((e) => e.id === defaultEngine);
  const availableModels = useMemo(
    () => currentEngine?.models || [],
    [currentEngine]
  );

  // Reset model if not available for current engine
  useEffect(() => {
    if (availableModels.length > 0 && !availableModels.includes(defaultModel)) {
      setDefaultModel(availableModels[0]);
    }
  }, [defaultEngine, availableModels, defaultModel]);

  async function saveSettings() {
    setIsSaving(true);
    setSaveMessage(null);

    const updates: Record<string, any> = {
      default_model: defaultModel,
      default_engine: defaultEngine,
      diarization_enabled: diarizationEnabled,
      min_speakers: minSpeakers,
      max_speakers: maxSpeakers,
      default_llm_provider: defaultLlmProvider,
      // Whisper Anti-Hallucination settings
      whisper_no_speech_threshold: noSpeechThreshold,
      whisper_logprob_threshold: logprobThreshold,
      whisper_compression_ratio_threshold: compressionRatioThreshold,
      whisper_hallucination_silence_threshold: hallucinationSilenceThreshold,
      whisper_condition_on_previous_text: conditionOnPreviousText,
      whisper_initial_prompt: initialPrompt || null,
    };

    // Only include API keys if they were entered
    if (hfToken) updates.hf_token = hfToken;
    if (assemblyaiKey) updates.assemblyai_api_key = assemblyaiKey;
    if (deepgramKey) updates.deepgram_api_key = deepgramKey;
    if (elevenlabsKey) updates.elevenlabs_api_key = elevenlabsKey;
    if (yandexKey) updates.yandex_api_key = yandexKey;
    if (geminiKey) updates.gemini_api_key = geminiKey;
    if (openrouterKey) updates.openrouter_api_key = openrouterKey;

    try {
      const res = await fetch(`${API_BASE}/api/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        setSaveMessage("Settings saved successfully!");
        // Clear API key inputs after save
        setHfToken("");
        setAssemblyaiKey("");
        setDeepgramKey("");
        setElevenlabsKey("");
        setYandexKey("");
        setGeminiKey("");
        setOpenrouterKey("");
      } else {
        setSaveMessage("Failed to save settings");
      }
    } catch (error) {
      setSaveMessage("Error saving settings");
    } finally {
      setIsSaving(false);
      setTimeout(() => setSaveMessage(null), 3000);
    }
  }

  if (!settings) {
    return (
      <main className="container mx-auto py-8 px-4 max-w-4xl">
        <p>Loading...</p>
      </main>
    );
  }

  return (
    <main className="container mx-auto py-8 px-4 max-w-4xl">
      <Link href="/" className="text-primary hover:underline mb-4 inline-block">
        &larr; Back
      </Link>

      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Settings</h1>
        <Button onClick={saveSettings} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Changes"}
        </Button>
      </div>

      {saveMessage && (
        <div className={`mb-4 p-3 rounded ${saveMessage.includes("success") ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
          {saveMessage}
        </div>
      )}

      <div className="space-y-6">
        {/* Transcription Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Transcription</CardTitle>
            <CardDescription>Default settings for new transcriptions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Default Engine</Label>
                <Select value={defaultEngine} onValueChange={setDefaultEngine}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {engines.length > 0 ? (
                      engines.map((e) => (
                        <SelectItem key={e.id} value={e.id}>
                          {e.name}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="mlx-whisper">MLX Local</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Default Model</Label>
                <Select value={defaultModel} onValueChange={setDefaultModel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {availableModels.length > 0 ? (
                      availableModels.map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="large-v3-turbo">large-v3-turbo</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Diarization Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Speaker Diarization</CardTitle>
            <CardDescription>Identify who said what in recordings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <Label>Enable Diarization</Label>
              <Button
                variant={diarizationEnabled ? "default" : "outline"}
                size="sm"
                onClick={() => setDiarizationEnabled(!diarizationEnabled)}
              >
                {diarizationEnabled ? "Enabled" : "Disabled"}
              </Button>
              <Badge variant={settings.has_hf_token ? "outline" : "destructive"}>
                HuggingFace Token: {settings.has_hf_token ? "Configured" : "Missing"}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Min Speakers</Label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={minSpeakers}
                  onChange={(e) => setMinSpeakers(parseInt(e.target.value) || 2)}
                />
              </div>
              <div className="space-y-2">
                <Label>Max Speakers</Label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={maxSpeakers}
                  onChange={(e) => setMaxSpeakers(parseInt(e.target.value) || 6)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>HuggingFace Token</Label>
              <Input
                type="password"
                placeholder={settings.has_hf_token ? "********" : "Enter HuggingFace token"}
                value={hfToken}
                onChange={(e) => setHfToken(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Get token from <a href="https://huggingface.co/settings/tokens" target="_blank" className="underline">huggingface.co/settings/tokens</a>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Whisper Anti-Hallucination Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Whisper Quality Settings</CardTitle>
            <CardDescription>
              Prevent hallucinations like &quot;Субтитры сделал DimaTorzok&quot; during silence
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label>No Speech Threshold</Label>
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={noSpeechThreshold}
                  onChange={(e) => setNoSpeechThreshold(parseFloat(e.target.value) || 0.6)}
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>Диапазон:</strong> 0.0 — 1.0</p>
                  <p><strong>Default:</strong> 0.6</p>
                  <p>Если Whisper думает, что в сегменте нет речи с вероятностью выше этого порога — сегмент пропускается.</p>
                  <p className="text-amber-600">↑ Выше (0.7-0.9) = меньше галлюцинаций, но может пропустить тихую речь</p>
                  <p className="text-blue-600">↓ Ниже (0.3-0.5) = больше текста, но больше мусора</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Log Probability Threshold</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="-10"
                  max="0"
                  value={logprobThreshold}
                  onChange={(e) => setLogprobThreshold(parseFloat(e.target.value) || -1.0)}
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>Диапазон:</strong> -10.0 — 0.0 (всегда отрицательное!)</p>
                  <p><strong>Default:</strong> -1.0</p>
                  <p>Средняя уверенность модели в сегменте. Чем ближе к 0, тем увереннее.</p>
                  <p className="text-amber-600">↑ Ближе к 0 (-0.5) = только уверенные сегменты, может потерять текст</p>
                  <p className="text-blue-600">↓ Дальше от 0 (-2.0) = больше текста, больше галлюцинаций</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label>Compression Ratio Threshold</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="1"
                  max="10"
                  value={compressionRatioThreshold}
                  onChange={(e) => setCompressionRatioThreshold(parseFloat(e.target.value) || 2.4)}
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>Диапазон:</strong> 1.0 — 10.0</p>
                  <p><strong>Default:</strong> 2.4</p>
                  <p>Фильтрует повторяющийся/зацикленный текст (типа &quot;да да да да да&quot;).</p>
                  <p className="text-amber-600">↓ Ниже (1.5-2.0) = строже фильтрует повторы</p>
                  <p className="text-blue-600">↑ Выше (3.0-5.0) = пропускает больше повторов</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Hallucination Silence Threshold (сек)</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  max="30"
                  value={hallucinationSilenceThreshold ?? ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    setHallucinationSilenceThreshold(val ? parseFloat(val) : null);
                  }}
                  placeholder="Пусто = выключено"
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>Диапазон:</strong> 0.5 — 30.0 секунд (или пусто)</p>
                  <p><strong>Default:</strong> 2.0</p>
                  <p>Пропускает текст, который появляется после длинной паузы (главный фильтр галлюцинаций!).</p>
                  <p className="text-amber-600">↓ Ниже (0.5-1.0) = агрессивнее, может отрезать реальную речь после пауз</p>
                  <p className="text-blue-600">↑ Выше (3.0-5.0) = мягче, пропустит короткие галлюцинации</p>
                </div>
              </div>
            </div>

            <div className="space-y-2 p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-4">
                <Label>Use Previous Context</Label>
                <Button
                  variant={conditionOnPreviousText ? "default" : "outline"}
                  size="sm"
                  onClick={() => setConditionOnPreviousText(!conditionOnPreviousText)}
                >
                  {conditionOnPreviousText ? "Включено" : "Выключено"}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Использует предыдущий распознанный текст как контекст для следующего сегмента.
                Помогает с консистентностью, но может &quot;застрять&quot; на ошибке.
                <strong> Рекомендуется оставить включённым.</strong>
              </p>
            </div>

            <div className="space-y-2">
              <Label>Initial Prompt (опционально)</Label>
              <Input
                type="text"
                placeholder="e.g., Это рабочий митинг о разработке..."
                value={initialPrompt}
                onChange={(e) => setInitialPrompt(e.target.value)}
              />
              <div className="text-xs text-muted-foreground space-y-1">
                <p>Начальный контекст для модели. Помогает с терминологией и стилем.</p>
                <p><strong>Примеры:</strong></p>
                <p>• &quot;Это техническое интервью о программировании&quot;</p>
                <p>• &quot;Разговор на русском языке о машинном обучении&quot;</p>
                <p>• &quot;Подкаст о стартапах, участники: Иван и Мария&quot;</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cloud ASR Providers */}
        <Card>
          <CardHeader>
            <CardTitle>Cloud ASR Providers</CardTitle>
            <CardDescription>Configure API keys for cloud transcription services</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ApiKeyInput
              label="AssemblyAI"
              hasKey={settings.has_assemblyai_key}
              value={assemblyaiKey}
              onChange={setAssemblyaiKey}
              status={settings.features.assemblyai?.status}
            />
            <ApiKeyInput
              label="Deepgram"
              hasKey={settings.has_deepgram_key}
              value={deepgramKey}
              onChange={setDeepgramKey}
              status={settings.features.deepgram?.status}
            />
            <ApiKeyInput
              label="ElevenLabs Scribe"
              hasKey={settings.has_elevenlabs_key}
              value={elevenlabsKey}
              onChange={setElevenlabsKey}
              status={settings.features.elevenlabs?.status}
            />
            <ApiKeyInput
              label="Yandex SpeechKit"
              hasKey={settings.has_yandex_key}
              value={yandexKey}
              onChange={setYandexKey}
              status={settings.features.yandex?.status}
            />
          </CardContent>
        </Card>

        {/* LLM Settings */}
        <Card>
          <CardHeader>
            <CardTitle>LLM Post-Processing</CardTitle>
            <CardDescription>AI-powered summarization and analysis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Default LLM Provider</Label>
              <Select value={defaultLlmProvider} onValueChange={setDefaultLlmProvider}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LLM_PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <ApiKeyInput
              label="Google Gemini"
              hasKey={settings.has_gemini_key}
              value={geminiKey}
              onChange={setGeminiKey}
              status={settings.features.gemini_llm?.status}
            />
            <ApiKeyInput
              label="OpenRouter"
              hasKey={settings.has_openrouter_key}
              value={openrouterKey}
              onChange={setOpenrouterKey}
              status={settings.features.openrouter_llm?.status}
            />
          </CardContent>
        </Card>

        {/* Feature Status */}
        <Card>
          <CardHeader>
            <CardTitle>Feature Status</CardTitle>
            <CardDescription>Implementation status of features</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(settings.features).map(([key, feature]) => (
                <div key={key} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                  <span className="text-sm">{feature.description}</span>
                  <Badge variant={feature.status === "implemented" ? "default" : "secondary"}>
                    {feature.status === "implemented" ? "Ready" : "TBD"}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

function ApiKeyInput({
  label,
  hasKey,
  value,
  onChange,
  status,
}: {
  label: string;
  hasKey: boolean;
  value: string;
  onChange: (value: string) => void;
  status?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Label>{label}</Label>
        <Badge variant={hasKey ? "outline" : "secondary"}>
          {hasKey ? "Configured" : "Not set"}
        </Badge>
        {status === "tbd" && (
          <Badge variant="secondary" className="text-xs">TBD</Badge>
        )}
      </div>
      <Input
        type="password"
        placeholder={hasKey ? "********" : `Enter ${label} API key`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={status === "tbd"}
      />
    </div>
  );
}
