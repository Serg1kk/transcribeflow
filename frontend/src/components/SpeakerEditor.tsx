// components/SpeakerEditor.tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Lightbulb, Check } from "lucide-react";
import {
  updateSpeakerNames,
  getSpeakerSuggestions,
  applySpeakerSuggestion,
  applyAllSpeakerSuggestions,
  SpeakerSuggestion,
} from "@/lib/api";

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
  const [suggestions, setSuggestions] = useState<SpeakerSuggestion[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isApplyingAll, setIsApplyingAll] = useState(false);

  // Load suggestions on mount
  useEffect(() => {
    async function loadSuggestions() {
      const data = await getSpeakerSuggestions(transcriptionId);
      if (data) {
        setSuggestions(data.suggestions.filter((s) => !s.applied && s.display_name));
      }
    }
    loadSuggestions();
  }, [transcriptionId]);

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

  const handleApplySuggestion = async (speakerId: string) => {
    try {
      await applySpeakerSuggestion(transcriptionId, speakerId);

      // Update local state
      const suggestion = suggestions.find((s) => s.speaker_id === speakerId);
      if (suggestion) {
        setSpeakers((prev) =>
          prev.map((s) =>
            s.id === speakerId ? { ...s, name: suggestion.display_name } : s
          )
        );
        setSuggestions((prev) => prev.filter((s) => s.speaker_id !== speakerId));

        // Notify parent
        const updatedSpeakers = Object.fromEntries(
          speakers.map((s) => [
            s.id,
            {
              name: s.id === speakerId ? suggestion.display_name : s.name,
              color: s.color,
            },
          ])
        );
        onUpdate?.(updatedSpeakers);
      }
    } catch (error) {
      console.error("Failed to apply suggestion:", error);
    }
  };

  const handleApplyAll = async () => {
    setIsApplyingAll(true);
    try {
      await applyAllSpeakerSuggestions(transcriptionId);

      // Update local state with all suggestions
      const suggestionMap = new Map(
        suggestions.map((s) => [s.speaker_id, s.display_name])
      );

      setSpeakers((prev) =>
        prev.map((s) => ({
          ...s,
          name: suggestionMap.get(s.id) || s.name,
        }))
      );
      setSuggestions([]);

      // Notify parent
      const updatedSpeakers = Object.fromEntries(
        speakers.map((s) => [
          s.id,
          {
            name: suggestionMap.get(s.id) || s.name,
            color: s.color,
          },
        ])
      );
      onUpdate?.(updatedSpeakers);
    } catch (error) {
      console.error("Failed to apply all suggestions:", error);
    } finally {
      setIsApplyingAll(false);
    }
  };

  const getSuggestionForSpeaker = (speakerId: string) => {
    return suggestions.find((s) => s.speaker_id === speakerId);
  };

  const getConfidenceColor = (suggestion: SpeakerSuggestion) => {
    const maxConf = Math.max(suggestion.name_confidence, suggestion.role_confidence);
    if (maxConf >= 0.8) return "text-green-600";
    if (maxConf >= 0.5) return "text-yellow-600";
    return "text-gray-400";
  };

  const getConfidenceBgColor = (suggestion: SpeakerSuggestion) => {
    const maxConf = Math.max(suggestion.name_confidence, suggestion.role_confidence);
    if (maxConf >= 0.8) return "bg-green-50 border-green-200";
    if (maxConf >= 0.5) return "bg-yellow-50 border-yellow-200";
    return "bg-gray-50 border-gray-200";
  };

  const buildTooltipContent = (suggestion: SpeakerSuggestion) => {
    const lines: string[] = [];
    if (suggestion.name && suggestion.name_reason) {
      lines.push(`Name: ${suggestion.name_reason} (${Math.round(suggestion.name_confidence * 100)}%)`);
    }
    if (suggestion.role && suggestion.role_reason) {
      lines.push(`Role: ${suggestion.role_reason} (${Math.round(suggestion.role_confidence * 100)}%)`);
    }
    return lines.join("\n");
  };

  const pendingSuggestionsCount = suggestions.length;

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Participants (click to edit)</h3>
          {pendingSuggestionsCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleApplyAll}
              disabled={isApplyingAll}
            >
              {isApplyingAll ? "Applying..." : `Apply All (${pendingSuggestionsCount})`}
            </Button>
          )}
        </div>
        <div className="space-y-2">
          {speakers.map((speaker) => {
            const suggestion = getSuggestionForSpeaker(speaker.id);
            return (
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
                {suggestion && (
                  <div
                    className={`flex items-center gap-2 px-2 py-1 rounded border ${getConfidenceBgColor(
                      suggestion
                    )}`}
                  >
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex items-center gap-1 cursor-help">
                          <Lightbulb
                            className={`h-4 w-4 ${getConfidenceColor(suggestion)}`}
                          />
                          <span className={`text-sm ${getConfidenceColor(suggestion)}`}>
                            {suggestion.display_name}
                          </span>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <pre className="text-xs whitespace-pre-wrap">
                          {buildTooltipContent(suggestion)}
                        </pre>
                      </TooltipContent>
                    </Tooltip>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => handleApplySuggestion(speaker.id)}
                      title="Apply suggestion"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? "Saving..." : "Apply Names"}
        </Button>
      </div>
    </TooltipProvider>
  );
}
