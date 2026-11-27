#!/usr/bin/env bash
# ===== 分区：常量/配置 =====
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
gui_bin="${FREECAD_GUI_BIN:-/Applications/FreeCAD.app/Contents/MacOS/FreeCAD}"
script="$project_root/cad/animate_drive_freecad.py"

# ===== 分区：业务逻辑 =====
if [[ ! -x "$gui_bin" ]]; then
  echo "找不到 FreeCAD 图形界面: $gui_bin" >&2
  exit 1
fi

export PROJECT_ROOT="$project_root"
rm -f "$project_root/output/simulation/freecad-animation.log"
mkdir -p "$project_root/output/simulation"

# ===== 分区：公开 API =====
echo "正在打开 FreeCAD 三维传动动画。"
echo "请看 CotsDrive 窗口：绿色小齿轮快转，黄色大齿轮按 5:1 反向慢转。"
echo "如果只看到 Python 文本，在 FreeCAD 里选 Macro → Execute macro。"
exec "$gui_bin" "$script"
