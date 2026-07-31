#!/usr/bin/env bash
# 托管 enclosure/stl 预览（守护进程；已在跑则复用，不重复弹窗）
#
#   ./scripts/preview-stl.sh
#   ./scripts/preview-stl.sh status|stop|restart
set -euo pipefail

# ===== 分区：常量/配置 =====
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/enclosure/stl"
PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}/preview/"
PID_FILE="${PREVIEW_PID_FILE:-$DIR/.preview-http.pid}"
LOG_FILE="${PREVIEW_LOG_FILE:-$DIR/.preview-http.log}"
CMD="${1:-start}"

# ===== 分区：私有成员 =====
is_listening() {
  command -v lsof >/dev/null 2>&1 && lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1
}

pid_alive() {
  local pid="$1"
  [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null
}

current_pid() {
  [[ -f "$PID_FILE" ]] && tr -d '[:space:]' <"$PID_FILE"
}

health_ok() {
  curl -fsS --max-time 2 "${URL}" >/dev/null 2>&1
}

stop_server() {
  local pid
  pid="$(current_pid || true)"
  if pid_alive "${pid:-}"; then
    kill "$pid" 2>/dev/null || true
    sleep 0.3
    kill -9 "$pid" 2>/dev/null || true
  fi
  if is_listening; then
    lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
    sleep 0.3
  fi
  rm -f "$PID_FILE"
}

ensure_assets() {
  if [[ ! -f "$DIR/preview/index.html" ]]; then
    echo "错误: 缺少 $DIR/preview/index.html" >&2
    exit 1
  fi
  if [[ ! -f "$DIR/preview/vendor/three/three.module.js" ]]; then
    echo "错误: 缺少 preview/vendor/three" >&2
    exit 1
  fi
  if [[ ! -f "$DIR/paddle_handle_tail.stl" ]]; then
    echo "→ 缺少 paddle_handle_tail.stl，先导出…"
    "$ROOT/scripts/export-stl.sh"
  fi
}

start_daemon() {
  local fresh=0
  ensure_assets
  if health_ok; then
    echo "✓ 已在运行 pid=$(current_pid || echo '?')  $URL"
    return 1  # 1 = 未新建（调用方勿再 open）
  fi
  if is_listening || pid_alive "$(current_pid || true)"; then
    stop_server
  fi
  : >"$LOG_FILE"
  (
    cd "$DIR"
    nohup python3 -m http.server "$PORT" --bind 127.0.0.1 >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
  )
  local i
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if health_ok; then
      echo "✓ 已启动 pid=$(current_pid)  $URL"
      echo "  停止: ./scripts/preview-stl.sh stop"
      return 0
    fi
    sleep 0.25
  done
  echo "错误: 端口 $PORT 未就绪，见 $LOG_FILE" >&2
  tail -20 "$LOG_FILE" >&2 || true
  exit 1
}

# ===== 分区：公开 API =====
case "$CMD" in
  start|"")
    if start_daemon; then
      command -v open >/dev/null 2>&1 && open "$URL"
    fi
    ;;
  status)
    if health_ok; then
      echo "running pid=$(current_pid || echo '?')  $URL"
      exit 0
    fi
    echo "stopped"
    exit 1
    ;;
  stop)
    stop_server
    echo "✓ 已停止"
    ;;
  restart)
    stop_server
    if start_daemon; then
      command -v open >/dev/null 2>&1 && open "$URL"
    fi
    ;;
  *)
    echo "用法: $0 {start|status|stop|restart}" >&2
    exit 2
    ;;
esac
