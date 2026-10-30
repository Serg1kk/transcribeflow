"""Shared strict JSON schemas for transcript AI operations."""
from copy import deepcopy

def _object(properties: dict, required: list) -> dict:
    return {"type": "object", "properties": properties, "required": required,
            "additionalProperties": False}


_SPEAKER = _object({
    "speaker_id": {"type": "string"},
    "name": {"type": ["string", "null"]},
    "name_confidence": {"type": "number"},
    "name_reason": {"type": ["string", "null"]},
    "role": {"type": ["string", "null"]},
    "role_confidence": {"type": "number"},
    "role_reason": {"type": ["string", "null"]},
}, ["speaker_id", "name", "name_confidence", "name_reason", "role", "role_confidence", "role_reason"])
_SUGGESTIONS = {"type": "array", "items": _SPEAKER}
RESPONSE_SCHEMAS = {
    "cleanup": _object({
        "segments": {"type": "array", "items": _object({
            "start": {"type": "number"}, "speaker": {"type": "string"}, "text": {"type": "string"},
        }, ["start", "speaker", "text"])},
        "speaker_suggestions": _SUGGESTIONS,
    }, ["segments", "speaker_suggestions"]),
    "speakers": _object({"speaker_suggestions": _SUGGESTIONS}, ["speaker_suggestions"]),
    "insights": _object({
        "description": {"type": "string"},
        "sections": {"type": "array", "items": _object({
            "id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"},
        }, ["id", "title", "content"])},
        "mindmap": _object({"format": {"type": "string", "enum": ["markdown"]},
                            "content": {"type": "string"}}, ["format", "content"]),
    }, ["description", "sections", "mindmap"]),
}
# A template that requests a mindmap must not silently receive null. Keep the
# explicit no-mindmap template path separate rather than relaxing both schemas.
RESPONSE_SCHEMAS["insights_no_mindmap"] = deepcopy(RESPONSE_SCHEMAS["insights"])
RESPONSE_SCHEMAS["insights_no_mindmap"]["properties"]["mindmap"] = {"type": "null"}
