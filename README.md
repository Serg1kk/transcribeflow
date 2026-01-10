# TranscribeFlow

![TranscribeFlow Hero](./docs/hero.png)

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

> **Note:** On first run, you may see errors about model access. You need to visit these HuggingFace model pages and click "Agree" to accept their licenses (one-time operation):
> - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
> - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

### Step 3: Configure & Start
```bash
cp .env.example .env
# Edit .env → add your HF token: TRANSCRIBEFLOW_HF_TOKEN=hf_xxx

./start.sh
```

### Step 4: Open Browser
```
Frontend:  http://localhost:3000  (exact port shown in console)
Backend:   http://localhost:8000
API Docs:  http://localhost:8000/docs
```

### Step 5: Upload & Transcribe
Drag-drop audio → Wait for processing → Get transcript with speakers!

---

## Important Notes

### No Apple Silicon? Use Cloud Transcription

Local transcription with MLX Whisper requires **Apple Silicon Mac (M1/M2/M3/M4)**.

If you have:
- Windows/Linux machine
- Intel Mac
- Older/weaker hardware

You can use **cloud transcription providers** instead:

| Provider | Description | Setup |
|----------|-------------|-------|
| **ElevenLabs** | High-quality ASR | Get API key at [elevenlabs.io](https://elevenlabs.io) |
| **Deepgram** | Fast and accurate | Get API key at [deepgram.com](https://deepgram.com) |
| **AssemblyAI** | Feature-rich ASR | Get API key at [assemblyai.com](https://assemblyai.com) |
| **Yandex SpeechKit** | Good for Russian | Get API key at [cloud.yandex.ru](https://cloud.yandex.ru) |

Add your API key in Settings page or `.env` file, then select the provider when uploading.

### LLM API Keys for Post-Processing

To use **LLM Post-Processing** (cleanup) and **AI Insights** features, you need an API key:

| Provider | How to get | Cost |
|----------|------------|------|
| **Google Gemini** (recommended) | [aistudio.google.com](https://aistudio.google.com) → Get API Key | Free tier available |
| **OpenRouter** | [openrouter.ai](https://openrouter.ai) → Keys | Pay-per-use, many models |

Add your key in **Settings** page after starting the app.

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
| **Cloud ASR** | ElevenLabs, Deepgram, AssemblyAI, Yandex (for non-Apple hardware) |
| **Speaker Diarization** | Pyannote Audio 3.1 identifies who said what |
| **Queue System** | Upload multiple files, process in background |
| **Multi-Format** | MP3, M4A, WAV, OGG, FLAC, WebM |

### LLM Post-Processing (Level 1)
| Feature | Description |
|---------|-------------|
| **ASR Cleanup** | Fix transcription errors using LLM |
| **Speaker Identification** | LLM detects names and/or roles from context (e.g., "Seller & Client", "Developer & Designer"). Suggestions appear in UI — apply, reject, or edit as you like |
| **Fragment Merging** | Combine broken sentences |
| **Comparison View** | Side-by-side diff between original and cleaned transcript to see what changed |
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

## Settings (Available in UI)

After starting the app, go to **http://localhost:3000/settings** to configure:

### Transcription Settings
| Setting | Options | Description |
|---------|---------|-------------|
| Default Engine | MLX Whisper, ElevenLabs, Deepgram, AssemblyAI, Yandex | ASR engine to use |
| Default Model | tiny, base, small, medium, large-v2, large-v3, large-v3-turbo | Whisper model size |
| Diarization Method | None, Fast (GPU), Accurate | Speaker detection mode |
| Compute Device | Auto, MPS (GPU), CPU | For local processing |
| Min/Max Speakers | 1-10 | Expected speaker count |

**Model recommendations:**
- **M1 Pro / M1 Max / M2 Pro+ / M3 Pro+** → Use `large-v3` for best transcription quality
- **MacBook Air / base M1/M2/M3** → Use `large-v3-turbo` (faster, slightly less accurate)
- If transcription feels slow or machine overheats → try smaller model or `turbo` variant

**Compute device recommendations:**
- **M1 Pro and higher** → `MPS (GPU)` works great, significantly faster diarization
- **MacBook Air / weaker machines** → Switch to `CPU` if you experience freezing or overheating

### Whisper Quality Settings
Fine-tune to prevent hallucinations (e.g., "Субтитры сделал DimaTorzok" during silence):
- No Speech Threshold
- Log Probability Threshold
- Compression Ratio Threshold
- Hallucination Silence Threshold

### LLM Settings
| Setting | Options | Description |
|---------|---------|-------------|
| Post-Processing Provider | Gemini, OpenRouter | For Level 1 cleanup |
| Post-Processing Model | gemini-2.5-flash, etc. | Model to use |
| Insights Provider | Gemini, OpenRouter | For Level 2 insights |
| Insights Model | gemini-2.5-flash, etc. | Model to use |

### API Keys
Configure in Settings page:
- HuggingFace Token (required for diarization)
- Gemini API Key (for LLM features)
- OpenRouter API Key (alternative LLM provider)
- Cloud ASR keys (ElevenLabs, Deepgram, AssemblyAI, Yandex)

### Template System
Both Level 1 and Level 2 processing use templates:

**Level 1 (Cleanup) Templates:**
- IT Meeting, Sales Call, Interview, etc.

**Level 2 (Insights) Templates:**
- IT Meeting (with mindmap)
- Sales Call
- Business Meeting (with mindmap)
- Interview
- Retrospective (with mindmap)
- Brainstorm (with mindmap)

Templates define what sections to extract and whether to generate a mindmap.

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
│   │   ├── mlx_whisper.py        # Apple Silicon ASR
│   │   ├── elevenlabs.py         # Cloud ASR
│   │   ├── deepgram.py           # Cloud ASR
│   │   ├── assemblyai.py         # Cloud ASR
│   │   └── yandex.py             # Cloud ASR
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
| **ASR** | MLX Whisper (local) / ElevenLabs, Deepgram, AssemblyAI, Yandex (cloud) |
| **Diarization** | Pyannote Audio 3.1 |
| **Backend** | FastAPI, SQLAlchemy, SQLite |
| **Frontend** | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| **Mindmap** | markmap-lib, markmap-view |
| **LLM** | Google Gemini API, OpenRouter |

---

## Requirements

**Minimum:**
- **Python** 3.12+
- **Node.js** 18+

**For local transcription:**
- **macOS** with Apple Silicon (M1/M2/M3/M4)
- **HuggingFace** account (for Pyannote diarization)

**For cloud transcription:**
- API key from ElevenLabs, Deepgram, AssemblyAI, or Yandex

**For LLM features (optional):**
- **Gemini API key** or **OpenRouter API key**

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
| Port in use | `lsof -ti:3000 \| xargs kill -9` |
| Diarization fails | Check HF token, accept Pyannote license |
| HuggingFace model errors | Visit model pages and click "Agree" to accept licenses |
| Database issues | `rm ~/.transcribeflow/transcribeflow.db` |
| MLX not found | `pip install mlx-whisper` |
| LLM features not working | Add Gemini or OpenRouter API key in Settings |

---

## Roadmap

- [ ] Real-time streaming transcription
- [ ] Meeting summary export (PDF, Notion)
- [ ] Custom insight templates (user-editable)
- [ ] Multi-language support improvements
- [ ] Batch processing improvements

---

## License

MIT — Free to use, modify, and distribute. Just keep the copyright notice.

---

## Contributing

1. Fork → 2. Branch → 3. Code → 4. Test (`pytest -v`) → 5. PR

