#!/usr/bin/env bash
set -euo pipefail

set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== FreeCAD 本地仿真就绪检查 ==="

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误: 未检测到 python3"
  exit 1
fi
echo "python3: $(python3 --version)"

FREECAD_CMD=""
if command -v freecadcmd >/dev/null 2>&1; then
  FREECAD_CMD="freecadcmd"
elif [ -x "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd" ]; then
  FREECAD_CMD="/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
else
  echo "错误: 未检测到 freecadcmd"
  echo "请安装 FreeCAD（macOS 推荐：Homebrew Cask 或官方 dmg）并确认 /Applications/FreeCAD.app 或 PATH。"
  echo "尝试：brew install --cask freecad"
  exit 1
fi

echo "freecadcmd: ${FREECAD_CMD}"
"${FREECAD_CMD}" --version 2>&1 | sed -n '1,3p'

echo "本地脚本: ${SCRIPT_DIR}/run_freecad_pipeline.sh"
if [ ! -x "${SCRIPT_DIR}/run_freecad_pipeline.sh" ]; then
  echo "警告: run_freecad_pipeline.sh 不可执行"
fi

if [ ! -d "${PROJECT_ROOT}/web/assets/stl" ]; then
  echo "首次运行：web/assets/stl 尚不存在（正常，可通过首次建模生成）"
fi

if [ -f "${PROJECT_ROOT}/build/SmartPartsDrawer.FCStd" ]; then
  echo "历史产物: build/SmartPartsDrawer.FCStd 已存在"
fi

if [ -f "${PROJECT_ROOT}/web/assets/stl/manifest.json" ]; then
  echo "历史产物: web/assets/stl/manifest.json 已存在"
fi

echo "✅ 检查通过：可启动 FreeCAD CLI 建模流水线。"
