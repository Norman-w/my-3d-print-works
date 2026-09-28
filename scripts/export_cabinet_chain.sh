#!/usr/bin/env bash
# Export rear-cavity 03C snake chain STLs into the existing HTTP preview.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/resolve_preview_tools.sh"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad/enclosure"
SCAD_FILE="cabinet_chain.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_STL="${PROJECT_ROOT}/output/3d-print/cabinet-chain"
OUT_CLUTCH="${PROJECT_ROOT}/output/3d-print/cabinet-clutch"
OUT_PNG="${PROJECT_ROOT}/output/previews"
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
PARTS=(plates rollers pins sprockets idlers bearings idler_axles clutch_trigger_carrier clutch_trigger_magnet clutch_trigger_connecting_pins clutch_trigger_retaining_clip motor motor_shaft motor_cover motor_spring_hardware)
QUALITY="${QUALITY:-2}"

# ===== 分区：模型/类型 =====
# plates / rollers / pins 是外购链条；sprockets / idlers 是后仓轮。

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

export_stl() {
    local part="$1"
    local dest="${OUT_STL}/cabinet_chain_${part}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL PART=${part} QUALITY=${QUALITY} → ${dest}"
    (
        cd "$SCAD_DIR"
        local backend="Manifold"
        # The single-piece carrier contains a through pocket, two pin bores,
        # and overlapping root/pod solids.  CGAL is the authoritative export
        # backend for this part because it preserves a watertight boolean
        # result; the display-only chain solids keep the faster Manifold path.
        [[ "$part" == "clutch_trigger_carrier" ]] && backend="CGAL"
        "$OPENSCAD_BIN" \
            --backend "$backend" \
            --export-format binstl \
            -D "CHAIN_PART=\"${part}\"" \
            -D "QUALITY=${QUALITY}" \
            -o "$tmp" \
            "$SCAD_FILE"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

patch_manifest() {
    python3 - "$PREVIEW_DIR/manifest.json" "$MANIFEST_SEMANTICS_BACKUP" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
semantics_path = Path(sys.argv[2])
payload = json.loads(path.read_text(encoding="utf-8"))
previous = {}
if semantics_path.is_file():
    previous = json.loads(semantics_path.read_text(encoding="utf-8"))
previous_parts = {
    str(part.get("id")): part
    for part in previous.get("parts", [])
    if isinstance(part, dict) and part.get("id")
}
payload["title"] = "零件柜 · 后仓横走 03C + 张紧 U"
payload["units"] = "mm"
payload["up"] = "y"
obsolete_cabinet_ids = {
    "cabinet-clutch/cabinet_clutch_cabinet",
    "cabinet-clutch/cabinet_clutch_cabinet_context",
}
payload["parts"] = [
    part for part in payload.get("parts", [])
    if part.get("id") not in obsolete_cabinet_ids
]
models_dir = path.parent / "models" / "cabinet-clutch"
for stale_name in (
    "cabinet_clutch_cabinet.stl",
    "cabinet_clutch_cabinet_context.stl",
):
    stale_path = models_dir / stale_name
    if stale_path.exists() or stale_path.is_symlink():
        stale_path.unlink()
names = {
    "cabinet_shell": {
        "name": "柜体（外框+隔板+格栅）",
        "role": "printed",
        "color": "#6f8f9a",
        "explosion": [0, 0, 0],
        "visible": False,
    },
    "cabinet_back_panel": {
        "name": "可拆背板",
        "role": "printed",
        "color": "#c4a574",
        "explosion": [0, 48, 0],
        "visible": False,
    },
    "cabinet_chain_plates": {
        "name": "03C 蛇形链板",
        "role": "purchased",
        "color": "#8A919C",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_rollers": {
        "name": "03C 滚子",
        "role": "purchased",
        "color": "#E8EDF2",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_pins": {
        "name": "03C 销轴",
        "role": "purchased",
        "color": "#B08D57",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_sprockets": {
        "name": "12T 尖齿唯一主动轮（D 轴）",
        "role": "printed",
        "color": "#5b9fd6",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_idlers": {
        "name": "8T 小尺寸绿色钝齿轴承导向轮（9颗）",
        "role": "printed",
        "color": "#7dcc4a",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_idler_axles": {
        "name": "绿色导向轮固定轴·M3 肩螺钉/Ø3 光杆×9（采购件参考）",
        "role": "purchased",
        "color": "#aeb6bf",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_bearings": {
        "name": "3×6×2 轴承（装配显示/采购件）",
        "role": "purchased",
        "color": "#b9c2ca",
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_clutch_trigger_carrier": {
        "name": "03C 蛇形链条·后侧圆角矩形 M5 磁铁一体拖尾（PETG）",
        "role": "printed",
        "color": "#d9933d",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_clutch_trigger_magnet": {
        "name": "蛇形链条·M5×4 触发磁铁（采购件参考）",
        "role": "purchased",
        "color": "#5b6670",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_clutch_trigger_connecting_pins": {
        "name": "03C 蛇形链条·17.50 mm 双卡槽穿销×2（现成采购件）",
        "role": "purchased",
        "color": "#b08d57",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_clutch_trigger_retaining_clip": {
        "name": "03C 蛇形链条·双卡槽 U 形固定卡×2（现成采购件）",
        "role": "purchased",
        "color": "#9aa7b6",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor": {
        "name": "蛇形链条唯一驱动电机本体（右下张紧位）",
        "role": "purchased",
        "color": "#424a54",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_shaft": {
        "name": "蛇形链条驱动 D 输出轴（右下，随动力轮转动）",
        "role": "purchased",
        "color": "#d6d9dc",
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_cover": {
        "name": "蛇形链条电机 Ω 固定套（四孔套 Ø5×12 Boss；M3 下压）",
        "role": "printed",
        "color": "#56616d",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_spring_hardware": {
        "name": "蛇链电机固定座·四组硬弹簧与下压蘑菇头螺丝",
        "role": "purchased",
        "color": "#c9a227",
        "explosion": [0, 0, 0],
    },
}
# Keep the single root viewer complete when this chain export is run after
# the drawer/clutch export.  The manifest writer scans all supplied folders;
# these mappings restore the canonical mechanism folders and labels for the
# native-world drawer parts instead of leaving raw filenames in the tree.
names.update({
    "cabinet_clutch_cabinet_frame": {
        "name": "箱体·上下左右外框 + X+立板 + 前部层格/立格 + 前后仓隔板皮带孔 + 后仓贯通 + 前下实体面",
        "role": "printed", "color": "#6f8f9a", "opacity": 0.30, "visible": True,
    },
    "00_tensioner_t_solid_reference": {"name": "右侧张紧滑台 · SKP 参数化", "color": "#aebdce"},
    "13_drawer_timing_belt_reference": {"name": "抽屉同步皮带"},
    "14_front_timing_pulley_candidate": {"name": "前方同步轮"},
    "15_front_pinion_candidate": {"name": "抽屉底部驱动齿轮"},
    "16_drawer_linear_rack_candidate": {"name": "抽屉底部直线齿排"},
})
clutch_group_map = {
    "cabinet_clutch_cabinet_frame": "00·箱体框架",
    "00_tensioner_t_solid_reference": "01·动力母线",
    "13_drawer_timing_belt_reference": "03·抽屉驱动",
    "14_front_timing_pulley_candidate": "03·抽屉驱动",
    "15_front_pinion_candidate": "03·抽屉驱动",
    "16_drawer_linear_rack_candidate": "03·抽屉驱动",
}
for part in payload.get("parts", []):
    extra = names.get(Path(str(part.get("file", ""))).stem)
    if extra is not None:
        part.update(extra)
        part["visible"] = extra.get("visible", True)
    group_id = clutch_group_map.get(Path(str(part.get("file", ""))).stem)
    if group_id is not None:
        part["group"] = group_id

# The chain exporter may run by itself after the full clutch exporter.  The
# STL scanner knows files and colors, but not the authored world/frame tree or
# the shared-template motion metadata. Carry those semantics forward instead
# of silently replacing the canonical assembly with a flat file list.
semantic_keys = (
    "placement", "motion", "instances", "instanceCount", "instanceMode",
    "templateSourceId", "animationRole", "componentMode", "componentCount",
    "componentBindings", "assemblyRole",
)
for part in payload.get("parts", []):
    old = previous_parts.get(str(part.get("id")))
    if old is not None:
        for key in semantic_keys:
            if key in old:
                part[key] = old[key]
    if isinstance(previous.get("assembly"), dict) and "placement" not in part:
        part_id = str(part.get("id", ""))
        parent = "chain-source" if part_id.startswith("cabinet-chain/") else "world"
        part["placement"] = {
            "geometrySpace": "source-adapter" if parent == "chain-source" else "world",
            "parentFrameId": parent,
            "mode": "instances" if part.get("instances") else "single",
        }
chain_trigger_component_specs = {
    "cabinet-chain/cabinet_chain_clutch_trigger_carrier": {
        "id": "carrier",
        "role": "printed-carrier",
        "parent": "chain-segment",
        "mountRelation": "two-adjacent-03C-pin-bores",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_connecting_pins": {
        "id": "connecting-pins",
        "role": "purchased-extended-pins",
        "parent": "carrier+chain-segment",
        "mountRelation": "paired-pin-bores",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_retaining_clip": {
        "id": "retaining-clips",
        "role": "purchased-retaining-clips",
        "parent": "connecting-pins",
        "mountRelation": "two-groove-capture",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_magnet": {
        "id": "magnet",
        "role": "purchased-magnet",
        "parent": "carrier",
        "mountRelation": "rear-rounded-tail-through-seat",
    },
}
for part in payload.get("parts", []):
    spec = chain_trigger_component_specs.get(str(part.get("id")))
    if not spec:
        continue
    part["assemblyId"] = "chain-trigger-assembly"
    part["assemblyRole"] = spec["role"]
    part["componentMode"] = "rigid-mounted-component"
    part["componentId"] = spec["id"]
    part["mountRelation"] = {
        "parent": spec["parent"],
        "interface": spec["mountRelation"],
        "motion": "shared-rigid-chain-segment-pose",
    }
    part.setdefault("placement", {}).update({
        "assemblyId": "chain-trigger-assembly",
        "assemblyFrameId": "chain-source",
        "mountRelationRef": "chainTriggerAssembly.mountRelations",
    })
if isinstance(previous.get("assembly"), dict):
    payload["assembly"] = previous["assembly"]
group_order = ["00·箱体框架", "01·动力母线", "02·离合机构", "03·抽屉驱动", "99·总装配检查体"]
counts = {}
for part in payload.get("parts", []):
    group_id = str(part.get("group") or "未分组")
    counts[group_id] = counts.get(group_id, 0) + 1
ordered = [group_id for group_id in group_order if counts.get(group_id)]
ordered += sorted(group_id for group_id in counts if group_id not in group_order)
payload["groups"] = [{"id": group_id, "name": group_id, "count": counts[group_id]} for group_id in ordered]
payload["groupCount"] = len(payload["groups"])

if isinstance(previous.get("tree"), list):
    parts_by_id = {
        str(part.get("id")): part
        for part in payload.get("parts", [])
        if part.get("id")
    }

    def refresh_tree(node):
        if not isinstance(node, dict):
            return
        part_id = node.get("partId")
        if part_id in parts_by_id:
            node["name"] = parts_by_id[part_id].get("name") or node.get("name")
        for child in node.get("children", []):
            refresh_tree(child)

    for root in previous["tree"]:
        refresh_tree(root)
    referenced = set()

    def collect_tree(node):
        if not isinstance(node, dict):
            return
        if node.get("kind") == "part" and node.get("partId"):
            referenced.add(str(node["partId"]))
        for child in node.get("children", []):
            collect_tree(child)

    for root in previous["tree"]:
        collect_tree(root)
    missing = [
        part for part in payload.get("parts", [])
        if str(part.get("id")) not in referenced
    ]
    chain_folder = next(
        (root for root in previous["tree"]
         if root.get("kind") == "folder" and root.get("groupId") == "cabinet-chain"),
        None,
    )
    if chain_folder is None and any(str(part.get("id", "")).startswith("cabinet-chain/") for part in missing):
        chain_folder = {
            "id": "cabinet-chain",
            "kind": "folder",
            "groupId": "cabinet-chain",
            "name": "cabinet-chain",
            "children": [],
        }
        previous["tree"].append(chain_folder)
    for part in missing:
        if not str(part.get("id", "")).startswith("cabinet-chain/") or chain_folder is None:
            continue
        trigger_part_ids = set(chain_trigger_component_specs)
        if str(part.get("id")) in trigger_part_ids:
            trigger_folder = next(
                (
                    child for child in chain_folder.get("children", [])
                    if child.get("kind") == "call"
                    and child.get("id") == "call:chain/trigger-assembly"
                ),
                None,
            )
            if trigger_folder is None:
                trigger_folder = {
                    "id": "call:chain/trigger-assembly",
                    "kind": "call",
                    "name": "03C 蛇形链条·触发组件（双长穿销 + 两卡簧 + 一体磁台 + M5磁铁）",
                    "description": "四个 STL 是一个刚性挂载组件：载架套两根相邻 STL-Y 长穿销，卡簧扣入卡槽，M5×4 磁铁装入载架后侧圆角拖尾贯通座，由用户螺丝固定；动画共享链节中点姿态。",
                    "children": [],
                }
                chain_folder.setdefault("children", []).insert(0, trigger_folder)
            trigger_folder.setdefault("children", []).append({
                "id": f"part:{part['id']}",
                "kind": "part",
                "partId": part["id"],
                "name": part.get("name") or part["id"],
            })
            continue
        chain_folder.setdefault("children", []).append({
            "id": f"part:{part['id']}",
            "kind": "part",
            "partId": part["id"],
            "name": part.get("name") or part["id"],
        })
    payload["treeVersion"] = previous.get("treeVersion", 1)
    payload["tree"] = previous["tree"]
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
path.write_text(text, encoding="utf-8")
path.with_name("parts.json").write_text(text, encoding="utf-8")
print(f"已标注零件名: {path}")
PY
}

# ===== 分区：公开 API =====
[[ -x "$OPENSCAD_BIN" ]] || die "找不到 OpenSCAD: $OPENSCAD_BIN"
mkdir -p "$OUT_STL" "$OUT_PNG"

# Preserve the canonical world/frame tree while this script refreshes the
# chain-specific STL files.  The backup is intentionally temporary and never
# becomes a generated project artifact.
MANIFEST_SEMANTICS_BACKUP="${TMPDIR:-/tmp}/smartpartsdrawer-manifest-semantics.$$.json"
if [[ -f "$PREVIEW_DIR/manifest.json" ]]; then
    cp "$PREVIEW_DIR/manifest.json" "$MANIFEST_SEMANTICS_BACKUP"
fi
trap 'rm -f "$MANIFEST_SEMANTICS_BACKUP"' EXIT

# The current world assembly has one canonical motor/cover and one ordinary
# 03C chain. Remove retired standalone libraries and highlighted connector
# meshes so a stale scan cannot reintroduce duplicate or non-installed parts.
rm -rf \
    "${PROJECT_ROOT}/output/3d-print/cabinet" \
    "${PROJECT_ROOT}/output/3d-print/motor-library" \
    "${PROJECT_ROOT}/output/3d-print/motor-mount" \
    "${PROJECT_ROOT}/output/3d-print/chain-hardware" \
    "${PROJECT_ROOT}/output/3d-print/chain-clutch" \
    "${PREVIEW_DIR}/models/motor-library" \
    "${PREVIEW_DIR}/models/motor-mount" \
    "${PREVIEW_DIR}/models/chain-hardware" \
    "${PREVIEW_DIR}/models/chain-clutch"

# Retired chain diagnostics were intentionally hidden before, but their stale
# STLs were still scanned into the tree. Remove the derived files now that the
# current world uses the native center clutch and the single M5 trigger carrier.
OBSOLETE_CHAIN_OUTPUTS=(
    "cabinet_chain_motor_tensioner.stl"
    "cabinet_chain_scheme1_power_wheels.stl"
    "cabinet_chain_scheme1_output_wheels.stl"
    "cabinet_chain_scheme1_clutch_faces.stl"
    "cabinet_chain_scheme1_bearings.stl"
    "cabinet_chain_scheme1_selector.stl"
    "cabinet_chain_connector.stl"
    "cabinet_chain_clutch_connector.stl"
    "cabinet_chain_clutch_bearing.stl"
)
for old_file in "${OBSOLETE_CHAIN_OUTPUTS[@]}"; do
    rm -f "${OUT_STL}/${old_file}"
    rm -f "${PREVIEW_DIR}/models/cabinet-chain/${old_file}"
done

echo "→ 按真实节距闭合链条 / 张紧轮"
python3 "${PROJECT_ROOT}/scripts/solve_cabinet_chain.py"

for part in "${PARTS[@]}"; do
    export_stl "$part"
done

if [[ -f "$INSPECT_PY" ]]; then
    for part in sprockets idlers bearings idler_axles clutch_trigger_carrier clutch_trigger_magnet clutch_trigger_connecting_pins clutch_trigger_retaining_clip motor motor_shaft motor_cover motor_spring_hardware; do
        echo "→ inspect cabinet_chain_${part}.stl"
        python3 "$INSPECT_PY" --require-watertight "${OUT_STL}/cabinet_chain_${part}.stl"
    done
    for part in plates rollers pins; do
        echo "→ inspect cabinet_chain_${part}.stl"
        python3 "$INSPECT_PY" "${OUT_STL}/cabinet_chain_${part}.stl"
    done
fi

python3 "${PROJECT_ROOT}/scripts/validate_cabinet_chain_sync.py" \
    --motion "${OUT_STL}/cabinet_chain_motion.json" \
    --stl-dir "${OUT_STL}"

if [[ -f "$MANIFEST_PY" ]]; then
    # Rebuild the canonical clutch model folder before scanning.  The manifest
    # writer updates the JSON but intentionally does not remove dangling links
    # left by retired parts from an older export.
    rm -rf "$PREVIEW_DIR/models/cabinet-clutch"
    args=(--preview-dir "$PREVIEW_DIR" --title "零件柜 · 后仓横走 03C + 张紧 U" --no-recursive)
    [[ -d "$OUT_CLUTCH" ]] && args+=(--stl-dir "$OUT_CLUTCH")
    args+=(--stl-dir "$OUT_STL")
    python3 "$MANIFEST_PY" "${args[@]}"
    patch_manifest
    mkdir -p "${PREVIEW_DIR}/js" "${PREVIEW_DIR}/models/cabinet-chain"
    cp "${PROJECT_ROOT}/web/cabinet-preview/index.html" "${PREVIEW_DIR}/index.html"
    cp "${PROJECT_ROOT}/web/cabinet-preview/app.js" "${PREVIEW_DIR}/app.js"
    cp "${PROJECT_ROOT}/web/cabinet-preview/js/cabinet-chain-play.js" "${PREVIEW_DIR}/js/cabinet-chain-play.js"
    MOTION_JSON="${OUT_STL}/cabinet_chain_motion.json"
    if [[ -f "$MOTION_JSON" ]]; then
        ln -sfn "$MOTION_JSON" "${PREVIEW_DIR}/models/cabinet-chain/cabinet_chain_motion.json"
    fi
fi

echo "完成:"
for part in "${PARTS[@]}"; do
    echo "  STL  ${OUT_STL}/cabinet_chain_${part}.stl"
done
echo "  预览保持现有 HTTP 服务，刷新即可"

# ===== 分区：业务逻辑 =====
# 不 restart 预览端口；链条 STL 只用于观看，不要当 FDM 打印件。

# ===== 分区：方法/工具 =====
# QUALITY 可用环境变量覆盖，默认 2。
