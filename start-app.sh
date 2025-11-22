#!/bin/bash

echo "🚀 Starting Knowledge Base PWA..."

# Start backend in background
echo "Starting backend..."
./start-backend.sh &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend..."
./start-frontend.sh &
FRONTEND_PID=$!

echo ""
echo "✅ App starting! Open http://localhost:5173"
echo "Press Ctrl+C to stop both servers"

# Cleanup function
cleanup() {
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT

# Wait
wait