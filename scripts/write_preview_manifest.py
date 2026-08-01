#!/usr/bin/env python3
"""Write the data-driven M6 process-preview manifest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "enclosure" / "stl"
OUT = STL / "preview" / "manifest.json"

PARTS = [
    ("skin_front", "第1层·拍柄正面外贴", "paddle_m6_layer1_handle_skin_front.stl", "#3b82f6", "skin"),
    ("core_front", "第2层·正面主承力板", "paddle_m6_layer2_core_front.stl", "#ef4444", "core"),
    ("core_back", "第3层·背面主承力板", "paddle_m6_layer3_core_back.stl", "#991b1b", "core"),
    ("skin_back", "第4层·拍柄背面外贴", "paddle_m6_layer4_handle_skin_back.stl", "#1d4ed8", "skin"),
    ("monolithic_front", "正面无缝合体打印件", "paddle_m6_monolithic_front.stl", "#f59e0b", "monolithic"),
    ("monolithic_back", "背面无缝合体打印件", "paddle_m6_monolithic_back.stl", "#d97706", "monolithic"),
    ("assembly", "M6 四层装配", "paddle_m6_assembly.stl", "#94a3b8", "assembly"),
    ("exploded", "M6 四层爆炸图", "paddle_m6_exploded.stl", "#cbd5e1", "assembly"),
    ("tail", "M6 拍柄尾段", "paddle_m6_handle_tail.stl", "#64748b", "inspection"),
    ("board_slot", "尾板槽干涉体", "interference/board_slot.stl", "#22c55e", "interference"),
    ("ui_cuts", "USB/按键/LED 干涉体", "interference/ui_cuts.stl", "#f97316", "interference"),
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


# ===== 分区：公开 API =====
def main() -> int:
    components = [_component(item) for item in PARTS if (STL / item[2]).is_file()]
    available = {str(item["id"]) for item in components}

    def present(*ids: str) -> list[str]:
        return [ident for ident in ids if ident in available]

    manifest = {
        "schemaVersion": 1,
        "modelVersion": "M6",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "coordinateSystem": {"x": "拍宽", "y": "拍长", "z": "层叠/厚度"},
        "components": components,
        "processSteps": [
            {
                "id": "monolithic",
                "label": "合体打印·头柄无缝",
                "components": present("monolithic_front", "monolithic_back"),
                "camera": "head_handle_joint",
            },
            {
                "id": "four_layers",
                "label": "四层分制",
                "components": present("skin_front", "core_front", "core_back", "skin_back"),
                "camera": "exploded_layers",
            },
            {
                "id": "handle_fasteners",
                "label": "正反大件螺丝压紧",
                "components": present("monolithic_front", "monolithic_back"),
                "camera": "handle_fasteners",
            },
            {
                "id": "tail_interference",
                "label": "尾板与开孔干涉",
                "components": present("tail", "board_slot", "ui_cuts"),
                "camera": "tail_pcb",
            },
            {
                "id": "assembled",
                "label": "最终装配",
                "components": present("assembly"),
                "camera": "full_paddle",
            },
        ],
        "processTypes": [
            {"id": "print", "label": "3D打印", "components": present("monolithic_front", "monolithic_back")},
            {"id": "layered", "label": "木板/CNC四层", "components": present("skin_front", "core_front", "core_back", "skin_back")},
            {"id": "interference", "label": "电子干涉", "components": present("tail", "board_slot", "ui_cuts")},
        ],
        "cameraPresets": [
            {"id": "full_paddle", "label": "整拍", "target": [0, -50, 0], "position": [170, -270, 150]},
            {"id": "head_handle_joint", "label": "头柄连接", "target": [0, -82, 0], "position": [65, -135, 45]},
            {"id": "handle_fasteners", "label": "拍柄螺丝", "target": [0, -122, 0], "position": [42, -158, 28]},
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
