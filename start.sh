#!/bin/bash

echo -e "\033[32mStarting Investment System...\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "\033[33mStarting backend service...\033[0m"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
sleep 2

echo -e "\033[33mStarting frontend service...\033[0m"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\033[32mStarted!\033[0m"
echo -e "\033[36mFrontend: http://localhost:3000\033[0m"
echo -e "\033[36mBackend: http://localhost:8000\033[0m"
echo ""
echo -e "Backend PID: $BACKEND_PID"
echo -e "Frontend PID: $FRONTEND_PID"
echo ""
echo -e "Press Ctrl+C to stop all services..."

trap "echo -e '\033[33mStopping services...\033[0m'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
