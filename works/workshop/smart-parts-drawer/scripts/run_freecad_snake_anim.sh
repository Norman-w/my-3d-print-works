#!/usr/bin/env bash
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FCSTD="${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd"
ANIM="${SCRIPT_DIR}/freecad_snake_animate.py"
APP="/Applications/FreeCAD.app"

# ===== 分区：公开 API =====
if [[ ! -d "${APP}" ]]; then
  echo "未找到 ${APP}"
  echo "请安装：brew install --cask freecad"
  exit 1
fi
if [[ ! -f "${FCSTD}" ]]; then
  echo "缺少 ${FCSTD}，先生成模型："
  echo "  ./scripts/run_freecad_pipeline.sh --no-export --columns 4 --layers 3"
  exit 1
fi

# ===== 分区：业务逻辑 =====
export PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONUNBUFFERED=1
export QT_ACCESSIBILITY=0
echo "通过 macOS Launch Services 打开 FreeCAD。"
echo "方案1：选择带先定位停稳，单离合接合后才开启目标抽屉动力，释放后回 HOME。"
open -n -a "${APP}" --args -P "${SCRIPT_DIR}" "${FCSTD}" "${ANIM}"
sleep 2
osascript -e 'tell application "FreeCAD" to activate' >/dev/null 2>&1 || true
