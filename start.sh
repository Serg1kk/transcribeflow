#!/bin/bash
set -e

echo "Starting TranscribeFlow..."

# Start backend
cd backend
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "Backend running on http://localhost:8000"
echo "Frontend running on http://localhost:3000"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
