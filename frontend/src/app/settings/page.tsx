// app/settings/page.tsx
"use client";

import { useEffect, useState, useMemo } from "react";
import { useIntl } from "react-intl";
import { toast } from "sonner";
import { Header } from "@/components/Header";
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

interface Settings {
  default_engine: string;
  default_model: string;
  diarization_method: string;  // "none" | "fast" | "accurate"
  compute_device: string;  // "auto" | "mps" | "cpu"
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
  // Post-processing
  postprocessing_provider: string;
  postprocessing_model: string;
  postprocessing_default_template: string | null;
  // AI Insights
  insights_provider: string;
  insights_model: string;
  insights_default_template: string | null;
  // API keys
  has_hf_token: boolean;
  has_assemblyai_key: boolean;
  has_elevenlabs_key: boolean;
  has_deepgram_key: boolean;
  has_yandex_key: boolean;
  has_gemini_key: boolean;
  has_openrouter_key: boolean;
}

export default function SettingsPage() {
  const intl = useIntl();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Form state
  const [defaultModel, setDefaultModel] = useState("");
  const [defaultEngine, setDefaultEngine] = useState("");
  const [diarizationMethod, setDiarizationMethod] = useState("fast");
  const [computeDevice, setComputeDevice] = useState("auto");
  const [minSpeakers, setMinSpeakers] = useState(2);
  const [maxSpeakers, setMaxSpeakers] = useState(6);
  const [defaultLlmProvider, setDefaultLlmProvider] = useState("");

  // Post-processing state
  const [postprocessingProvider, setPostprocessingProvider] = useState("gemini");
  const [postprocessingModel, setPostprocessingModel] = useState("gemini-2.5-flash");

  // AI Insights state
  const [insightsProvider, setInsightsProvider] = useState("gemini");
  const [insightsModel, setInsightsModel] = useState("gemini-2.5-flash");

  // Whisper Anti-Hallucination state
  const [noSpeechThreshold, setNoSpeechThreshold] = useState(0.6);
  const [logprobThreshold, setLogprobThreshold] = useState(-1.0);
  const [compressionRatioThreshold, setCompressionRatioThreshold] = useState(2.4);
  const [hallucinationSilenceThreshold, setHallucinationSilenceThreshold] = useState<number | null>(2.0);
  const [conditionOnPreviousText, setConditionOnPreviousText] = useState(true);

  // API Keys (for input)
  const [hfToken, setHfToken] = useState("");
  const [assemblyaiKey, setAssemblyaiKey] = useState("");
  const [deepgramKey, setDeepgramKey] = useState("");
  const [elevenlabsKey, setElevenlabsKey] = useState("");
  const [yandexKey, setYandexKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [openrouterKey, setOpenrouterKey] = useState("");

  // LLM Providers with translated labels
  const LLM_PROVIDERS = useMemo(() => [
    { value: "gemini", label: intl.formatMessage({ id: "settings.llm.provider.gemini" }) },
    { value: "openrouter", label: intl.formatMessage({ id: "settings.llm.provider.openrouter" }) },
  ], [intl]);

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
      setDiarizationMethod(data.diarization_method);
      setComputeDevice(data.compute_device);
      setMinSpeakers(data.min_speakers);
      setMaxSpeakers(data.max_speakers);
      setDefaultLlmProvider(data.default_llm_provider);
      // Post-processing settings
      setPostprocessingProvider(data.postprocessing_provider);
      setPostprocessingModel(data.postprocessing_model);
      // AI Insights settings
      setInsightsProvider(data.insights_provider || "gemini");
      setInsightsModel(data.insights_model || "gemini-2.5-flash");
      // Whisper settings
      setNoSpeechThreshold(data.whisper_no_speech_threshold);
      setLogprobThreshold(data.whisper_logprob_threshold);
      setCompressionRatioThreshold(data.whisper_compression_ratio_threshold);
      setHallucinationSilenceThreshold(data.whisper_hallucination_silence_threshold);
      setConditionOnPreviousText(data.whisper_condition_on_previous_text);
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

    const updates: Record<string, string | number | boolean | null> = {
      default_model: defaultModel,
      default_engine: defaultEngine,
      diarization_method: diarizationMethod,
      compute_device: computeDevice,
      min_speakers: minSpeakers,
      max_speakers: maxSpeakers,
      default_llm_provider: defaultLlmProvider,
      // Post-processing settings
      postprocessing_provider: postprocessingProvider,
      postprocessing_model: postprocessingModel,
      // AI Insights settings
      insights_provider: insightsProvider,
      insights_model: insightsModel,
      // Whisper Anti-Hallucination settings
      whisper_no_speech_threshold: noSpeechThreshold,
      whisper_logprob_threshold: logprobThreshold,
      whisper_compression_ratio_threshold: compressionRatioThreshold,
      whisper_hallucination_silence_threshold: hallucinationSilenceThreshold,
      whisper_condition_on_previous_text: conditionOnPreviousText,
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
        toast.success("Settings saved successfully!");
        // Clear API key inputs after save
        setHfToken("");
        setAssemblyaiKey("");
        setDeepgramKey("");
        setElevenlabsKey("");
        setYandexKey("");
        setGeminiKey("");
        setOpenrouterKey("");
      } else {
        toast.error("Failed to save settings");
      }
    } catch {
      toast.error("Error saving settings");
    } finally {
      setIsSaving(false);
    }
  }

  if (!settings) {
    return (
      <main className="container mx-auto py-8 px-4 max-w-4xl">
        <p>{intl.formatMessage({ id: "status.loading" })}</p>
      </main>
    );
  }

  return (
    <main className="container mx-auto py-8 px-4 max-w-4xl">
      <Header showSettings={false} showBack={true} />

      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">{intl.formatMessage({ id: "settings.title" })}</h1>
        <Button onClick={saveSettings} disabled={isSaving}>
          {isSaving
            ? intl.formatMessage({ id: "button.saving" })
            : intl.formatMessage({ id: "button.save" })}
        </Button>
      </div>


      <div className="space-y-6">
        {/* Transcription Settings (ASR) */}
        <Card>
          <CardHeader>
            <CardTitle>{intl.formatMessage({ id: "settings.asr.title" })}</CardTitle>
            <CardDescription>{intl.formatMessage({ id: "settings.asr.description" })}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "label.engine" })}</Label>
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
                <Label>{intl.formatMessage({ id: "label.model" })}</Label>
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
            {defaultEngine === "mlx-whisper" && (
              <p className="text-xs text-muted-foreground">
                {intl.formatMessage({ id: "settings.asr.help.mlx" })}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Speaker Diarization Settings */}
        <Card>
          <CardHeader>
            <CardTitle>{intl.formatMessage({ id: "settings.diarization.title" })}</CardTitle>
            <CardDescription>{intl.formatMessage({ id: "settings.diarization.description" })}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Only show for local engine */}
            {defaultEngine === "mlx-whisper" && (
              <>
                <div className="space-y-2">
                  <Label>{intl.formatMessage({ id: "settings.diarization.device.label" })}</Label>
                  <Select
                    value={computeDevice}
                    onValueChange={(value) => {
                      setComputeDevice(value);
                      // Reset to "fast" if switching to GPU while "accurate" is selected
                      if (value !== "cpu" && diarizationMethod === "accurate") {
                        setDiarizationMethod("fast");
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">{intl.formatMessage({ id: "settings.diarization.device.auto" })}</SelectItem>
                      <SelectItem value="mps">{intl.formatMessage({ id: "settings.diarization.device.gpu" })}</SelectItem>
                      <SelectItem value="cpu">{intl.formatMessage({ id: "settings.diarization.device.cpu" })}</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {intl.formatMessage({ id: "settings.diarization.device.help" })}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>{intl.formatMessage({ id: "settings.diarization.method.label" })}</Label>
                  <Select value={diarizationMethod} onValueChange={setDiarizationMethod}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">{intl.formatMessage({ id: "settings.diarization.method.none" })}</SelectItem>
                      <SelectItem value="fast">{intl.formatMessage({ id: "settings.diarization.method.fast" })}</SelectItem>
                      {computeDevice === "cpu" && (
                        <SelectItem value="accurate">{intl.formatMessage({ id: "settings.diarization.method.accurate" })}</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {computeDevice === "cpu"
                      ? intl.formatMessage({ id: "settings.diarization.method.help.cpu" })
                      : intl.formatMessage({ id: "settings.diarization.method.help.gpu" })
                    }
                  </p>
                </div>

                {/* Speaker count settings */}
                {diarizationMethod !== "none" && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>{intl.formatMessage({ id: "settings.diarization.speakers.min" })}</Label>
                      <Input
                        type="number"
                        min={1}
                        max={10}
                        value={minSpeakers}
                        onChange={(e) => setMinSpeakers(parseInt(e.target.value) || 2)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{intl.formatMessage({ id: "settings.diarization.speakers.max" })}</Label>
                      <Input
                        type="number"
                        min={1}
                        max={10}
                        value={maxSpeakers}
                        onChange={(e) => setMaxSpeakers(parseInt(e.target.value) || 6)}
                      />
                    </div>
                  </div>
                )}

                {diarizationMethod !== "none" && (
                  <div className="space-y-2">
                    <Label>{intl.formatMessage({ id: "settings.diarization.token.label" })}</Label>
                    <div className="flex items-center gap-2">
                      <Badge variant={settings.has_hf_token ? "outline" : "destructive"}>
                        {settings.has_hf_token
                          ? intl.formatMessage({ id: "badge.configured" })
                          : intl.formatMessage({ id: "badge.required" })}
                      </Badge>
                    </div>
                    <Input
                      type="password"
                      placeholder={settings.has_hf_token ? "********" : intl.formatMessage({ id: "settings.diarization.token.label" })}
                      value={hfToken}
                      onChange={(e) => setHfToken(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      {intl.formatMessage({ id: "settings.diarization.token.help" })}{" "}
                      <a href="https://huggingface.co/settings/tokens" target="_blank" className="underline">
                        huggingface.co/settings/tokens
                      </a>
                    </p>
                  </div>
                )}
              </>
            )}

            {/* Show for cloud engines */}
            {defaultEngine !== "mlx-whisper" && (
              <>
                <p className="text-sm text-muted-foreground">
                  {intl.formatMessage({ id: "settings.asr.help.cloud" })}
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>{intl.formatMessage({ id: "settings.diarization.speakers.min" })}</Label>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={minSpeakers}
                      onChange={(e) => setMinSpeakers(parseInt(e.target.value) || 2)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>{intl.formatMessage({ id: "settings.diarization.speakers.max" })}</Label>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={maxSpeakers}
                      onChange={(e) => setMaxSpeakers(parseInt(e.target.value) || 6)}
                    />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Whisper Anti-Hallucination Settings */}
        <Card>
          <CardHeader>
            <CardTitle>{intl.formatMessage({ id: "settings.whisper.title" })}</CardTitle>
            <CardDescription>
              {intl.formatMessage({ id: "settings.whisper.description" })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "settings.whisper.noSpeech.label" })}</Label>
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={noSpeechThreshold}
                  onChange={(e) => setNoSpeechThreshold(parseFloat(e.target.value) || 0.6)}
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.noSpeech.range" })}</strong></p>
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.noSpeech.default" })}</strong></p>
                  <p>{intl.formatMessage({ id: "settings.whisper.noSpeech.help" })}</p>
                  <p className="text-amber-600">{intl.formatMessage({ id: "settings.whisper.noSpeech.helpHigh" })}</p>
                  <p className="text-blue-600">{intl.formatMessage({ id: "settings.whisper.noSpeech.helpLow" })}</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "settings.whisper.logProb.label" })}</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="-10"
                  max="0"
                  value={logprobThreshold}
                  onChange={(e) => setLogprobThreshold(parseFloat(e.target.value) || -1.0)}
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.logProb.range" })}</strong></p>
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.logProb.default" })}</strong></p>
                  <p>{intl.formatMessage({ id: "settings.whisper.logProb.help" })}</p>
                  <p className="text-amber-600">{intl.formatMessage({ id: "settings.whisper.logProb.helpHigh" })}</p>
                  <p className="text-blue-600">{intl.formatMessage({ id: "settings.whisper.logProb.helpLow" })}</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "settings.whisper.compression.label" })}</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="1"
                  max="10"
                  value={compressionRatioThreshold}
                  onChange={(e) => setCompressionRatioThreshold(parseFloat(e.target.value) || 2.4)}
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.compression.range" })}</strong></p>
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.compression.default" })}</strong></p>
                  <p>{intl.formatMessage({ id: "settings.whisper.compression.help" })}</p>
                  <p className="text-amber-600">{intl.formatMessage({ id: "settings.whisper.compression.helpLow" })}</p>
                  <p className="text-blue-600">{intl.formatMessage({ id: "settings.whisper.compression.helpHigh" })}</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "settings.whisper.silence.label" })}</Label>
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
                  placeholder={intl.formatMessage({ id: "settings.whisper.silence.placeholder" })}
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.silence.range" })}</strong></p>
                  <p><strong>{intl.formatMessage({ id: "settings.whisper.silence.default" })}</strong></p>
                  <p>{intl.formatMessage({ id: "settings.whisper.silence.help" })}</p>
                  <p className="text-amber-600">{intl.formatMessage({ id: "settings.whisper.silence.helpLow" })}</p>
                  <p className="text-blue-600">{intl.formatMessage({ id: "settings.whisper.silence.helpHigh" })}</p>
                </div>
              </div>
            </div>

            <div className="space-y-2 p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-4">
                <Label>{intl.formatMessage({ id: "settings.whisper.context.label" })}</Label>
                <Button
                  variant={conditionOnPreviousText ? "default" : "outline"}
                  size="sm"
                  onClick={() => setConditionOnPreviousText(!conditionOnPreviousText)}
                >
                  {conditionOnPreviousText
                    ? intl.formatMessage({ id: "settings.whisper.context.enabled" })
                    : intl.formatMessage({ id: "settings.whisper.context.disabled" })}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {intl.formatMessage({ id: "settings.whisper.context.help" })}
              </p>
            </div>

          </CardContent>
        </Card>

        {/* Cloud ASR Providers */}
        <Card>
          <CardHeader>
            <CardTitle>{intl.formatMessage({ id: "settings.cloudAsr.title" })}</CardTitle>
            <CardDescription>{intl.formatMessage({ id: "settings.cloudAsr.description" })}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ApiKeyInput
              label={intl.formatMessage({ id: "settings.cloudAsr.assemblyai" })}
              hasKey={settings.has_assemblyai_key}
              value={assemblyaiKey}
              onChange={setAssemblyaiKey}
              intl={intl}
            />
            <ApiKeyInput
              label={intl.formatMessage({ id: "settings.cloudAsr.deepgram" })}
              hasKey={settings.has_deepgram_key}
              value={deepgramKey}
              onChange={setDeepgramKey}
              intl={intl}
            />
            <ApiKeyInput
              label={intl.formatMessage({ id: "settings.cloudAsr.elevenlabs" })}
              hasKey={settings.has_elevenlabs_key}
              value={elevenlabsKey}
              onChange={setElevenlabsKey}
              intl={intl}
            />
            <ApiKeyInput
              label={intl.formatMessage({ id: "settings.cloudAsr.yandex" })}
              hasKey={settings.has_yandex_key}
              value={yandexKey}
              onChange={setYandexKey}
              intl={intl}
            />
          </CardContent>
        </Card>

        {/* LLM Settings */}
        <Card>
          <CardHeader>
            <CardTitle>{intl.formatMessage({ id: "settings.llm.title" })}</CardTitle>
            <CardDescription>{intl.formatMessage({ id: "settings.llm.description" })}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "settings.llm.provider.label" })}</Label>
                <Select value={postprocessingProvider} onValueChange={setPostprocessingProvider}>
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
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "settings.llm.model.label" })}</Label>
                <Select value={postprocessingModel} onValueChange={setPostprocessingModel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {postprocessingProvider === "gemini" ? (
                      <>
                        <SelectItem value="gemini-2.5-flash">{intl.formatMessage({ id: "settings.llm.model.gemini25flash" })}</SelectItem>
                        <SelectItem value="gemini-2.5-flash-lite">{intl.formatMessage({ id: "settings.llm.model.gemini25flashLite" })}</SelectItem>
                        <SelectItem value="gemini-3-flash-preview">{intl.formatMessage({ id: "settings.llm.model.gemini3flashPreview" })}</SelectItem>
                      </>
                    ) : (
                      <>
                        <SelectItem value="openai/gpt-4o-mini">{intl.formatMessage({ id: "settings.llm.model.gpt4oMini" })}</SelectItem>
                        <SelectItem value="anthropic/claude-3.5-haiku">{intl.formatMessage({ id: "settings.llm.model.claude35haiku" })}</SelectItem>
                        <SelectItem value="deepseek/deepseek-r1">{intl.formatMessage({ id: "settings.llm.model.deepseekR1" })}</SelectItem>
                        <SelectItem value="google/gemini-2.5-flash">{intl.formatMessage({ id: "settings.llm.model.gemini25flashViaOr" })}</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>{intl.formatMessage({ id: "settings.llm.legacy.label" })}</Label>
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
              <p className="text-xs text-muted-foreground">{intl.formatMessage({ id: "settings.llm.legacy.help" })}</p>
            </div>

            <ApiKeyInput
              label={intl.formatMessage({ id: "settings.llm.provider.gemini" })}
              hasKey={settings.has_gemini_key}
              value={geminiKey}
              onChange={setGeminiKey}
              intl={intl}
            />
            <ApiKeyInput
              label={intl.formatMessage({ id: "settings.llm.provider.openrouter" })}
              hasKey={settings.has_openrouter_key}
              value={openrouterKey}
              onChange={setOpenrouterKey}
              intl={intl}
            />
          </CardContent>
        </Card>

        {/* AI Insights Settings */}
        <Card>
          <CardHeader>
            <CardTitle>{intl.formatMessage({ id: "settings.insights.title" })}</CardTitle>
            <CardDescription>
              {intl.formatMessage({ id: "settings.insights.description" })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "label.provider" })}</Label>
                <Select value={insightsProvider} onValueChange={setInsightsProvider}>
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
              <div className="space-y-2">
                <Label>{intl.formatMessage({ id: "label.model" })}</Label>
                <Select value={insightsModel} onValueChange={setInsightsModel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {insightsProvider === "gemini" ? (
                      <>
                        <SelectItem value="gemini-2.5-flash">{intl.formatMessage({ id: "settings.llm.model.gemini25flash" })}</SelectItem>
                        <SelectItem value="gemini-2.5-flash-lite">{intl.formatMessage({ id: "settings.llm.model.gemini25flashLite" })}</SelectItem>
                        <SelectItem value="gemini-3-flash-preview">{intl.formatMessage({ id: "settings.llm.model.gemini3flashPreview" })}</SelectItem>
                      </>
                    ) : (
                      <>
                        <SelectItem value="openai/gpt-4o-mini">{intl.formatMessage({ id: "settings.llm.model.gpt4oMini" })}</SelectItem>
                        <SelectItem value="anthropic/claude-3.5-haiku">{intl.formatMessage({ id: "settings.llm.model.claude35haiku" })}</SelectItem>
                        <SelectItem value="deepseek/deepseek-r1">{intl.formatMessage({ id: "settings.llm.model.deepseekR1" })}</SelectItem>
                        <SelectItem value="google/gemini-2.5-flash">{intl.formatMessage({ id: "settings.llm.model.gemini25flashViaOr" })}</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              {intl.formatMessage({ id: "settings.insights.help" })}
            </p>
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
  intl,
}: {
  label: string;
  hasKey: boolean;
  value: string;
  onChange: (value: string) => void;
  intl: ReturnType<typeof useIntl>;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Label>{label}</Label>
        <Badge variant={hasKey ? "outline" : "secondary"}>
          {hasKey
            ? intl.formatMessage({ id: "badge.configured" })
            : intl.formatMessage({ id: "badge.notSet" })}
        </Badge>
      </div>
      <Input
        type="password"
        placeholder={hasKey ? "********" : `Enter ${label} API key`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
