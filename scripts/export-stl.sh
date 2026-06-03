#!/usr/bin/env bash
# Export paddle shell STLs: four parts + optional assembled front/back halves.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENC="$ROOT/enclosure"
OUT="$ENC/stl"
SCAD="$ENC/paddle_shell.scad"
QUALITY_MODE="${QUALITY_MODE:-normal}"
SCAD_DEFS=()

is_windows() {
  case "${OSTYPE:-}" in
    msys*|cygwin*|win32*) return 0 ;;
    *) return 1 ;;
  esac
}

setup_proxy_if_needed() {
  local proxy_url="${HTTP_PROXY:-${http_proxy:-http://localhost:10080}}"
  export HTTP_PROXY="$proxy_url"
  export HTTPS_PROXY="${HTTPS_PROXY:-$proxy_url}"
  export http_proxy="$HTTP_PROXY"
  export https_proxy="$HTTPS_PROXY"
  echo "→ 使用代理: $HTTP_PROXY"
}

ensure_openscad() {
  local default_paths=(
    "/c/Program Files/OpenSCAD/openscad.exe"
    "/c/Program Files (x86)/OpenSCAD/openscad.exe"
  )
  local p

  # Prefer snapshot (Manifold backend, ~400x faster) on macOS.
  if [[ -x /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD ]]; then
    OPENSCAD_BIN="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    OPENSCAD_FLAGS="--backend=Manifold"
    return 0
  elif [[ -x /opt/homebrew/bin/openscad ]]; then
    OPENSCAD_BIN="/opt/homebrew/bin/openscad"
    OPENSCAD_FLAGS=""
    return 0
  fi

  if command -v openscad >/dev/null 2>&1; then
    OPENSCAD_BIN="openscad"
    OPENSCAD_FLAGS=""
    return 0
  fi

  for p in "${default_paths[@]}"; do
    if [[ -x "$p" ]]; then
      export PATH="$(dirname "$p"):$PATH"
      OPENSCAD_BIN="openscad"
      OPENSCAD_FLAGS=""
      return 0
    fi
  done

  if ! is_windows; then
    echo "错误: 未找到 openscad。请安装 OpenSCAD 并加入 PATH。" >&2
    return 1
  fi

  echo "→ 未检测到 openscad，尝试在 Windows 下自动安装…"

  if command -v choco >/dev/null 2>&1; then
    echo "→ 使用 Chocolatey 安装 OpenSCAD（先直连）…"
    if ! choco install openscad -y; then
      echo "警告: Chocolatey 直连安装失败，改用代理重试…"
      setup_proxy_if_needed
      choco install openscad -y || echo "警告: Chocolatey 安装失败，尝试其他方式…"
    fi
  fi

  if ! command -v openscad >/dev/null 2>&1; then
    for p in "${default_paths[@]}"; do
      if [[ -x "$p" ]]; then
        export PATH="$(dirname "$p"):$PATH"
        OPENSCAD_BIN="openscad"
        OPENSCAD_FLAGS=""
        break
      fi
    done
  fi

  if ! command -v openscad >/dev/null 2>&1 && command -v winget >/dev/null 2>&1; then
    echo "→ 使用 winget 安装 OpenSCAD …"
    winget install --id OpenSCAD.OpenSCAD --exact --accept-source-agreements --accept-package-agreements || {
      echo "警告: winget 安装失败，改用代理重试…"
      setup_proxy_if_needed
      winget install --id OpenSCAD.OpenSCAD --exact --accept-source-agreements --accept-package-agreements || \
        echo "警告: winget 安装失败。"
    }
    for p in "${default_paths[@]}"; do
      if [[ -x "$p" ]]; then
        export PATH="$(dirname "$p"):$PATH"
        OPENSCAD_BIN="openscad"
        OPENSCAD_FLAGS=""
        break
      fi
    done
  fi

  if ! command -v openscad >/dev/null 2>&1; then
    echo "错误: 仍未找到 openscad。请手动安装 OpenSCAD 并加入 PATH。" >&2
    return 1
  fi
  OPENSCAD_BIN="openscad"
  OPENSCAD_FLAGS=""
}

ensure_openscad

mkdir -p "$OUT"
GEN="$ENC/generated/bezier_geometry.scad"
PYTHON_CMD=()

detect_python() {
  if command -v python3 >/dev/null 2>&1; then
    if python3 -V >/dev/null 2>&1; then
      PYTHON_CMD=(python3)
      return 0
    fi
  fi
  if command -v python >/dev/null 2>&1; then
    if python -V >/dev/null 2>&1; then
      PYTHON_CMD=(python)
      return 0
    fi
  fi
  if command -v py >/dev/null 2>&1; then
    if py -3 -V >/dev/null 2>&1; then
      PYTHON_CMD=(py -3)
      return 0
    fi
  fi
  return 1
}

setup_quality_mode() {
  case "$QUALITY_MODE" in
    quick)
      # Quick preview mode: reduce tessellation and loft slices.
      SCAD_DEFS+=(-D '$fn=28' -D 'LOFT_SLICES=24')
      echo "→ 渲染质量: quick（预览）"
      ;;
    normal)
      echo "→ 渲染质量: normal（默认）"
      ;;
    *)
      echo "错误: 未知 QUALITY_MODE=$QUALITY_MODE（可选: quick / normal）" >&2
      exit 1
      ;;
  esac
}

echo "→ 生成 OpenSCAD 腔体/外壳放样 …"
if detect_python; then
  PYTHONUTF8=1 "${PYTHON_CMD[@]}" "$ROOT/scripts/bezier_to_openscad.py" || {
    echo "错误: bezier_to_openscad.py 失败" >&2
    exit 1
  }
else
  echo "错误: 需要可用的 Python 3（python3/python/py -3）运行 bezier_to_openscad.py" >&2
  exit 1
fi
setup_quality_mode
if [[ ! -f "$GEN" ]] || [[ ! -f "$ENC/generated/profiles.scad" ]]; then
  echo "错误: 未生成 $GEN 或 profiles.scad" >&2
  exit 1
fi
echo ""

export_part() {
  local half="$1"
  local out_file="$2"
  echo "→ 渲染 HALF=${half} …"
  $OPENSCAD_BIN $OPENSCAD_FLAGS -o "$out_file" "${SCAD_DEFS[@]}" -D "HALF=\"${half}\"" "$SCAD"
  if [[ -f "$out_file" ]]; then
    ls -lh "$out_file"
  else
    echo "错误: 未生成 $out_file" >&2
    exit 1
  fi
}

echo "=== SmartPaddle STL 导出（四零件 + 半壳组装）==="
echo "源: $SCAD"
echo "输出: $OUT/"
echo ""

export_part blade_front "$OUT/paddle_blade_front.stl"
export_part blade_back  "$OUT/paddle_blade_back.stl"
export_part handle_front "$OUT/paddle_handle_front.stl"
export_part handle_back  "$OUT/paddle_handle_back.stl"

if [[ "${EXPORT_ASSEMBLED_HALVES:-0}" == "1" ]]; then
  echo "→ 额外导出半壳组装件（较慢）…"
  # 兼容旧流程：前壳 = 拍面前半 + 拍柄前半
  export_part front "$OUT/paddle_shell_front.stl"
  export_part back  "$OUT/paddle_shell_back.stl"
fi

echo ""
echo "完成。四零件:"
echo "  paddle_blade_front.stl / paddle_blade_back.stl"
echo "  paddle_handle_front.stl / paddle_handle_back.stl"
if [[ "${EXPORT_ASSEMBLED_HALVES:-0}" == "1" ]]; then
  echo "半壳组装（前后各一片）:"
  echo "  paddle_shell_front.stl / paddle_shell_back.stl"
else
  echo "如需半壳组装件（较慢），运行:"
  echo "  EXPORT_ASSEMBLED_HALVES=1 ./scripts/export-stl.sh"
fi
echo "如需快速预览模式，运行:"
echo "  QUALITY_MODE=quick ./scripts/export-stl.sh"
