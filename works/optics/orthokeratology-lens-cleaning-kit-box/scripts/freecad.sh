#!/usr/bin/env bash
# ===== 分区：常量/配置 =====
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
freecad_bin="${FREECAD_BIN:-}"

# ===== 分区：业务逻辑 =====
if [[ -z "$freecad_bin" ]]; then
  for candidate in \
    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
    /Applications/FreeCAD.app/Contents/MacOS/FreeCAD \
    "$(command -v freecadcmd || true)" \
    "$(command -v FreeCADCmd || true)"
  do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      freecad_bin="$candidate"
      break
    fi
  done
fi

if [[ -z "${freecad_bin}" || ! -x "$freecad_bin" ]]; then
  echo "FreeCAD executable not found. Install FreeCAD 1.1+ or set FREECAD_BIN." >&2
  exit 1
fi

export PROJECT_ROOT="$project_root"

# ===== 分区：公开 API =====
if [[ $# -ge 1 && "$1" == *.py ]]; then
  script_path="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  shift
  exec "$freecad_bin" -c <<EOF
__file__ = r'''${script_path}'''
exec(open(__file__, encoding='utf-8').read())
EOF
fi

exec "$freecad_bin" "$@"
