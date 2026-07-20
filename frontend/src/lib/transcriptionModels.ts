export function formatTranscriptionModelLabel(model: string): string {
  if (model === "scribe_v1") return "Scribe v1";
  if (model === "scribe_v2") return "Scribe v2";
  return model;
}
