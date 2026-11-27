#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

SP_API_PORT="${SP_API_PORT:-8000}"
SP_WEB_PORT="${SP_WEB_PORT:-5173}"
SP_STL_PORT="${SP_STL_PORT:-8775}"
SP_DEV_KILL_PORTS="${SP_DEV_KILL_PORTS:-0}"
SP_OPEN_TAB="${SP_OPEN_TAB:-process}"
SP_DEVICE_HOST="${SP_DEVICE_HOST:-}"
export SP_API_PORT SP_WEB_PORT SP_STL_PORT

port_listen_pids() {
  command -v lsof >/dev/null 2>&1 || return 0
  lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true
}

require_free_port() {
  local port="$1" label="$2"
  local pids
  pids=$(port_listen_pids "$port")
  if [[ -n "$pids" ]]; then
    echo "ERROR: 端口 :$port（$label）已被占用 PID: $pids"
    echo "  乒云等其它任务请继续用默认端口；SmartPaddle 可用: ./dev-sim.sh（8010/5183/8775）"
    echo "  或自定义: SP_API_PORT=8020 SP_WEB_PORT=5190 SP_DEV_KILL_PORTS=0 ./dev.sh"
    exit 1
  fi
}

maybe_release_web_port() {
  if [[ "$SP_DEV_KILL_PORTS" != "1" ]]; then
    return 0
  fi
  local pids
  pids=$(port_listen_pids "$SP_WEB_PORT")
  if [[ -n "$pids" ]]; then
    echo "  SP_DEV_KILL_PORTS=1：释放占用 :$SP_WEB_PORT 的进程…"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $SERVER_PID 2>/dev/null || true
    kill $WEB_PID 2>/dev/null || true
    kill $PREVIEW_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

echo "============================================"
echo "  SmartPaddle Dev Server"
echo "============================================"
echo ""

# 1. Keep ignored/generated STL assets in sync with the checked-out source.
echo "[1/5] Checking M7 STL assets..."
M7_FRONT="$ROOT/enclosure/stl/paddle_m7_monolithic_front.stl"
STALE_STL=0
for SOURCE in \
  "$ROOT/enclosure/paddle_shell.scad" \
  "$ROOT/enclosure/parameters.scad" \
  "$ROOT/scripts/bezier_to_openscad.py" \
  "$ROOT/pcb-tail/layouts/default/default.kicad_pcb"; do
  if [[ ! -f "$M7_FRONT" || "$SOURCE" -nt "$M7_FRONT" ]]; then
    STALE_STL=1
  fi
done
if [[ "${SKIP_STL_EXPORT:-0}" != "1" && "$STALE_STL" == "1" ]]; then
  echo "  M7 源文件有更新，执行快速 STL 导出（可用 SKIP_STL_EXPORT=1 跳过）..."
  QUALITY_MODE=quick "$ROOT/scripts/export-stl.sh"
else
  python3 "$ROOT/scripts/write_preview_manifest.py"
fi

LIGHTBOARD_MANIFEST="$ROOT/enclosure/stl/lightboard/preview/lightboard_manifest.json"
LIGHTBOARD_STALE=0
for SOURCE in \
  "$ROOT/enclosure/paddle_shell.scad" \
  "$ROOT/enclosure/parameters.scad" \
  "$ROOT/scripts/bezier_to_openscad.py" \
  "$ROOT/scripts/export-lightboard-stl.sh" \
  "$ROOT/scripts/build_print_plates.py" \
  "$ROOT/scripts/build_3mf_package.py" \
  "$ROOT/scripts/write_lightboard_manifest.py"; do
  if [[ ! -f "$LIGHTBOARD_MANIFEST" || "$SOURCE" -nt "$LIGHTBOARD_MANIFEST" ]]; then
    LIGHTBOARD_STALE=1
  fi
done
if [[ "${SKIP_STL_EXPORT:-0}" != "1" && "$LIGHTBOARD_STALE" == "1" ]]; then
  echo "  M7-LB1 光板版源文件有更新，执行快速 STL → 3MF 导出..."
  QUALITY_MODE=quick "$ROOT/scripts/export-lightboard-stl.sh"
fi

# 2. Start Go server
require_free_port "$SP_API_PORT" "Go API"
echo "[2/5] Starting Go server on :$SP_API_PORT..."
cd "$ROOT/server"
PORT="$SP_API_PORT" go run . &
SERVER_PID=$!

# Wait until API is actually listening (first run may compile deps)
echo "  Waiting for http://127.0.0.1:$SP_API_PORT ..."
for i in $(seq 1 90); do
  if curl -sf -m 1 "http://127.0.0.1:$SP_API_PORT/api/bezier-profiles/project" >/dev/null 2>&1; then
    echo "  Go server ready."
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "ERROR: Go server exited before becoming ready."
    exit 1
  fi
  sleep 1
  if [[ "$i" -eq 90 ]]; then
    echo "ERROR: Go server did not become ready within 90s."
    kill "$SERVER_PID" 2>/dev/null || true
    exit 1
  fi
done

# 3. Serve exported STL and manifest for the unified process preview.
require_free_port "$SP_STL_PORT" "STL preview"
echo "[3/5] Starting STL asset server on :$SP_STL_PORT..."
cd "$ROOT/enclosure/stl"
python3 -m http.server "$SP_STL_PORT" --bind 127.0.0.1 >/tmp/smartpaddle-stl-preview.log 2>&1 &
PREVIEW_PID=$!

# 4. Start Web dev server (fixed port — localStorage is per-origin; curves live on server)
maybe_release_web_port
require_free_port "$SP_WEB_PORT" "Web UI"
echo "[4/5] Starting Web UI on :$SP_WEB_PORT (strict)..."
cd "$ROOT/web"
npm run dev -- --host --port "$SP_WEB_PORT" --strictPort &
WEB_PID=$!
sleep 2

# 5. Open browser
WEB_URL="http://localhost:$SP_WEB_PORT/?tab=$SP_OPEN_TAB"
if [[ -n "$SP_DEVICE_HOST" ]]; then
  WEB_URL="${WEB_URL}&device=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$SP_DEVICE_HOST'''))")"
fi
echo "[5/5] Ready!"
echo ""
echo "  Server:  http://localhost:$SP_API_PORT  (API + WebSocket)"
echo "  Web UI:  http://localhost:$SP_WEB_PORT"
echo "  Live:    http://localhost:$SP_WEB_PORT/?tab=live"
echo "  M7:      http://localhost:$SP_WEB_PORT/?tab=process"
echo "  Models:  $ROOT/enclosure/stl/"
echo ""
echo "Press Ctrl+C to stop all services."

if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
  open "$WEB_URL"
  open "$ROOT/enclosure/stl" 2>/dev/null || true
fi

wait
