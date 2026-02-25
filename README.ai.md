# TranscribeFlow — AI Agent Setup Guide

> This file is for AI agents (OpenClaw, Claude Code, etc.) deploying TranscribeFlow on a Mac mini or similar macOS machine.
> Follow these steps exactly. When done, notify your human.

---

## What This Is

TranscribeFlow is a local AI-powered transcription service with speaker diarization and AI insights. It runs a Python backend (FastAPI) + Next.js frontend. Optimized for Apple Silicon.

**After setup, your human drops audio files into a folder, you upload them via API, and results appear in the web UI.**

---

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- Node.js 18+ (recommend 20+)
- Git
- HuggingFace account with accepted model licenses (see Step 3)

---

## Step 1: Clone the repo

```bash
cd ~
mkdir -p services/transcribeflow
git clone https://github.com/Serg1kk/transcribeflow.git services/transcribeflow/app
cd services/transcribeflow/app
```

## Step 2: Configure environment

```bash
cp .env.example backend/.env
```

Edit `backend/.env` and set these values:

| Variable | Required | Description |
|----------|----------|-------------|
| `TRANSCRIBEFLOW_HF_TOKEN` | ✅ | HuggingFace token (see Step 3) |
| `TRANSCRIBEFLOW_DEFAULT_ENGINE` | Set to `mlx-whisper` | Local Apple Silicon engine |
| `TRANSCRIBEFLOW_DEFAULT_MODEL` | Set to `large-v3` | Best quality model |
| `TRANSCRIBEFLOW_BACKEND_HOST` | Set to `0.0.0.0` | Allow LAN access |
| `TRANSCRIBEFLOW_GEMINI_API_KEY` | Optional | For AI post-processing |
| `TRANSCRIBEFLOW_OPENROUTER_API_KEY` | Optional | Alternative LLM provider |

**Important:** Set `TRANSCRIBEFLOW_BACKEND_HOST=0.0.0.0` so the service is accessible over the network, not just localhost.

## Step 3: HuggingFace setup (requires human action)

⚠️ **Ask your human to do this manually — it requires clicking "Agree" on web pages:**

1. Create account at https://huggingface.co
2. Create token at https://huggingface.co/settings/tokens
3. Accept licenses at:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
4. Give you the token to put in `backend/.env`

## Step 4: Install dependencies

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## Step 5: Test that it starts

```bash
cd ~/services/transcribeflow/app

# Start backend
cd backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &

# Wait for backend
sleep 3
curl -s http://localhost:8000/api/health | python3 -m json.tool

# Start frontend
cd ../frontend
npm run dev -- -H 0.0.0.0 -p 3001 &

# Test frontend
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001
```

Both should respond (backend: JSON health response, frontend: HTTP 200). Then kill both processes — we'll set up a proper daemon next.

```bash
pkill -f "uvicorn main:app.*8000"
pkill -f "next dev.*3001"
```

## Step 6: Set up as a persistent service (launchd)

Create the daemon startup script (it's already in the repo as `start-daemon.sh`):

```bash
chmod +x ~/services/transcribeflow/app/start-daemon.sh
```

Create launchd plist:

```bash
cat > ~/Library/LaunchAgents/com.transcribeflow.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.transcribeflow</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>START_DAEMON_PATH</string>
    </array>
    <key>WorkingDirectory</key>
    <string>APP_DIR_PATH</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>APP_DIR_PATH/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>APP_DIR_PATH/logs/launchd-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF
```

**Replace `START_DAEMON_PATH` and `APP_DIR_PATH`** with actual paths on the target machine (e.g., `/Users/USERNAME/services/transcribeflow/app/start-daemon.sh` and `/Users/USERNAME/services/transcribeflow/app`).

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.transcribeflow.plist
```

Verify it's running:

```bash
launchctl list | grep transcribeflow
curl -s http://localhost:8000/api/health
```

## Step 7: Create the transcription inbox folder

Create a folder where your human will drop audio files:

```bash
mkdir -p ~/clawd/inbox/transcribe/in-progress
```

Add this to your `TOOLS.md` or equivalent:

```markdown
## 🎙 TranscribeFlow

**Ports:** Frontend: 3001, Backend: 8000
**LAN URL:** http://<YOUR_LAN_IP>:3001

### Transcription Workflow

1. Human drops audio files into `~/clawd/inbox/transcribe/`
2. Upload via API:
   ```bash
   curl -X POST "http://localhost:8000/api/transcribe/upload" \
     -F "file=@/path/to/file.m4a" \
     -F "engine=mlx-whisper" \
     -F "model=large-v3"
   ```
3. Set initial prompt (context about the call):
   ```bash
   curl -X PUT "http://localhost:8000/api/transcribe/{ID}" \
     -H "Content-Type: application/json" \
     -d '{"initial_prompt": "Meeting about X with Y and Z"}'
   ```
4. Start transcription:
   ```bash
   curl -X POST "http://localhost:8000/api/transcribe/start" \
     -H "Content-Type: application/json" \
     -d '{"ids": ["{ID}"]}'
   ```
5. Move file to in-progress:
   ```bash
   mv ~/clawd/inbox/transcribe/FILE ~/clawd/inbox/transcribe/in-progress/
   ```
6. Check status:
   ```bash
   curl -s http://localhost:8000/api/transcribe/queue
   ```

**Always use:** engine=mlx-whisper, model=large-v3
```

## Step 8: Verify everything works end-to-end

1. Check service is running: `curl -s http://localhost:8000/api/health`
2. Check frontend is accessible: open `http://localhost:3001` in browser
3. Check LAN access: `http://<LAN_IP>:3001` from another device
4. Test transcription with a small audio file

## Done!

When everything is working, notify your human with:
- ✅ TranscribeFlow is deployed and running
- 🌐 Web UI: `http://<LAN_IP>:3001`
- 📂 Drop audio files in: `~/clawd/inbox/transcribe/`
- 🔄 Service auto-starts on reboot (launchd)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend won't start | Check `logs/backend.log`, verify Python venv |
| Frontend won't start | Check `logs/frontend.log`, run `npm install` |
| Diarization fails | Verify HF token and model license acceptance |
| Port conflict | Change ports in `.env` and `start-daemon.sh` |
| Service not restarting | `launchctl unload` then `launchctl load` the plist |
| Model download slow | First run downloads ~3GB for large-v3, be patient |

## Service Management

```bash
# Check status
launchctl list | grep transcribeflow

# Restart
launchctl kickstart -k gui/$(id -u)/com.transcribeflow

# Stop
launchctl unload ~/Library/LaunchAgents/com.transcribeflow.plist

# Start
launchctl load ~/Library/LaunchAgents/com.transcribeflow.plist

# Logs
tail -f ~/services/transcribeflow/app/logs/backend.log
tail -f ~/services/transcribeflow/app/logs/frontend.log
```
