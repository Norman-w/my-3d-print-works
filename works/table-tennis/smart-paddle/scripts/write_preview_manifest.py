#!/usr/bin/env python3
"""Write the data-driven M7 process-preview manifest."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "enclosure" / "stl"
OUT = STL / "preview" / "manifest.json"
SCREW_SAFETY_REPORT = ROOT / "enclosure" / "generated" / "m7_screw_safety.json"

PARTS = [
    ("stage_planform", "01·整拍贝塞尔平面轮廓", "preview/stage_planform.stl", "#38bdf8", "inspection"),
    ("stage_handle_envelope", "02·拍柄贝塞尔人体工学包络", "preview/stage_handle_envelope.stl", "#8b5cf6", "inspection"),
    ("stage_continuous_blank", "03·头柄连续承力毛坯", "preview/stage_continuous_blank.stl", "#f59e0b", "inspection"),
    ("stage_voids", "04·内部挖空与电子空间", "preview/stage_voids.stl", "#22d3ee", "interference"),
    ("skin_front", "第1层·拍柄正面外贴", "paddle_m7_layer1_handle_skin_front.stl", "#3b82f6", "skin"),
    ("core_front", "第2层·正面主承力板", "paddle_m7_layer2_core_front.stl", "#ef4444", "core"),
    ("core_back", "第3层·背面主承力板", "paddle_m7_layer3_core_back.stl", "#991b1b", "core"),
    ("skin_back", "第4层·拍柄背面外贴", "paddle_m7_layer4_handle_skin_back.stl", "#1d4ed8", "skin"),
    ("monolithic_front", "正面无缝合体打印件", "paddle_m7_monolithic_front.stl", "#f59e0b", "monolithic"),
    ("monolithic_back", "背面无缝合体打印件", "paddle_m7_monolithic_back.stl", "#d97706", "monolithic"),
    ("fasteners_front", "拍柄侧边第2层→第1层螺丝", "preview/fasteners_front.stl", "#e5e7eb", "fastener"),
    ("fasteners_back", "拍柄侧边第3层→第4层螺丝", "preview/fasteners_back.stl", "#aeb8c6", "fastener"),
    ("fasteners_through", "拍柄三点第1层→第4层贯穿螺丝", "preview/fasteners_through.stl", "#d1fae5", "fastener"),
    ("fasteners_blade", "拍面第2层→第3层沉头螺丝", "preview/fasteners_blade.stl", "#f8fafc", "fastener"),
    ("silicone_plugs", "拍柄三点M2硅胶盖", "preview/silicone_plugs.stl", "#111827", "plug"),
    ("assembly", "M7 四层装配", "paddle_m7_assembly.stl", "#94a3b8", "assembly"),
    ("exploded", "M7 四层爆炸图", "paddle_m7_exploded.stl", "#cbd5e1", "assembly"),
    ("tail", "M7 拍柄尾段", "paddle_m7_handle_tail.stl", "#64748b", "inspection"),
    ("board_slot", "尾板槽干涉体", "interference/board_slot.stl", "#22c55e", "interference"),
    ("ui_cuts", "USB/按键/LED 干涉体", "interference/ui_cuts.stl", "#f97316", "interference"),
]

PRINT_PLATES = [
    (
        "layers_1_2",
        "拼板 A：第1块 + 第2块",
        "print/paddle_m7_print_plate_layers_1_2.stl",
        "第1+2层修复版：已恢复大镂空区靠拍头PCB穿透M2承力柱；保持既有摆放，尚未按X1C左前禁区重新排版，请导入后人工确认，不能作为X1C最终免检文件",
    ),
    (
        "layers_3_4",
        "拼板 B：第3块 + 第4块",
        "print/paddle_m7_print_plate_layers_3_4.stl",
        "X1C验证拼板：第3层长承力板平放45°并自动左移，第4层上下翻正、以自动识别的物理底座面落床竖立并自动右移到肩颈区域；真实投影独立且避开左前禁区，装配接口原尺寸；请为竖立件开启树状自动支撑",
    ),
]


# ===== 分区：私有成员 =====
def _component(item: tuple[str, str, str, str, str]) -> dict[str, object]:
    ident, label, path, color, kind = item
    return {
        "id": ident,
        "label": label,
        "path": f"/stl/{path}",
        "color": color,
        "kind": kind,
        "opacity": 0.72 if kind == "interference" else 1.0,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ===== 分区：公开 API =====
def main() -> int:
    components = [_component(item) for item in PARTS if (STL / item[2]).is_file()]
    available = {str(item["id"]) for item in components}

    def present(*ids: str) -> list[str]:
        return [ident for ident in ids if ident in available]

    fastener_overlays = present(
        "fasteners_front", "fasteners_back", "fasteners_through", "fasteners_blade",
        "silicone_plugs"
    )
    screw_safety = (
        json.loads(SCREW_SAFETY_REPORT.read_text(encoding="utf-8"))
        if SCREW_SAFETY_REPORT.is_file()
        else {}
    )

    manifest = {
        "schemaVersion": 1,
        "modelVersion": "M7",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "coordinateSystem": {"x": "拍宽", "y": "拍长", "z": "层叠/厚度"},
        "components": components,
        "printPlates": [
            {
                "id": ident,
                "label": label,
                "path": f"/stl/{path}?v={_sha256(STL / path)[:16]}",
                "description": description,
            }
            for ident, label, path, description in PRINT_PLATES
            if (STL / path).is_file()
        ],
        "fastenerSafetyMap": [
            item for item in screw_safety.get("directionChecks", [])
            if item.get("visualCallout") is not None
        ],
        "processSteps": [
            {
                "id": "profile_intent",
                "label": "01 运动边界：整拍贝塞尔轮廓",
                "description": "先由拍宽、拍长、甜区和挥拍边界确定连续平面轮廓，不急着分件。",
                "components": present("stage_planform"),
                "camera": "full_paddle",
            },
            {
                "id": "handle_ergonomics",
                "label": "02 握持定义：拍柄贝塞尔包络",
                "description": "围绕手掌接触、尾端收束和内部空间建立随长度变化的三维截面。",
                "components": present("stage_handle_envelope"),
                "camera": "full_handle",
            },
            {
                "id": "continuous_load_path",
                "label": "03 承力连续：拍头与拍柄合体",
                "description": "先形成不带孔洞的连续承力毛坯，消除头柄接缝和突变薄弱点。",
                "components": present("stage_continuous_blank"),
                "camera": "head_handle_joint",
            },
            {
                "id": "hollowing",
                "label": "04 空间分配：挖空与电子腔",
                "description": "在连续毛坯中分配空腔、主板和走线空间，再检查剩余壁厚与承力路径。",
                "components": present("monolithic_front", "monolithic_back", "stage_voids"),
                "overlays": fastener_overlays,
                "camera": "handle_internals",
            },
            {
                "id": "four_layers",
                "label": "05 制造拆分：四层连续承力",
                "description": "根据打印、CNC 和装配可达性拆成 1–4 层，同时保持第 2/3 层贯通头柄。",
                "components": present("skin_front", "core_front", "core_back", "skin_back"),
                "overlays": fastener_overlays,
                "camera": "exploded_layers",
            },
            {
                "id": "handle_fasteners",
                "label": "06 紧固闭环：侧边2→1/3→4 · 三点M2 1→4",
                "description": "侧边阵列从第 2/3 层向外攻丝，三颗 M2 从第 1 层贯穿到第 4 层；拍面由第 2 层攻入第 3 层。",
                "components": present("skin_front", "core_front", "core_back", "skin_back"),
                "overlays": fastener_overlays,
                "camera": "handle_fasteners",
            },
            {
                "id": "tail_interference",
                "label": "07 机电校核：尾板、USB 与开孔",
                "description": "用真实 KiCad 尾板和接口包络做布尔干涉，确认装入、插拔和开孔余量。",
                "components": present("tail", "board_slot", "ui_cuts"),
                "camera": "tail_pcb",
            },
            {
                "id": "assembled",
                "label": "08 收敛验证：最终装配",
                "description": "合并所有结构与紧固件，检查外形连续、内部避让、壁厚和可制造性。",
                "components": present("assembly"),
                "overlays": fastener_overlays,
                "camera": "full_paddle",
            },
        ],
        "processTypes": [
            {"id": "print", "label": "3D打印", "components": present("monolithic_front", "monolithic_back"), "overlays": fastener_overlays},
            {"id": "layered", "label": "木板/CNC四层", "components": present("skin_front", "core_front", "core_back", "skin_back"), "overlays": fastener_overlays},
            {"id": "interference", "label": "电子干涉", "components": present("tail", "board_slot", "ui_cuts")},
        ],
        "cameraPresets": [
            {"id": "full_paddle", "label": "整拍", "target": [0, -50, 0], "position": [170, -270, 150]},
            {"id": "full_handle", "label": "拍柄贝塞尔", "target": [0, -112, 0], "position": [70, -235, 65]},
            {"id": "head_handle_joint", "label": "头柄连接", "target": [0, -82, 0], "position": [65, -135, 45]},
            {"id": "handle_internals", "label": "内部挖空", "target": [0, -125, 0], "position": [85, -215, 55]},
            {"id": "handle_fasteners", "label": "拍柄1→4贯穿螺丝", "target": [0, -122, 0], "position": [42, -158, 28]},
            {"id": "tail_fasteners", "label": "尾端抗变形螺丝", "target": [0, -166, 0], "position": [35, -205, 22]},
            {"id": "tail_pcb", "label": "尾板/USB", "target": [0, -174, 0], "position": [0, -230, 0]},
            {"id": "exploded_layers", "label": "四层爆炸", "target": [0, -70, 0], "position": [180, -260, 120]},
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
