#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $SERVER_PID 2>/dev/null || true
    kill $WEB_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

echo "============================================"
echo "  SmartPaddle Dev Server"
echo "============================================"
echo ""

# 1. Start Go server
echo "[1/3] Starting Go server on :8000..."
cd "$ROOT/server"
go run . &
SERVER_PID=$!
sleep 1

# 2. Start Web dev server (fixed port — localStorage is per-origin; curves live on server)
echo "[2/3] Starting Web UI on :5173 (strict)..."
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti:5173 2>/dev/null || true)
  if [[ -n "$PIDS" ]]; then
    echo "  释放占用 5173 的进程…"
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
fi
cd "$ROOT/web"
npm run dev -- --host --port 5173 --strictPort &
WEB_PID=$!
sleep 2

# 3. Open browser
echo "[3/3] Ready!"
echo ""
echo "  Server:  http://localhost:8000  (API + WebSocket)"
echo "  Web UI:  http://localhost:5173"
echo "  Models:  $ROOT/enclosure/stl/"
echo ""
echo "Press Ctrl+C to stop all services."

open "http://localhost:5173"
open "$ROOT/enclosure/stl" 2>/dev/null || true

wait
