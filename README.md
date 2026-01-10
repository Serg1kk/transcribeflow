# TranscribeFlow

<!-- TODO: Add hero image here -->
<!-- ![TranscribeFlow Hero](./docs/hero.png) -->

> **Local AI-powered meeting transcription with speaker diarization and intelligent insights — optimized for Apple Silicon.**

Transform your audio recordings into structured, actionable knowledge without sending data to the cloud.

---

## Quick Start (5 Steps)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Clone  →  2. Configure  →  3. Start  →  4. Open  →  5. Use  │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1: Clone Repository
```bash
git clone https://github.com/Serg1kk/transcribeflow.git
cd transcribeflow
```

### Step 2: Get HuggingFace Token
1. Create account at [huggingface.co](https://huggingface.co)
2. Go to [Settings → Tokens](https://huggingface.co/settings/tokens) → Create token
3. Accept license at [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)

### Step 3: Configure & Start
```bash
cp .env.example .env
# Edit .env → add your HF token: TRANSCRIBEFLOW_HF_TOKEN=hf_xxx

./start.sh
```

### Step 4: Open Browser
```
Frontend:  http://localhost:3001
Backend:   http://localhost:8000
API Docs:  http://localhost:8000/docs
```

### Step 5: Upload & Transcribe
Drag-drop audio → Wait for processing → Get transcript with speakers!

---

## Processing Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           TRANSCRIBEFLOW PIPELINE                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│   │  AUDIO  │───▶│  WHISPER    │───▶│  PYANNOTE   │───▶│  TRANSCRIPT     │  │
│   │  FILE   │    │  (MLX ASR)  │    │ (SPEAKERS)  │    │  + SPEAKERS     │  │
│   └─────────┘    └─────────────┘    └─────────────┘    └────────┬────────┘  │
│                                                                  │           │
│                        LEVEL 1 POST-PROCESSING                   ▼           │
│                  ┌───────────────────────────────────────────────────────┐   │
│                  │  LLM CLEANUP: Fix ASR errors, merge fragments,        │   │
│                  │  identify speakers by name, clean filler words        │   │
│                  └───────────────────────────────────────────────────────┘   │
│                                                                  │           │
│                        LEVEL 2 AI INSIGHTS                       ▼           │
│                  ┌───────────────────────────────────────────────────────┐   │
│                  │  STRUCTURED EXTRACTION: Action items, decisions,      │   │
│                  │  blockers, key points + interactive MINDMAP           │   │
│                  └───────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Transcription
| Feature | Description |
|---------|-------------|
| **100% Local** | All processing on your Mac — no data leaves your machine |
| **MLX Whisper** | Apple Silicon optimized ASR (M1/M2/M3/M4) |
| **Speaker Diarization** | Pyannote Audio 3.1 identifies who said what |
| **Queue System** | Upload multiple files, process in background |
| **Multi-Format** | MP3, M4A, WAV, OGG, FLAC, WebM |

### LLM Post-Processing (Level 1)
| Feature | Description |
|---------|-------------|
| **ASR Cleanup** | Fix transcription errors using LLM |
| **Speaker Identification** | Auto-detect speaker names from context |
| **Fragment Merging** | Combine broken sentences |
| **Template System** | IT Meeting, Sales Call, Interview templates |

### AI Insights (Level 2)
| Feature | Description |
|---------|-------------|
| **Structured Extraction** | Action items, decisions, blockers, key points |
| **Interactive Mindmap** | Visual meeting overview with markmap.js |
| **6 Templates** | IT Meeting, Sales Call, Business Meeting, Interview, Retrospective, Brainstorm |
| **Original/Cleaned Source** | Generate insights from raw or cleaned transcript |

### LLM Providers
| Provider | Models |
|----------|--------|
| **Google Gemini** | gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3-flash-preview |
| **OpenRouter** | GPT-4o Mini, Claude 3.5 Haiku, DeepSeek R1, and more |

---

## Architecture

```
transcribeflow/
├── backend/                      # FastAPI (Python 3.12)
│   ├── api/
│   │   ├── transcribe.py         # Upload, queue, history
│   │   ├── postprocess.py        # Level 1: LLM cleanup
│   │   ├── insights.py           # Level 2: AI insights
│   │   └── settings.py           # Configuration API
│   ├── engines/
│   │   └── mlx_whisper.py        # Apple Silicon ASR
│   ├── services/
│   │   ├── postprocessing_service.py  # Cleanup logic
│   │   ├── insight_service.py         # Insights extraction
│   │   └── insight_template_service.py # Template management
│   ├── workers/
│   │   ├── transcription_worker.py    # ASR + diarization
│   │   └── queue_processor.py         # Background processing
│   └── models/
│       ├── transcription.py      # SQLAlchemy models
│       └── llm_operation.py      # LLM usage tracking
│
├── frontend/                     # Next.js 14 (App Router)
│   └── src/
│       ├── app/
│       │   ├── page.tsx          # Upload & queue
│       │   ├── settings/         # Configuration UI
│       │   └── transcription/[id]/ # Results viewer
│       └── components/
│           ├── TranscriptPanel.tsx    # Transcript display
│           ├── PostProcessingControls.tsx # Level 1 UI
│           ├── InsightsControls.tsx   # Level 2 UI
│           ├── InsightsPanel.tsx      # Insights display
│           └── MindmapViewer.tsx      # Interactive mindmap
│
└── start.sh                      # One-command startup
```

---

## Output Structure

```
~/Transcriptions/transcribed/2024-01-08_meeting/
├── meeting.mp3                   # Original audio
├── transcript.json               # Raw transcript + speakers
├── transcript.txt                # Human-readable format
├── transcript_cleaned.json       # Level 1: LLM-cleaned version
├── suggestions.json              # Speaker name suggestions
├── insights_it-meeting.json      # Level 2: Extracted insights
└── insights_log.json             # LLM operations log
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **ASR** | MLX Whisper (Apple Silicon optimized) |
| **Diarization** | Pyannote Audio 3.1 |
| **Backend** | FastAPI, SQLAlchemy, SQLite |
| **Frontend** | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| **Mindmap** | markmap-lib, markmap-view |
| **LLM** | Google Gemini API, OpenRouter |

---

## Requirements

- **macOS** with Apple Silicon (M1/M2/M3/M4)
- **Python** 3.12+
- **Node.js** 18+
- **HuggingFace** account (for Pyannote)
- **Gemini API key** (for post-processing, optional)

---

## Configuration

Settings are stored in `~/.transcribeflow/config.json` (UI-editable) or `.env`:

| Setting | Description | Default |
|---------|-------------|---------|
| `default_model` | Whisper model | `large-v3-turbo` |
| `diarization_method` | none / fast / accurate | `fast` |
| `compute_device` | auto / mps / cpu | `auto` |
| `postprocessing_provider` | gemini / openrouter | `gemini` |
| `insights_provider` | gemini / openrouter | `gemini` |

---

## API Endpoints

### Transcription
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transcribe/upload` | Upload audio file |
| GET | `/api/transcribe/queue` | List all transcriptions |
| GET | `/api/transcribe/{id}` | Get transcription details |
| GET | `/api/transcribe/{id}/transcript` | Get transcript data |

### Post-Processing (Level 1)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/postprocess/templates` | List cleanup templates |
| POST | `/api/postprocess/transcriptions/{id}` | Run LLM cleanup |
| GET | `/api/postprocess/transcriptions/{id}/cleaned` | Get cleaned transcript |

### AI Insights (Level 2)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/insights/templates` | List insight templates |
| POST | `/api/insights/transcriptions/{id}` | Generate insights |
| GET | `/api/insights/transcriptions/{id}/{template}` | Get insights |

Full API docs: http://localhost:8000/docs

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -v
```

**Test coverage:** 118 tests

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port in use | `lsof -ti:3001 \| xargs kill -9` |
| Diarization fails | Check HF token, accept Pyannote license |
| Database issues | `rm ~/.transcribeflow/transcribeflow.db` |
| MLX not found | `pip install mlx-whisper` |

---

## Roadmap

- [ ] Cloud ASR providers (AssemblyAI, Deepgram, ElevenLabs)
- [ ] Real-time streaming transcription
- [ ] Meeting summary export (PDF, Notion)
- [ ] Custom insight templates
- [ ] Multi-language support improvements

---

## License

MIT

---

## Contributing

1. Fork → 2. Branch → 3. Code → 4. Test (`pytest -v`) → 5. PR

