#!/usr/bin/env bash
# Export paddle shell STLs: four parts + optional assembled front/back halves.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENC="$ROOT/enclosure"
OUT="$ENC/stl"
SCAD="$ENC/paddle_shell.scad"
QUALITY_MODE="${QUALITY_MODE:-normal}"
M6_PROCESS="${M6_PROCESS:-print}"
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
  case "$M6_PROCESS" in
    print|cnc)
      SCAD_DEFS+=(-D "m6_process=\"${M6_PROCESS}\"")
      echo "→ M6 工艺公差: $M6_PROCESS"
      ;;
    *)
      echo "错误: 未知 M6_PROCESS=$M6_PROCESS（可选: print / cnc）" >&2
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
  $OPENSCAD_BIN $OPENSCAD_FLAGS -o "$out_file" ${SCAD_DEFS[@]+"${SCAD_DEFS[@]}"} -D "HALF=\"${half}\"" "$SCAD"
  if [[ -f "$out_file" ]]; then
    ls -lh "$out_file"
  else
    echo "错误: 未生成 $out_file" >&2
    exit 1
  fi
}

echo "=== SmartPaddle M6 STL 完整导出 ==="
echo "源: $SCAD"
echo "输出: $OUT/"
echo ""

# 交互式子命令: ./scripts/export-stl.sh tip
if [[ "${1:-}" == "tip" ]]; then
  TIP_LENGTH="${TIP_LENGTH:-25}"
  echo "→ 导出 M6 背面合体尾部 ${TIP_LENGTH}mm 切片（装配验证用）"
  $OPENSCAD_BIN $OPENSCAD_FLAGS -o "$OUT/paddle_m6_handle_back_tip.stl" \
    ${SCAD_DEFS[@]+"${SCAD_DEFS[@]}"} \
    -D "HALF=\"m6_handle_back_tip\"" \
    -D "TIP_LENGTH=${TIP_LENGTH}" \
    "$SCAD"
  if [[ -f "$OUT/paddle_m6_handle_back_tip.stl" ]]; then
    ls -lh "$OUT/paddle_m6_handle_back_tip.stl"
  else
    echo "错误: 未生成 paddle_m6_handle_back_tip.stl" >&2
    exit 1
  fi
  echo ""
  echo "完成：paddle_m6_handle_back_tip.stl (${TIP_LENGTH}mm)"
  echo ""
  echo "如需指定长度: TIP_LENGTH=30 ./scripts/export-stl.sh tip"
  exit 0
fi

SKIP_STEP6="${SKIP_STEP6:-0}"

# M6 是破坏性工艺升级：移除旧四件/半壳名称，避免误打印旧结构。
rm -f \
  "$OUT"/paddle_blade_front.stl "$OUT"/paddle_blade_back.stl \
  "$OUT"/paddle_handle_front.stl "$OUT"/paddle_handle_back.stl \
  "$OUT"/paddle_shell_front.stl "$OUT"/paddle_shell_back.stl \
  "$OUT"/paddle_split_assembly.stl "$OUT"/paddle_handle_back_tip.stl \
  "$OUT"/paddle_handle_tail.stl

export_part m6_skin_front "$OUT/paddle_m6_layer1_handle_skin_front.stl"
export_part m6_core_front "$OUT/paddle_m6_layer2_core_front.stl"
export_part m6_core_back "$OUT/paddle_m6_layer3_core_back.stl"
export_part m6_skin_back "$OUT/paddle_m6_layer4_handle_skin_back.stl"
export_part m6_monolithic_front "$OUT/paddle_m6_monolithic_front.stl"
export_part m6_monolithic_back "$OUT/paddle_m6_monolithic_back.stl"
export_part m6_assembly "$OUT/paddle_m6_assembly.stl"
export_part m6_exploded "$OUT/paddle_m6_exploded.stl"

TIP_LENGTH="${TIP_LENGTH:-25}"
echo "→ M6 背面合体尾部切片 ${TIP_LENGTH}mm …"
$OPENSCAD_BIN $OPENSCAD_FLAGS -o "$OUT/paddle_m6_handle_back_tip.stl" \
  ${SCAD_DEFS[@]+"${SCAD_DEFS[@]}"} \
  -D "HALF=\"m6_handle_back_tip\"" \
  -D "TIP_LENGTH=${TIP_LENGTH}" \
  "$SCAD" || true

# Step6：若 pcb-tail 存在，用尾板干涉已导出拍柄，覆盖最终打印件
if [[ "$SKIP_STEP6" != "1" ]]; then
  STEP6="$ROOT/scripts/step6_tail_board_interfere_handle.py"
  PCB_TAIL="$ROOT/pcb-tail/layouts/default/default.kicad_pcb"
  if [[ -f "$STEP6" && -f "$PCB_TAIL" ]]; then
    echo ""
    echo "→ Step6：pcb-tail 干涉 M6 四层与合体件 …"
    STEP6_PY="$ROOT/scripts/.venv-stl/bin/python"
    if [[ ! -x "$STEP6_PY" ]]; then
      STEP6_PY="${PYTHON_CMD[0]:-python3}"
    fi
    if ! "$STEP6_PY" "$STEP6"; then
      echo "警告: Step6 失败；OpenSCAD 基线 STL 仍保留（未含尾板开孔）" >&2
    fi
  else
    echo ""
    echo "→ 跳过 Step6（无 pcb-tail 板文件）；输出为无尾板干涉的基线壳"
  fi
fi

echo ""
echo "→ 写入 M6 工艺预览 manifest …"
"${PYTHON_CMD[@]}" "$ROOT/scripts/write_preview_manifest.py"

echo ""
echo "完成。最终打印件（enclosure/stl/）:"
echo "  paddle_m6_layer{1..4}_*.stl      ← 四层分制"
echo "  paddle_m6_monolithic_{front,back}.stl"
echo "  paddle_m6_{assembly,exploded}.stl"
echo "  paddle_m6_handle_back_tip.stl"
echo "跳过尾板干涉: SKIP_STEP6=1 ./scripts/export-stl.sh"
echo "快速预览:     QUALITY_MODE=quick ./scripts/export-stl.sh"
echo "CNC 榫槽:     M6_PROCESS=cnc ./scripts/export-stl.sh"
