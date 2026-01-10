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
import { Lightbulb, Check, X } from "lucide-react";
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
  // Track saved values for dirty detection
  const [savedNames, setSavedNames] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(initialSpeakers).map(([id, data]) => [id, data.name]))
  );
  // Track which speakers are currently saving
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set());
  // Track which speakers just saved (for green flash)
  const [justSavedIds, setJustSavedIds] = useState<Set<string>>(new Set());
  // Track if applying all suggestions
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

  const saveSpeaker = async (speakerId: string, name: string) => {
    setSavingIds(prev => new Set(prev).add(speakerId));
    try {
      await updateSpeakerNames(transcriptionId, { [speakerId]: name });
      setSavedNames(prev => ({ ...prev, [speakerId]: name }));

      // Flash green for 300ms
      setJustSavedIds(prev => new Set(prev).add(speakerId));
      setTimeout(() => {
        setJustSavedIds(prev => {
          const next = new Set(prev);
          next.delete(speakerId);
          return next;
        });
      }, 300);

      // Notify parent
      const updatedSpeakers = Object.fromEntries(
        speakers.map((s) => [
          s.id,
          { name: s.id === speakerId ? name : s.name, color: s.color },
        ])
      );
      onUpdate?.(updatedSpeakers);
    } catch (error) {
      console.error("Failed to save speaker name:", error);
    } finally {
      setSavingIds(prev => {
        const next = new Set(prev);
        next.delete(speakerId);
        return next;
      });
    }
  };

  const handleApplySuggestion = async (speakerId: string) => {
    const suggestion = suggestions.find((s) => s.speaker_id === speakerId);
    if (!suggestion) return;

    // Update input value
    setSpeakers((prev) =>
      prev.map((s) =>
        s.id === speakerId ? { ...s, name: suggestion.display_name } : s
      )
    );
    // Remove suggestion from list
    setSuggestions((prev) => prev.filter((s) => s.speaker_id !== speakerId));

    // Save immediately
    await saveSpeaker(speakerId, suggestion.display_name);
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

  const handleDismissSuggestion = (speakerId: string) => {
    setSuggestions((prev) => prev.filter((s) => s.speaker_id !== speakerId));
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
                <span className="text-sm text-muted-foreground w-36 shrink-0 truncate" title={speaker.id}>
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
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-muted-foreground hover:text-destructive"
                      onClick={() => handleDismissSuggestion(speaker.id)}
                      title="Dismiss suggestion"
                    >
                      <X className="h-3.5 w-3.5" />
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
