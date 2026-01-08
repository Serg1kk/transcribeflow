# TranscribeFlow

Local meeting transcription with speaker diarization, optimized for Apple Silicon.

## Features

- **Local Processing** - All transcription happens on your machine, no data leaves your computer
- **MLX Whisper** - Fast transcription using Apple Silicon optimized Whisper models
- **Speaker Diarization** - Automatic speaker identification using Pyannote Audio 3.1
- **Speaker Editor** - Rename speakers after transcription for better readability
- **Multiple Formats** - Export transcripts as JSON or TXT
- **Queue System** - Upload multiple files and process them in background
- **Modern UI** - Clean Next.js frontend with shadcn/ui components

## Tech Stack

**Backend:**
- FastAPI (Python 3.12+)
- SQLite database
- MLX Whisper for ASR
- Pyannote Audio for speaker diarization

**Frontend:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui components

## Requirements

- macOS with Apple Silicon (M1/M2/M3)
- Python 3.12+
- Node.js 18+
- HuggingFace account (for Pyannote diarization)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Serg1kk/transcribeflow.git
cd transcribeflow
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your HuggingFace token:

```env
TRANSCRIBEFLOW_HF_TOKEN=your_huggingface_token_here
```

> **Note:** To get the HuggingFace token:
> 1. Create account at https://huggingface.co
> 2. Go to https://huggingface.co/settings/tokens
> 3. Create a new token
> 4. Accept the license at https://huggingface.co/pyannote/speaker-diarization-3.1

### 3. Run the application

```bash
./start.sh
```

This will:
- Create Python virtual environment and install dependencies
- Install npm packages for the frontend
- Start backend on http://localhost:8000
- Start frontend on http://localhost:3000

### 4. Open the app

Navigate to http://localhost:3000 in your browser.

## Manual Setup

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

## Project Structure

```
transcribeflow/
├── backend/
│   ├── api/                 # API endpoints
│   │   ├── transcribe.py    # Transcription endpoints
│   │   └── settings.py      # Settings endpoint
│   ├── engines/             # ASR engines
│   │   ├── base.py          # Base engine interface
│   │   └── mlx_whisper.py   # MLX Whisper implementation
│   ├── models/              # Database models
│   │   ├── database.py      # SQLite configuration
│   │   └── transcription.py # Transcription model
│   ├── workers/             # Background workers
│   │   ├── diarization.py   # Pyannote diarization
│   │   ├── transcription_worker.py  # Main worker
│   │   └── queue_processor.py       # Queue processor
│   ├── tests/               # Backend tests
│   ├── config.py            # Configuration
│   ├── main.py              # FastAPI app
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages
│   │   │   ├── page.tsx     # Main page
│   │   │   ├── settings/    # Settings page
│   │   │   └── transcription/[id]/  # Detail page
│   │   ├── components/      # React components
│   │   │   ├── FileUpload.tsx
│   │   │   ├── TranscriptionQueue.tsx
│   │   │   └── SpeakerEditor.tsx
│   │   └── lib/
│   │       └── api.ts       # API client
│   └── package.json
├── .env.example             # Environment template
├── start.sh                 # Startup script
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/settings` | Get current settings |
| POST | `/api/transcribe/upload` | Upload audio file |
| GET | `/api/transcribe/queue` | List all transcriptions |
| GET | `/api/transcribe/{id}` | Get transcription status |
| GET | `/api/transcribe/{id}/transcript` | Get transcript data |
| PUT | `/api/transcribe/{id}/speakers` | Update speaker names |

Full API documentation available at http://localhost:8000/docs

## Configuration

All configuration is done via environment variables with `TRANSCRIBEFLOW_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `TRANSCRIBEFLOW_HF_TOKEN` | HuggingFace token for Pyannote | Required for diarization |
| `TRANSCRIBEFLOW_BASE_PATH` | Base path for files | `~/Transcriptions` |
| `TRANSCRIBEFLOW_DEFAULT_ENGINE` | Default ASR engine | `mlx-whisper` |
| `TRANSCRIBEFLOW_DEFAULT_MODEL` | Default Whisper model | `large-v2` |
| `TRANSCRIBEFLOW_MIN_SPEAKERS` | Minimum speakers for diarization | `2` |
| `TRANSCRIBEFLOW_MAX_SPEAKERS` | Maximum speakers for diarization | `6` |

## Supported Audio Formats

- MP3 (`.mp3`)
- M4A (`.m4a`)
- WAV (`.wav`)
- OGG (`.ogg`)
- FLAC (`.flac`)
- WebM (`.webm`)

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -v
```

Current test coverage: **26 tests passing**

## Output Files

Transcriptions are saved to `~/Transcriptions/transcribed/` with the following structure:

```
2024-01-08_meeting/
├── meeting.mp3           # Original audio
├── transcript.json       # Full transcript with metadata
└── transcript.txt        # Human-readable transcript
```

### transcript.json structure

```json
{
  "metadata": {
    "id": "uuid",
    "filename": "meeting.mp3",
    "duration_seconds": 3600,
    "created_at": "2024-01-08T10:00:00",
    "engine": "mlx-whisper",
    "model": "large-v2",
    "language": "en"
  },
  "speakers": {
    "SPEAKER_00": { "name": "Alice", "color": "#3B82F6" },
    "SPEAKER_01": { "name": "Bob", "color": "#10B981" }
  },
  "segments": [
    {
      "start": 0.0,
      "end": 5.5,
      "text": "Hello everyone",
      "speaker": "SPEAKER_00",
      "confidence": 0.95
    }
  ],
  "stats": {
    "total_words": 1500,
    "speakers_count": 2,
    "processing_time_seconds": 120
  }
}
```

## Troubleshooting

### Port already in use

If port 3000 or 8000 is in use, kill existing processes:

```bash
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

### MLX Whisper not found

Install MLX Whisper:

```bash
pip install mlx-whisper
```

### Diarization not working

1. Ensure HuggingFace token is set in `.env`
2. Accept the Pyannote license at https://huggingface.co/pyannote/speaker-diarization-3.1
3. Install PyTorch: `pip install torch torchaudio`

### Database reset

To reset the database:

```bash
rm ~/.transcribeflow/transcribeflow.db
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (`pytest -v`)
5. Submit a pull request
