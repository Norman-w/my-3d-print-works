#!/usr/bin/env bash
# ===== 分区：常量/配置 =====
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
openscad_bin="${OPENSCAD_BIN:-$(command -v openscad || true)}"
openscad_bin="${openscad_bin:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"

# ===== 分区：业务逻辑 =====
if [[ ! -x "$openscad_bin" ]]; then
  echo "OpenSCAD executable not found: $openscad_bin" >&2
  echo "Set OPENSCAD_BIN to an installed OpenSCAD CLI and retry." >&2
  exit 1
fi

# Agent sandboxes on Apple Silicon can hide NEON/CRC32 from Qt.
export QT_NO_CPU_FEATURE="${QT_NO_CPU_FEATURE:-neon,crc32}"

# ===== 分区：公开 API =====
exec "$openscad_bin" "$@"
