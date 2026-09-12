#!/usr/bin/env bash
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIPELINE="${SCRIPT_DIR}/freecad_drawer_pipeline.py"
PASS_ARGS="${*:-}"

# ===== 分区：公开 API =====
cd "${PROJECT_ROOT}"
export PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

for arg in "$@"; do
  if [[ "${arg}" == "--dry-run" ]]; then
    exec python3 "${PIPELINE}" "$@"
  fi
done

run_with() {
  local cmd="$1"
  # FreeCAD 1.1：把脚本当文件打开，参数走 --pass
  exec "${cmd}" -P "${SCRIPT_DIR}" "${PIPELINE}" --pass "${PASS_ARGS}"
}

# ===== 分区：业务逻辑 =====
if command -v freecadcmd >/dev/null 2>&1; then
  run_with "$(command -v freecadcmd)"
fi
if [ -x "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd" ]; then
  run_with "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
fi

echo "未检测到 freecadcmd。请先安装/激活 FreeCAD，然后重试。"
echo "可选：如果安装在 macOS 标准路径，尝试："
echo "  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -P scripts scripts/freecad_drawer_pipeline.py --pass \"--help\""
exit 1
