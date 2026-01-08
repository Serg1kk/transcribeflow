// app/settings/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Settings {
  default_engine: string;
  default_model: string;
  diarization_enabled: boolean;
  min_speakers: number;
  max_speakers: number;
  has_hf_token: boolean;
  has_assemblyai_key: boolean;
  has_elevenlabs_key: boolean;
  has_openai_key: boolean;
  has_deepgram_key: boolean;
  has_gemini_key: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/settings`)
      .then((res) => res.json())
      .then(setSettings)
      .catch(console.error);
  }, []);

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
        ← Back
      </Link>

      <h1 className="text-3xl font-bold mb-8">Settings</h1>

      <div className="space-y-6">
        {/* Transcription Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Transcription</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Default Engine</p>
                <p className="font-medium">{settings.default_engine}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Default Model</p>
                <p className="font-medium">{settings.default_model}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Diarization Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Diarization</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant={settings.diarization_enabled ? "default" : "secondary"}>
                {settings.diarization_enabled ? "Enabled" : "Disabled"}
              </Badge>
              <Badge variant={settings.has_hf_token ? "outline" : "destructive"}>
                HuggingFace Token: {settings.has_hf_token ? "OK" : "Missing"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Min Speakers</p>
                <p className="font-medium">{settings.min_speakers}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Max Speakers</p>
                <p className="font-medium">{settings.max_speakers}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* API Keys Status */}
        <Card>
          <CardHeader>
            <CardTitle>API Keys</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <ApiKeyStatus name="AssemblyAI" configured={settings.has_assemblyai_key} />
              <ApiKeyStatus name="ElevenLabs" configured={settings.has_elevenlabs_key} />
              <ApiKeyStatus name="OpenAI" configured={settings.has_openai_key} />
              <ApiKeyStatus name="Deepgram" configured={settings.has_deepgram_key} />
              <ApiKeyStatus name="Google Gemini" configured={settings.has_gemini_key} />
            </div>
            <p className="text-sm text-muted-foreground mt-4">
              Configure keys in .env file or ~/.transcribeflow/config.json
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

function ApiKeyStatus({ name, configured }: { name: string; configured: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span>{name}</span>
      <Badge variant={configured ? "outline" : "secondary"}>
        {configured ? "Configured" : "Not configured"}
      </Badge>
    </div>
  );
}
