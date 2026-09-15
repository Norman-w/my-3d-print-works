#!/usr/bin/env bash
# Render repeatable OpenSCAD views for the drawer clutch mechanism.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad/enclosure"
SCAD_FILE="cabinet_clutch.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_DIR="${PROJECT_ROOT}/output/previews/cabinet-clutch"
QUALITY="${QUALITY:-2}"
SHOW_LEGACY_STATIONS="${SHOW_LEGACY_STATIONS:-false}"

# ===== 分区：模型/类型 =====
# Cameras use the user/world coordinate contract: X=width, Y=height, Z=depth.
# The front is Z=0 and the rear is +Z, so a true rear view looks along -Z and
# reverses the apparent X order. The SCAD scene itself is authored in this
# frame; these cameras only select the observation direction.

# ===== 分区：私有成员 =====
render_view() {
    local name="$1"
    local part="$2"
    local engaged="$3"
    local camera="$4"
    local imgsize="$5"
    local screw_out="${6:-4}"
    local fit="${7:-1}"
    local target="${OUT_DIR}/${name}.png"
    mkdir -p "$(dirname "${target}")"
    echo "→ render ${name}.png"
    local viewall_args=(--autocenter)
    if [[ "${fit}" == "1" ]]; then
        viewall_args+=(--viewall)
    fi
    "${OPENSCAD_BIN}" \
        --backend Manifold \
        --render \
        "${viewall_args[@]-}" \
        --projection=ortho \
        --camera="${camera}" \
        --imgsize="${imgsize}" \
        --colorscheme=BeforeDawn \
        -D "QUALITY=${QUALITY}" \
        -D "CLUTCH_PART=\"${part}\"" \
        -D "ENGAGED=${engaged}" \
        -D "SELECTED_COLUMN=2" \
        -D "SELECTED_ROW=2" \
        -D "SHOW_LEGACY_STATIONS=${SHOW_LEGACY_STATIONS}" \
        -D "CLUTCH_EXPLODE=8" \
        -D "TENSIONER_SCREW_OUT_MM=${screw_out}" \
        -o "${target}" \
        "${SCAD_DIR}/${SCAD_FILE}"
}

# ===== 分区：公开 API =====
[[ -x "${OPENSCAD_BIN}" ]] || { echo "错误: 未找到 OpenSCAD: ${OPENSCAD_BIN}" >&2; exit 1; }
mkdir -p "${OUT_DIR}"
render_view "axes/left-d-axis" "left_d_axis" false "247,130,76,0,0,0,500" "900,1200"
render_view "axes/side-axes" "side_axes" false "130,130,76,0,90,0,500" "1500,1200"
render_view "axes/all-vertical-axes" "all_vertical_axes" false "130,130,76,0,0,0,500" "1700,1200"
render_view "tensioner/parametric" "tensioner_t_solid" false "18,214,86,-20,215,0,500" "1200,1200"
render_view "assembly-back" "assembly" false "130,116,60,0,180,0,500" "1600,1200"
render_view "assembly-front" "assembly" false "130,116,60,0,0,0,500" "1600,1200"
render_view "assembly-iso" "assembly" false "130,116,60,-25,215,0,650" "1600,1200"
render_view "world-axes" "world_axes" false "0,0,0,-25,215,0,100" "1000,900"
render_view "clutch-detail-open" "clutch_detail" false "150,140,76,-20,215,0,500" "1200,1000"
render_view "clutch-detail-engaged" "clutch_detail" true "150,140,76,-20,215,0,500" "1200,1000"
render_view "clutch-detail-side-open" "clutch_detail" false "150,140,76,0,90,0,500" "1200,1000"
render_view "clutch-detail-side-engaged" "clutch_detail" true "150,140,76,0,90,0,500" "1200,1000"

# ===== 分区：逐件预览 =====
# The selected verification station is column 2 / row 2. These views are
# deliberately close so the mating faces and layer order can be inspected.
render_view "parts/01-motor-vertical" "motor" false "247,130,76,-20,0,0,500" "1000,1200"
render_view "parts/02-drive-column" "column" false "130,130,76,-20,0,0,500" "1100,1200"
render_view "parts/03-vertical-rack" "vertical_rack" false "130,130,76,-20,0,0,500" "900,1200"
render_view "parts/04-right-tensioner" "tensioner_t_solid" false "18,214,86,-20,215,0,500" "1000,1200"
render_view "parts/05-power-bus" "power_bus" false "130,130,76,-20,180,0,500" "1500,900"
render_view "parts/06-upper-axis-z-spur" "upper_spur" false "140,140,76,-20,215,0,500" "900,800"
render_view "parts/07-upper-downward-dog" "upper_dog" false "140,140,76,-20,215,0,500" "900,800"
render_view "parts/08-lower-upward-dog" "lower_dog" false "140,140,76,-20,215,0,500" "900,800"
render_view "parts/09-rear-takeoff-pulley" "rear_pulley" false "140,140,76,-20,215,0,500" "900,800"
render_view "parts/13-drawer-belt" "drawer_belt" false "140,140,76,-20,215,0,500" "1100,850"
render_view "parts/14-front-timing-pulley" "front_pulley" false "140,140,14,-20,0,0,500" "900,800"
render_view "parts/15-front-pinion" "front_gear" false "140,140,14,-20,0,0,500" "900,800"
render_view "parts/16-drawer-linear-rack" "drawer_rack" false "140,140,14,-20,0,0,500" "1100,800"
echo "完成: ${OUT_DIR}"
