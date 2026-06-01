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

# 2. Start Web dev server
echo "[2/3] Starting Web UI on :5173..."
cd "$ROOT/web"
npm run dev -- --host &
WEB_PID=$!
sleep 2

# 3. Open browser
echo "[3/3] Ready!"
echo ""
echo "  Server:  http://localhost:8000  (API + WebSocket)"
echo "  Web UI:  http://localhost:5173"
echo "  Models:  $ROOT/enclosure/output/"
echo ""
echo "Press Ctrl+C to stop all services."

open "http://localhost:5173"
open "$ROOT/enclosure/output"

wait
