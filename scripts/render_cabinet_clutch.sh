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

# ===== 分区：模型/类型 =====
# Cameras use the cabinet coordinate contract: X=0 is left when facing the
# front. Therefore the true rear view reverses the apparent X order: the
# front-left motor must appear on the right side of assembly-back.png.

# ===== 分区：私有成员 =====
render_view() {
    local name="$1"
    local part="$2"
    local engaged="$3"
    local camera="$4"
    local imgsize="$5"
    local screw_out="${6:-4}"
    local target="${OUT_DIR}/${name}.png"
    mkdir -p "$(dirname "${target}")"
    echo "→ render ${name}.png"
    "${OPENSCAD_BIN}" \
        --backend Manifold \
        --render \
        --viewall \
        --projection=ortho \
        --camera="${camera}" \
        --imgsize="${imgsize}" \
        --colorscheme=BeforeDawn \
        -D "QUALITY=${QUALITY}" \
        -D "CLUTCH_PART=\"${part}\"" \
        -D "ENGAGED=${engaged}" \
        -D "SELECTED_COLUMN=2" \
        -D "SELECTED_ROW=2" \
        -D "CLUTCH_EXPLODE=8" \
        -D "TENSIONER_SCREW_OUT_MM=${screw_out}" \
        -o "${target}" \
        "${SCAD_DIR}/${SCAD_FILE}"
}

# ===== 分区：公开 API =====
[[ -x "${OPENSCAD_BIN}" ]] || { echo "错误: 未找到 OpenSCAD: ${OPENSCAD_BIN}" >&2; exit 1; }
mkdir -p "${OUT_DIR}"
render_view "axes/left-d-axis" "left_d_axis" false "13,380,145,13,76,130" "900,1200"
render_view "axes/right-round-axis" "right_round_axis" false "245,380,145,245,76,130" "900,1200"
render_view "axes/side-axes" "side_axes" false "130,520,135,130,76,135" "1500,1200"
render_view "axes/all-vertical-axes" "all_vertical_axes" false "130,-400,135,130,76,135" "1700,1200"
render_view "tensioner/slide-open" "tensioner_slide" false "300,180,190,238,78,142" "1200,1200" 0
render_view "tensioner/slide-tight" "tensioner_slide" false "300,180,190,238,78,142" "1200,1200" 8
render_view "tensioner/base" "tensioner_base" false "285,145,160,235,76,141" "1200,900"
render_view "tensioner/carriage" "tensioner_carriage" false "285,145,160,235,76,141" "1200,900"
render_view "tensioner/pulley-top-closeup" "tensioner_pulley_top" false "300,170,270,262,76,222" "1200,1000"
render_view "assembly-back" "assembly" false "130,520,116,130,60,116" "1600,1200"
render_view "assembly-front" "assembly" false "130,-400,116,130,60,116" "1600,1200"
render_view "assembly-iso" "assembly" false "370,330,300,130,60,116" "1600,1200"
render_view "clutch-detail-open" "clutch_detail" false "150,220,210,140,81,140" "1200,1000"
render_view "clutch-detail-engaged" "clutch_detail" true "150,220,210,140,73,136" "1200,1000"
render_view "clutch-detail-side-open" "clutch_detail" false "280,130,150,140,76,139" "1200,1000"
render_view "clutch-detail-side-engaged" "clutch_detail" true "280,130,150,140,76,139" "1200,1000"

# ===== 分区：逐件预览 =====
# The selected verification station is column 2 / row 2. These views are
# deliberately close so the mating faces and layer order can be inspected.
render_view "parts/01-motor-vertical" "motor" false "13,380,145,13,76,130" "1000,1200"
render_view "parts/02-drive-column" "column" false "140,380,145,140,76,145" "1100,1200"
render_view "parts/03-vertical-rack" "vertical_rack" false "140,380,145,140,76,145" "900,1200"
render_view "parts/04-right-tensioner" "idler" false "300,180,190,238,78,142" "1000,1200"
render_view "parts/05-bus-belts" "bus_belt" false "360,260,260,140,76,143" "1500,900"
render_view "parts/06-upper-axis-y-spur" "upper_spur" false "155,120,155,140,76,139" "900,800"
render_view "parts/07-upper-downward-dog" "upper_dog" false "155,120,155,140,76,135" "900,800"
render_view "parts/08-lower-upward-dog" "lower_dog" false "155,120,155,140,76,131" "900,800"
render_view "parts/09-rear-takeoff-pulley" "rear_pulley" false "155,120,155,140,76,126" "900,800"
render_view "parts/10-spring" "spring" false "155,120,155,140,76,134" "900,800"
render_view "parts/11-t-countersunk-screw" "screw" false "155,120,155,140,76,139" "900,800"
render_view "parts/12-clutch-fork" "fork" false "155,120,155,140,76,140" "900,800"
render_view "parts/13-drawer-belt" "drawer_belt" false "170,145,150,140,44,126" "1100,850"
render_view "parts/14-front-timing-pulley" "front_pulley" false "155,100,155,140,14,126" "900,800"
render_view "parts/15-front-pinion" "front_gear" false "155,100,155,140,14,131" "900,800"
render_view "parts/16-drawer-linear-rack" "drawer_rack" false "155,100,155,140,35,131" "1100,800"
echo "完成: ${OUT_DIR}"
