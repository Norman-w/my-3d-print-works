#!/usr/bin/env bash
# 用本地 HTTP 托管 M5 预览（避免 file:// 加载不了相对路径 STL）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/enclosure/m5"
PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}/preview.html"

if [[ ! -f "$DIR/build/m5_handle_tail.stl" ]]; then
  echo "→ 尚无预览网格，先导出…"
  "$ROOT/scripts/export-m5-preview.sh"
fi

# 释放旧进程
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "${PIDS}" ]]; then
    echo "→ 释放端口 $PORT"
    echo "$PIDS" | xargs kill 2>/dev/null || true
    sleep 0.4
  fi
fi

cd "$DIR"
echo "============================================"
echo "  M5 preview  http://127.0.0.1:${PORT}/preview.html"
echo "  根目录      $DIR"
echo "  Ctrl+C 停止"
echo "============================================"

# 先开浏览器，再前台托管（相对路径 build/*.stl 可加载）
( sleep 0.6 && open "$URL" ) &
exec python3 -m http.server "$PORT" --bind 127.0.0.1
