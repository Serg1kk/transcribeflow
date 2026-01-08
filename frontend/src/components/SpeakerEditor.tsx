// components/SpeakerEditor.tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { updateSpeakerNames } from "@/lib/api";

interface Speaker {
  id: string;
  name: string;
  color: string;
}

interface SpeakerEditorProps {
  transcriptionId: string;
  speakers: Record<string, { name: string; color: string }>;
  onUpdate?: (speakers: Record<string, { name: string; color: string }>) => void;
}

export function SpeakerEditor({
  transcriptionId,
  speakers: initialSpeakers,
  onUpdate,
}: SpeakerEditorProps) {
  const [speakers, setSpeakers] = useState<Speaker[]>(
    Object.entries(initialSpeakers).map(([id, data]) => ({
      id,
      name: data.name,
      color: data.color,
    }))
  );
  const [isSaving, setIsSaving] = useState(false);

  const handleNameChange = (id: string, name: string) => {
    setSpeakers((prev) =>
      prev.map((s) => (s.id === id ? { ...s, name } : s))
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const speakerNames = Object.fromEntries(
        speakers.map((s) => [s.id, s.name])
      );
      await updateSpeakerNames(transcriptionId, speakerNames);

      // Notify parent of update
      const updatedSpeakers = Object.fromEntries(
        speakers.map((s) => [s.id, { name: s.name, color: s.color }])
      );
      onUpdate?.(updatedSpeakers);
    } catch (error) {
      console.error("Failed to save speaker names:", error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="font-medium">Participants (click to edit)</h3>
      <div className="space-y-2">
        {speakers.map((speaker) => (
          <div key={speaker.id} className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded-full shrink-0"
              style={{ backgroundColor: speaker.color }}
            />
            <span className="text-sm text-muted-foreground w-24 shrink-0">
              {speaker.id}
            </span>
            <span className="text-muted-foreground">→</span>
            <Input
              value={speaker.name}
              onChange={(e) => handleNameChange(speaker.id, e.target.value)}
              className="w-40"
            />
          </div>
        ))}
      </div>
      <Button onClick={handleSave} disabled={isSaving}>
        {isSaving ? "Saving..." : "Apply Names"}
      </Button>
    </div>
  );
}
