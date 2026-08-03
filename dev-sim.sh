#!/bin/bash
# SmartPaddle 本地开发（备用端口，避免与乒云等占用 8000/5173/8765 的任务冲突）
#
#   ./dev-sim.sh
#
# 默认：Go :8010 · Web :5183 · STL :8775
# 可覆盖：SP_API_PORT=8020 SP_WEB_PORT=5190 ./dev-sim.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
export SP_API_PORT="${SP_API_PORT:-8010}"
export SP_WEB_PORT="${SP_WEB_PORT:-5183}"
export SP_STL_PORT="${SP_STL_PORT:-8775}"
export SP_DEV_KILL_PORTS="${SP_DEV_KILL_PORTS:-0}"
export SP_OPEN_TAB="${SP_OPEN_TAB:-live}"
export SP_DEVICE_HOST="${SP_DEVICE_HOST:-192.168.7.90}"

exec "$ROOT/dev.sh"
