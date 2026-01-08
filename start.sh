#!/bin/bash
set -e

echo "========================================"
echo "         TranscribeFlow Startup         "
echo "========================================"

# Check Python version
python3 --version

# Setup backend
echo ""
echo "Setting up backend..."
cd backend

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

# Start backend in background
echo "Starting backend on http://localhost:8000..."
python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Setup frontend
cd ../frontend
echo ""
echo "Setting up frontend..."

if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Start frontend in background
echo "Starting frontend on http://localhost:3000..."
npm run dev &
FRONTEND_PID=$!

# Trap to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo "========================================"
echo "TranscribeFlow is running!"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================"

# Wait for both processes
wait
