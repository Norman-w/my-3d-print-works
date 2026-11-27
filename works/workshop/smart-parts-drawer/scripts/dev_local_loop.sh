#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT=4173
HOST="127.0.0.1"
LAN_HOST=""
PIPE_ARGS=()
SKIP_GUI=false
SKIP_VIEW=false
ONLY_VIEW=false
LOG_FILE="/tmp/smartpartsdrawer-pipeline.log"

resolve_lan_host() {
  local ip=""
  ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "${ip}" ]]; then
    ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  if [[ -z "${ip}" ]]; then
    ip="$(ifconfig 2>/dev/null | awk '/inet / {print $2}' | grep -v '^127\\.' | head -n 1 || true)"
  fi
  if [[ -z "${ip}" ]]; then
    LAN_HOST=""
  else
    LAN_HOST="${ip}"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      if [[ $# -lt 2 ]]; then
        echo "错误：--port 需要一个端口号"
        exit 1
      fi
      PORT="$2"
      shift 2
      ;;
    --host)
      if [[ $# -lt 2 ]]; then
        echo "错误：--host 需要一个地址"
        exit 1
      fi
      HOST="$2"
      shift 2
      ;;
  --lan-host)
      if [[ $# -lt 2 ]]; then
        echo "错误：--lan-host 需要一个地址"
        exit 1
      fi
      LAN_HOST="$2"
      shift 2
      ;;
    --skip-gui)
      SKIP_GUI=true
      shift
      ;;
    --skip-view)
      SKIP_VIEW=true
      shift
      ;;
    --only-view)
      ONLY_VIEW=true
      shift
      ;;
    -h|--help)
      cat <<EOF
用法:
  ./scripts/dev_local_loop.sh [--port 4173] [--host 127.0.0.1] [--lan-host 192.168.6.187] [--skip-gui] [--skip-view] [--only-view] [freecad 脚本参数...]

示例:
  ./scripts/dev_local_loop.sh --columns 2 --layers 2 --selector-mode snake
  ./scripts/dev_local_loop.sh --port 8080 -- --no-export --columns 2 --layers 2 --selector-mode snake
  ./scripts/dev_local_loop.sh --port 4173 --host 0.0.0.0 --lan-host 192.168.6.187 --columns 4 --layers 3 --selector-mode snake

说明:
  本脚本会先执行 FreeCAD CLI 重建（如果 freecadcmd 可用）后自动打开 GUI。
  默认会启动 web 服务并打开 STL 预览；若使用 --no-export 将只打开 FCStd。
  --skip-gui: 不自动打开 FreeCAD GUI。
  --skip-view: 不启动网页预览服务（可用于只跑 pipeline/检查日志）。
  --only-view: 仅启动预览服务（不执行 pipeline 重建，需现有 manifest）。
  --host: 指定 http.server 绑定地址。建议局域网可用时设置为 0.0.0.0。
  --lan-host: 可选，用于本机自动打开一个局域网 URL（仅用于浏览器自动打开提示）。值为 auto 时自动检测本机内网 IP。
EOF
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      PIPE_ARGS+=("$1")
      shift
      ;;
  esac
done

# 追加 -- 后剩余参数
while [[ $# -gt 0 ]]; do
  PIPE_ARGS+=("$1")
  shift
done

cd "${PROJECT_ROOT}"

if [ ! -x "${SCRIPT_DIR}/run_freecad_pipeline.sh" ]; then
  echo "缺少脚本: ${SCRIPT_DIR}/run_freecad_pipeline.sh"
  exit 1
fi

timestamp() {
  date +"%Y%m%d_%H%M%S"
}

mkdir -p "${HOME}/.cache/smartpartsdrawer"
LOG_FILE="${HOME}/.cache/smartpartsdrawer/pipeline_$(timestamp).log"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && ps -p "${SERVER_PID}" >/dev/null 2>&1; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

print_pipeline_outputs() {
  local manifest_file="${PROJECT_ROOT}/web/assets/stl/manifest.json"
  echo "--- 输出检查 ---"
  if [[ -f "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" ]]; then
    echo "FCStd: ${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd"
  else
    echo "FCStd: 尚未生成"
  fi
  if [[ -d "${PROJECT_ROOT}/web/assets/stl" ]]; then
    echo "STL 目录: ${PROJECT_ROOT}/web/assets/stl"
    shopt -s nullglob
    local local_stl_files
    local_stl_files=("${PROJECT_ROOT}/web/assets/stl/"*.stl)
    if ((${#local_stl_files[@]} == 0)); then
      echo "  (未检测到 STL 文件)"
    else
      for f in "${local_stl_files[@]}"; do
        echo "  $(basename "${f}")"
      done
    fi
    shopt -u nullglob
  fi
  if [[ -f "${manifest_file}" ]]; then
    echo "Manifest: ${manifest_file}"
    python3 - "$manifest_file" <<'PY'
import json
import pathlib
import sys

mf = pathlib.Path(sys.argv[1])
try:
    data = json.loads(mf.read_text(encoding="utf-8"))
except Exception as e:
    print(f"manifest 解析失败: {e}")
else:
    models = data.get("models", [])
    print(f"manifest.models 数量: {len(models)}")
    keys = list(data.get("mechanismMap", {}).keys())
    print(f"mechanismMap keys: {', '.join(keys) if keys else '无'}")
    cfg = data.get("config", {})
    print(f"config: 列数={cfg.get('columns')}, 层数={cfg.get('layers')}, selector={cfg.get('selectorMode')}")
PY
  else
    echo "Manifest: 不存在"
  fi
  echo "--------------"
}

NO_EXPORT=false
for arg in "${PIPE_ARGS[@]+"${PIPE_ARGS[@]}"}"; do
  if [[ "${arg}" == "--no-export" ]]; then
    NO_EXPORT=true
    break
  fi
done
DRY_RUN=false
for arg in "${PIPE_ARGS[@]+"${PIPE_ARGS[@]}"}"; do
  if [[ "${arg}" == "--dry-run" ]]; then
    DRY_RUN=true
    break
  fi
done

if [[ "${ONLY_VIEW}" == "true" ]]; then
  if [[ "${LAN_HOST}" == "auto" ]]; then
    resolve_lan_host
  fi
  if [[ "${SKIP_VIEW}" == "true" ]]; then
    echo "参数冲突：--only-view 与 --skip-view 不可同时使用。"
    exit 1
  fi
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "参数冲突：--only-view 与 --dry-run 不可同时使用。"
    exit 1
  fi
  if [[ "${NO_EXPORT}" == "true" ]]; then
    echo "参数冲突：--only-view 与 --no-export 不可同时使用。"
    exit 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "缺少 python3，无法启动预览服务。"
    exit 1
  fi
  if [ ! -f "${PROJECT_ROOT}/web/assets/stl/manifest.json" ]; then
    echo "only-view 模式需要先导出 manifest：web/assets/stl/manifest.json 不存在。"
    exit 1
  fi
  if [ ! -f "${PROJECT_ROOT}/web/assets/stl/all.stl" ]; then
    echo "only-view 模式需要先导出 all.stl：web/assets/stl/all.stl 不存在。"
    exit 1
  fi
  print_pipeline_outputs
  if [ -f "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" ] && [[ "${SKIP_GUI}" != "true" ]] && command -v open >/dev/null 2>&1; then
    open -a FreeCAD "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" >/dev/null 2>&1 || true
  fi

  python3 -m http.server "${PORT}" --directory web --bind "${HOST}" >/tmp/smartpartsdrawer-viewer.log 2>&1 &
  SERVER_PID=$!
  local_open_url="http://127.0.0.1:${PORT}/freecad-viewer.html"
  if [[ -n "${LAN_HOST}" ]]; then
    local_open_url="http://${LAN_HOST}:${PORT}/freecad-viewer.html"
  fi
  echo "本地预览服务已启动：${local_open_url}"
  if [[ "${HOST}" != "127.0.0.1" && -n "${LAN_HOST}" ]]; then
    echo "局域网访问地址：http://${LAN_HOST}:${PORT}/freecad-viewer.html"
  fi
  echo "日志文件: /tmp/smartpartsdrawer-viewer.log"
  sleep 0.6
  if command -v open >/dev/null 2>&1; then
    open "${local_open_url}" >/dev/null 2>&1 || true
  fi
  echo "脚本在前台等待。按 Ctrl-C 退出可停止本地服务。"
  wait "${SERVER_PID}"
fi

echo "运行 FreeCAD 建模命令..."
echo "日志文件: ${LOG_FILE}"
if "${SCRIPT_DIR}/run_freecad_pipeline.sh" "${PIPE_ARGS[@]}" 2>&1 | tee "${LOG_FILE}"; then
  echo "FreeCAD 导出完成。"
  print_pipeline_outputs
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "dry-run 模式已完成，未执行 STL/FCStd 导出。"
    echo "日志文件: ${LOG_FILE}"
    exit 0
  fi
else
  echo "FreeCAD 重建失败，终止后续流程。"
  echo "请查看日志: ${LOG_FILE}"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "缺少 python3，无法启动预览服务。"
  exit 1
fi

if [[ "${NO_EXPORT}" == "true" ]]; then
  echo "已使用 --no-export，不启动 STL 预览。"
  if [[ "${SKIP_GUI}" == "true" ]]; then
    echo "你启用了 --skip-gui，已跳过 GUI 打开步骤。"
    echo "日志文件: ${LOG_FILE}"
    exit 0
  fi
  if [ -f "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" ]; then
    if command -v open >/dev/null 2>&1; then
      open -a FreeCAD "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" >/dev/null 2>&1 || true
    fi
  else
    echo "未找到 FCStd 文件：${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd"
  fi
  exit 0
fi

if [[ "${SKIP_VIEW}" == "true" ]]; then
  echo "你启用了 --skip-view，已完成 FCStd + STL 产物导出。"
  echo "日志文件: ${LOG_FILE}"
  exit 0
fi

if [ ! -d "${PROJECT_ROOT}/web/assets/stl" ] || [ ! -f "${PROJECT_ROOT}/web/assets/stl/manifest.json" ] || [ ! -f "${PROJECT_ROOT}/web/assets/stl/all.stl" ]; then
  echo "未检测到完整 STL 导出产物（all.stl / manifest.json）。请先确认 pipeline 是否正确导出。"
  exit 1
fi

EXPECTED_STL_COUNT=5
actual_stl_count=$(ls "${PROJECT_ROOT}"/web/assets/stl/*.stl 2>/dev/null | wc -l | tr -d ' ')
if [[ "${actual_stl_count}" -lt "${EXPECTED_STL_COUNT}" ]]; then
  echo "检测到 STL 数量不足：${actual_stl_count}，建议检查 pipeline 里模型分组。"
fi

python3 -m http.server "${PORT}" --directory web --bind "${HOST}" >/tmp/smartpartsdrawer-viewer.log 2>&1 &
SERVER_PID=$!
LOCAL_VIEW_URL="http://127.0.0.1:${PORT}/freecad-viewer.html"
LAN_VIEW_URL="http://${HOST}:${PORT}/freecad-viewer.html"
if [[ "${LAN_HOST}" == "auto" ]]; then
  resolve_lan_host
fi
if [[ -n "${LAN_HOST}" ]]; then
  LAN_VIEW_URL="http://${LAN_HOST}:${PORT}/freecad-viewer.html"
fi
echo "本地预览服务已启动：${LOCAL_VIEW_URL}"
if [[ "${HOST}" != "127.0.0.1" ]]; then
  echo "局域网访问：${LAN_VIEW_URL}"
fi
sleep 0.6

if [ -f "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" ]; then
  if [[ "${SKIP_GUI}" != "true" ]] && command -v open >/dev/null 2>&1; then
    open -a FreeCAD "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" >/dev/null 2>&1 || true
  fi
fi

if command -v open >/dev/null 2>&1; then
  open "${LOCAL_VIEW_URL}" >/dev/null 2>&1 || true
fi

echo "脚本在前台等待。按 Ctrl-C 退出可停止本地服务。"
wait "${SERVER_PID}"
