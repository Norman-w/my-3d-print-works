#!/usr/bin/env python3
"""Write the small M7-LB1 manifest used by the 光板打印 page."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "enclosure" / "stl" / "lightboard"
OUT = STL / "preview" / "lightboard_manifest.json"

PARTS = [
    ("stage_planform", "整拍轮廓", "preview/stage_planform.stl", "#38bdf8", "inspection"),
    ("stage_solid_blade", "拍面实心承力区", "preview/stage_solid_blade.stl", "#f59e0b", "inspection"),
    ("stage_handle_cavity", "拍柄下段贝塞尔内腔", "preview/stage_handle_cavity.stl", "#22d3ee", "interference"),
    ("skin_front", "第1层·拍柄正面外贴", "paddle_m7_lb1_layer1_handle_skin_front.stl", "#3b82f6", "skin"),
    ("core_front", "第2层·拍面实心主承力板", "paddle_m7_lb1_layer2_core_front.stl", "#ef4444", "core"),
    ("core_back", "第3层·拍面实心主承力板", "paddle_m7_lb1_layer3_core_back.stl", "#991b1b", "core"),
    ("skin_back", "第4层·拍柄背面外贴", "paddle_m7_lb1_layer4_handle_skin_back.stl", "#1d4ed8", "skin"),
    ("monolithic_front", "正面无缝合体", "paddle_m7_lb1_monolithic_front.stl", "#f59e0b", "monolithic"),
    ("monolithic_back", "背面无缝合体", "paddle_m7_lb1_monolithic_back.stl", "#d97706", "monolithic"),
    ("assembly", "M7-LB1 四层装配", "paddle_m7_lb1_assembly.stl", "#94a3b8", "assembly"),
    ("exploded", "M7-LB1 四层爆炸图", "paddle_m7_lb1_exploded.stl", "#cbd5e1", "assembly"),
    ("fasteners_front", "拍柄侧边第2层→第1层螺丝", "preview/fasteners_front.stl", "#e5e7eb", "fastener"),
    ("fasteners_back", "拍柄侧边第3层→第4层螺丝", "preview/fasteners_back.stl", "#aeb8c6", "fastener"),
    ("fasteners_through", "拍柄三点第1层→第4层贯穿螺丝", "preview/fasteners_through.stl", "#d1fae5", "fastener"),
    ("fasteners_blade", "拍面第2层→第3层螺丝", "preview/fasteners_blade.stl", "#f8fafc", "fastener"),
    ("silicone_plugs", "拍柄三点M2硅胶盖", "preview/silicone_plugs.stl", "#111827", "plug"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def component(item: tuple[str, str, str, str, str]) -> dict[str, object]:
    ident, label, relative, color, kind = item
    path = STL / relative
    return {
        "id": ident,
        "label": label,
        "path": f"/stl/lightboard/{relative}?v={sha256(path)[:16]}",
        "color": color,
        "kind": kind,
        "opacity": 0.62 if kind == "interference" else 1.0,
    }


def main() -> int:
    components = [component(item) for item in PARTS if (STL / item[2]).is_file()]
    available = {str(item["id"]) for item in components}

    def present(*ids: str) -> list[str]:
        return [ident for ident in ids if ident in available]

    overlays = present(
        "fasteners_front", "fasteners_back", "fasteners_through",
        "fasteners_blade", "silicone_plugs",
    )
    plates = []
    for ident, label, filename, description in (
        (
            "layers_1_2",
            "拼板 A · 第1+2层",
            "paddle_m7_lb1_print_plate_layers_1_2",
            "沿用原 M7 两件拼板流程；拍面实体不含电子挖空。",
        ),
        (
            "layers_3_4",
            "拼板 B · 第3+4层",
            "paddle_m7_lb1_print_plate_layers_3_4",
            "沿用原 M7 摆放和支撑检查；装配接口保持原尺寸。",
        ),
    ):
        stl = STL / "print" / f"{filename}.stl"
        three_mf = STL / "print" / f"{filename}.3mf"
        if stl.is_file() and three_mf.is_file():
            plates.append({
                "id": ident,
                "label": label,
                "path": f"/stl/lightboard/print/{filename}.stl?v={sha256(stl)[:16]}",
                "threeMfPath": f"/stl/lightboard/print/{filename}.3mf?v={sha256(three_mf)[:16]}",
                "description": description,
            })

    manifest = {
        "schemaVersion": 1,
        "modelVersion": "M7-LB1",
        "baseModel": "M7.C5",
        "variantLabel": "光板版",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "coordinateSystem": {"x": "拍宽", "y": "拍长", "z": "层叠/厚度"},
        "components": components,
        "printPlates": plates,
        "processSteps": [
            {
                "id": "assembled",
                "label": "四层装配",
                "description": "沿用原 M7 的装配位置和紧固件；拍面与红框肩颈段保持实心，拍柄下段保留内腔。",
                "components": present("assembly"),
                "overlays": overlays,
                "camera": "full_paddle",
            },
            {
                "id": "solid_blade",
                "label": "拍面实心",
                "description": "拍头区域不切 PCB、PZT 或器件腔。",
                "components": present("stage_solid_blade"),
                "camera": "full_paddle",
            },
            {
                "id": "handle_cavity",
                "label": "拍柄内腔",
                "description": "只在肩颈实体加强段之后保留参考图所示的收窄贝塞尔手柄内腔。",
                "components": present("stage_handle_cavity"),
                "camera": "full_handle",
            },
            {
                "id": "four_layers",
                "label": "四层打印件",
                "description": "第1/4层为拍柄外贴，第2/3层贯通拍面和拍柄。",
                "components": present("skin_front", "core_front", "core_back", "skin_back"),
                "overlays": overlays,
                "camera": "exploded_layers",
            },
        ],
        "processTypes": [
            {"id": "print", "label": "四层打印", "components": present("skin_front", "core_front", "core_back", "skin_back")},
            {"id": "assembly", "label": "装配", "components": present("assembly"), "overlays": overlays},
        ],
        "cameraPresets": [
            {"id": "full_paddle", "label": "整拍", "target": [0, -50, 0], "position": [170, -270, 150]},
            {"id": "full_handle", "label": "拍柄", "target": [0, -122, 0], "position": [70, -235, 65]},
            {"id": "exploded_layers", "label": "四层爆炸", "target": [0, -70, 0], "position": [180, -260, 120]},
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
