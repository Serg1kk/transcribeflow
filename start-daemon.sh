#!/bin/bash
# TranscribeFlow Daemon Starter (for launchd)
# Starts backend + frontend with separate log files

set -e

BASE_DIR="$HOME/local-projects/transcribeflow"
LOG_DIR="$BASE_DIR/logs"

mkdir -p "$LOG_DIR"

# Kill any existing processes from previous runs (cleanup on start)
if [ -f "$LOG_DIR/backend.pid" ]; then
    OLD_PID=$(cat "$LOG_DIR/backend.pid")
    kill -9 $OLD_PID 2>/dev/null || true
    rm -f "$LOG_DIR/backend.pid"
fi
if [ -f "$LOG_DIR/frontend.pid" ]; then
    OLD_PID=$(cat "$LOG_DIR/frontend.pid")
    kill -9 $OLD_PID 2>/dev/null || true
    rm -f "$LOG_DIR/frontend.pid"
fi
# Also kill any orphan processes
pkill -9 -f "uvicorn main:app.*8000" 2>/dev/null || true
pkill -9 -f "next dev.*3001" 2>/dev/null || true

# Wait for ports to be released
sleep 3

cd "$BASE_DIR/backend"

# Setup venv if needed
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install deps if needed
pip install -q -r requirements.txt

# Start backend
echo "Starting backend..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 >> "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"

# Setup frontend
cd "$BASE_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm install
fi

# Start frontend (listening on all interfaces for LAN access)
echo "Starting frontend..."
npm run dev -- -H 0.0.0.0 -p 3001 >> "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"

echo "TranscribeFlow started!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Trap for cleanup
cleanup() {
    echo "Stopping TranscribeFlow..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    rm -f "$LOG_DIR/backend.pid" "$LOG_DIR/frontend.pid"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for both
wait
