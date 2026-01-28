# services/insight_template_service.py
"""Insight template management service for Level 2 post-processing."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from config import get_settings


@dataclass
class InsightTemplate:
    """AI Insights template for Level 2 post-processing."""
    id: str
    name: str
    description: str
    include_mindmap: bool
    sections: List[Dict[str, str]]
    system_prompt: str
    temperature: float


# Baseline system prompt for insights extraction
INSIGHTS_BASELINE_PROMPT = """You are an expert meeting analyst. Your task is to extract structured insights from a meeting transcript.

## INPUT FORMAT
The transcript contains timestamped dialogue:
[HH:MM:SS] SPEAKER_XX: text

## LANGUAGE HANDLING
- The transcript may contain mixed Russian and English (code-switching)
- Analyze meaning in both languages
- Generate output in the SAME primary language as the input
- Preserve technical terms and proper nouns

## OUTPUT FORMAT (STRICT JSON)
Return a JSON object with the following structure:

```json
{{
  "description": "Brief 1-2 sentence summary of the meeting",
  "sections": [
    {{
      "id": "section_id",
      "title": "Section Title",
      "content": "Markdown formatted content..."
    }}
  ],
  "mindmap": {{
    "format": "markdown",
    "content": "# Root Topic\\n\\n## Branch 1\\n- Item 1\\n- Item 2\\n\\n## Branch 2\\n- Item 3"
  }}
}}
```

## SECTION REQUIREMENTS
{section_instructions}

## MINDMAP REQUIREMENTS (if requested)
{mindmap_instructions}

Generate the mindmap in standard Markdown format with headings (#, ##) and lists (-, *).
The mindmap should capture the hierarchical structure of the discussion.

## QUALITY RULES
1. Be specific - use names, dates, numbers from the transcript
2. Quote relevant phrases for action items and decisions
3. If something is unclear, note the uncertainty
4. Don't invent information not present in the transcript

Return ONLY the JSON object, no explanations."""


def _build_section_instructions(sections: List[Dict[str, str]]) -> str:
    """Build section-specific instructions for the prompt."""
    instructions = ["Generate the following sections:\n"]
    for section in sections:
        instructions.append(f"- **{section['title']}** ({section['id']}): {section['description']}")
    return "\n".join(instructions)


def _build_mindmap_instructions(include_mindmap: bool) -> str:
    """Build mindmap instructions for the prompt."""
    if include_mindmap:
        return """Create a hierarchical mindmap that:
- Has a clear root node (meeting topic)
- Contains 4-6 main branches (key themes)
- Decomposes into 2-3 levels of detail
- Uses concise node labels (1-5 words)"""
    return "Mindmap is NOT required. Set mindmap to null in the response."


# Default insight templates
DEFAULT_INSIGHT_TEMPLATES = [
    InsightTemplate(
        id="it-meeting",
        name="IT Meeting",
        description="Standups, sprint reviews, architecture discussions",
        include_mindmap=True,
        sections=[
            {"id": "decisions", "title": "Key Decisions", "description": "Technical and process decisions made during the meeting"},
            {"id": "blockers", "title": "Blockers", "description": "Issues blocking progress, dependencies, risks"},
            {"id": "action_items", "title": "Action Items", "description": "Tasks with assignees (@name) and deadlines if mentioned"},
            {"id": "technical_notes", "title": "Technical Notes", "description": "Architecture decisions, code discussions, tech debt notes"},
        ],
        system_prompt="",  # Will be built dynamically
        temperature=0.3
    ),
    InsightTemplate(
        id="sales-call",
        name="Sales Call",
        description="Client calls, sales meetings, demos",
        include_mindmap=False,
        sections=[
            {"id": "pain_points", "title": "Pain Points", "description": "Customer problems and challenges mentioned"},
            {"id": "objections", "title": "Objections", "description": "Concerns, pushback, reasons for hesitation"},
            {"id": "next_steps", "title": "Next Steps", "description": "Agreed follow-up actions and timeline"},
            {"id": "competitor_mentions", "title": "Competitor Mentions", "description": "Any references to competing solutions"},
        ],
        system_prompt="",
        temperature=0.3
    ),
    InsightTemplate(
        id="business-meeting",
        name="Business Meeting",
        description="Strategic discussions, planning sessions",
        include_mindmap=True,
        sections=[
            {"id": "key_decisions", "title": "Key Decisions", "description": "Strategic and business decisions made"},
            {"id": "action_items", "title": "Action Items", "description": "Tasks with owners and deadlines"},
            {"id": "stakeholder_concerns", "title": "Stakeholder Concerns", "description": "Issues raised by participants"},
            {"id": "follow_ups", "title": "Follow-ups", "description": "Items requiring future discussion or review"},
        ],
        system_prompt="",
        temperature=0.3
    ),
    InsightTemplate(
        id="interview",
        name="Interview",
        description="Job interviews, candidate assessments",
        include_mindmap=False,
        sections=[
            {"id": "candidate_assessment", "title": "Candidate Assessment", "description": "Key strengths, weaknesses, and fit evaluation"},
            {"id": "key_qa", "title": "Key Q&A", "description": "Important questions asked and candidate's responses"},
            {"id": "red_green_flags", "title": "Red/Green Flags", "description": "Positive indicators and concerns noted"},
        ],
        system_prompt="",
        temperature=0.3
    ),
    InsightTemplate(
        id="retrospective",
        name="Retrospective",
        description="Sprint retros, post-mortems, team reviews",
        include_mindmap=True,
        sections=[
            {"id": "wins", "title": "Wins", "description": "What went well, successes, positive outcomes"},
            {"id": "issues", "title": "Issues", "description": "What went wrong, problems, challenges faced"},
            {"id": "action_plan", "title": "Action Plan", "description": "Specific improvements and who will implement them"},
            {"id": "team_sentiment", "title": "Team Sentiment", "description": "Overall mood, concerns about workload, morale"},
        ],
        system_prompt="",
        temperature=0.3
    ),
    InsightTemplate(
        id="brainstorm",
        name="Brainstorm",
        description="Ideation sessions, creative discussions",
        include_mindmap=True,
        sections=[
            {"id": "ideas", "title": "Ideas", "description": "All ideas proposed, categorized by theme if possible"},
            {"id": "decisions", "title": "Decisions", "description": "Which ideas were selected or prioritized"},
            {"id": "next_steps", "title": "Next Steps", "description": "How to move forward with selected ideas"},
        ],
        system_prompt="",
        temperature=0.4
    ),
    InsightTemplate(
        id="podcast",
        name="Podcast",
        description="Audio shows, conversations, long-form discussions",
        include_mindmap=True,
        sections=[
            {"id": "key_topics", "title": "Key Topics", "description": "Main themes and subjects discussed in the episode"},
            {"id": "notable_insights", "title": "Notable Insights", "description": "Interesting ideas, opinions, and perspectives shared"},
            {"id": "recommendations", "title": "Recommendations", "description": "Books, tools, resources, people mentioned by guests/hosts"},
            {"id": "takeaways", "title": "Key Takeaways", "description": "Main conclusions and actionable advice from the episode"},
        ],
        system_prompt="",
        temperature=0.4
    ),
    InsightTemplate(
        id="design-call",
        name="Design Call",
        description="UI/UX design reviews, mockup discussions",
        include_mindmap=True,
        sections=[
            {"id": "design_decisions", "title": "Design Decisions", "description": "UI/UX decisions made - layout choices, component selection, visual direction"},
            {"id": "feedback", "title": "Feedback & Iterations", "description": "Comments on mockups, requested changes, alternative options discussed"},
            {"id": "open_questions", "title": "Open Questions", "description": "Unresolved design questions, items needing user research or stakeholder input"},
            {"id": "action_items", "title": "Action Items", "description": "Tasks for designer (@name) - mockup updates, new screens, asset preparation"},
        ],
        system_prompt="",
        temperature=0.3
    ),
    InsightTemplate(
        id="pre-grooming",
        name="Pre-grooming",
        description="Requirements clarification, technical feasibility",
        include_mindmap=True,
        sections=[
            {"id": "clarified_requirements", "title": "Clarified Requirements", "description": "TBD items resolved, acceptance criteria defined, edge cases covered"},
            {"id": "technical_approach", "title": "Technical Approach", "description": "Implementation options discussed, chosen approach with rationale"},
            {"id": "decomposition", "title": "Preliminary Decomposition", "description": "High-level breakdown into subtasks, dependencies identified"},
            {"id": "open_items", "title": "Open Items", "description": "Remaining TBDs, items needing stakeholder decision, blocked topics"},
            {"id": "agreements", "title": "Agreements", "description": "Key decisions and consensus reached between PM and dev team"},
        ],
        system_prompt="",
        temperature=0.3
    ),
    InsightTemplate(
        id="grooming",
        name="Grooming",
        description="Story point estimation, sprint planning",
        include_mindmap=True,
        sections=[
            {"id": "estimated_stories", "title": "Estimated Stories", "description": "User stories discussed with final story point estimates (e.g., 'US-123: 5 SP')"},
            {"id": "estimation_rationale", "title": "Estimation Rationale", "description": "Key factors affecting estimates - complexity, unknowns, dependencies, tech debt"},
            {"id": "scope_concerns", "title": "Scope Concerns", "description": "Stories flagged as too large, unclear, or needing decomposition"},
            {"id": "qa_considerations", "title": "QA Considerations", "description": "Testing concerns, edge cases for QA, automation needs"},
            {"id": "sprint_readiness", "title": "Sprint Readiness", "description": "Stories ready for sprint, blocked stories, missing acceptance criteria"},
        ],
        system_prompt="",
        temperature=0.3
    ),
    InsightTemplate(
        id="feature-discussion",
        name="Feature Discussion",
        description="1-on-1 feature explanations with developers or QA",
        include_mindmap=True,
        sections=[
            {"id": "feature_scope", "title": "Feature Scope", "description": "What is included and excluded from the feature, boundaries, MVP vs future phases"},
            {"id": "context_shared", "title": "Context & Background", "description": "Business reasoning, history of decisions, why things are done a certain way, stakeholder context"},
            {"id": "requirements_clarified", "title": "Requirements Clarified", "description": "Specific requirements discussed, acceptance criteria mentioned, edge cases covered"},
            {"id": "tickets_mentioned", "title": "Tickets & References", "description": "Epics, user stories, tickets, PRs mentioned with their context"},
            {"id": "open_questions", "title": "Open Questions", "description": "Questions that remained unanswered or need further clarification from stakeholders"},
            {"id": "action_items", "title": "Action Items", "description": "Tasks for participants (@name) after the call - testing, development, follow-ups"},
        ],
        system_prompt="",
        temperature=0.3
    ),
]


class InsightTemplateService:
    """Service for managing AI Insights templates."""

    def __init__(self, templates_path: Optional[Path] = None):
        if templates_path is None:
            settings = get_settings()
            self.templates_path = settings.insight_templates_path
        else:
            self.templates_path = templates_path

        self._ensure_defaults()

    def _build_system_prompt(self, template: InsightTemplate) -> str:
        """Build the complete system prompt for a template."""
        section_instructions = _build_section_instructions(template.sections)
        mindmap_instructions = _build_mindmap_instructions(template.include_mindmap)

        return INSIGHTS_BASELINE_PROMPT.format(
            section_instructions=section_instructions,
            mindmap_instructions=mindmap_instructions
        )

    def _ensure_defaults(self):
        """Ensure default templates exist."""
        self.templates_path.mkdir(parents=True, exist_ok=True)

        for template in DEFAULT_INSIGHT_TEMPLATES:
            template_file = self.templates_path / f"{template.id}.json"
            if not template_file.exists():
                # Build system prompt before saving
                template_with_prompt = InsightTemplate(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    include_mindmap=template.include_mindmap,
                    sections=template.sections,
                    system_prompt=self._build_system_prompt(template),
                    temperature=template.temperature
                )
                self._save_template(template_with_prompt)

    def _save_template(self, template: InsightTemplate):
        """Save template to disk."""
        template_file = self.templates_path / f"{template.id}.json"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "include_mindmap": template.include_mindmap,
                "sections": template.sections,
                "system_prompt": template.system_prompt,
                "temperature": template.temperature,
            }, f, ensure_ascii=False, indent=2)

    def _load_template(self, template_file: Path) -> Optional[InsightTemplate]:
        """Load template from disk."""
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return InsightTemplate(
                id=data["id"],
                name=data["name"],
                description=data["description"],
                include_mindmap=data["include_mindmap"],
                sections=data["sections"],
                system_prompt=data["system_prompt"],
                temperature=data["temperature"],
            )
        except (json.JSONDecodeError, KeyError, IOError):
            return None

    def list_templates(self) -> List[InsightTemplate]:
        """List all available insight templates."""
        templates = []
        for template_file in self.templates_path.glob("*.json"):
            template = self._load_template(template_file)
            if template:
                templates.append(template)
        return sorted(templates, key=lambda t: t.name)

    def get_template(self, template_id: str) -> Optional[InsightTemplate]:
        """Get a template by ID."""
        template_file = self.templates_path / f"{template_id}.json"
        if template_file.exists():
            return self._load_template(template_file)
        return None

    def create_template(self, template: InsightTemplate) -> InsightTemplate:
        """Create a new template."""
        self._save_template(template)
        return template

    def update_template(self, template: InsightTemplate) -> InsightTemplate:
        """Update an existing template."""
        self._save_template(template)
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template. Returns True if deleted, False if not found or is default."""
        if template_id in [t.id for t in DEFAULT_INSIGHT_TEMPLATES]:
            return False

        template_file = self.templates_path / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()
            return True
        return False
