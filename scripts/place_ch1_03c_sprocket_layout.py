#!/usr/bin/env python3
"""Place existing CH1 03C sprocket STLs into a 1x-left / 2x-right layout."""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "output" / "3d-print"
LAYOUT_DIR = ROOT / "output" / "3d-print" / "sprocket-layout"
CENTER_DISTANCE_MM = 200.0
LEFT_SIZE = "1x"
RIGHT_SIZE = "2x"
VERTEX_RE = re.compile(
    r"^(\s*vertex\s+)([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)(\s*)$",
    re.IGNORECASE,
)

# ===== 分区：模型/类型 =====
Point = tuple[float, float, float]


# ===== 分区：私有成员 =====
def die(message: str) -> None:
    print(f"错误: {message}", file=sys.stderr)
    raise SystemExit(1)


def source_stl(size: str) -> Path:
    path = SOURCE_DIR / f"ch1_03c_sprocket_{size}.stl"
    if not path.is_file():
        die(f"找不到现成链轮 STL: {path}")
    return path


def collect_vertices(text: str) -> list[Point]:
    points: list[Point] = []
    for line in text.splitlines():
        match = VERTEX_RE.match(line)
        if match is None:
            continue
        points.append((float(match.group(2)), float(match.group(3)), float(match.group(4))))
    if not points:
        die("STL 里没有 vertex，无法平移")
    return points


def bbox_center(points: list[Point]) -> Point:
    mins = [min(point[axis] for point in points) for axis in range(3)]
    maxs = [max(point[axis] for point in points) for axis in range(3)]
    return (
        (mins[0] + maxs[0]) / 2.0,
        (mins[1] + maxs[1]) / 2.0,
        (mins[2] + maxs[2]) / 2.0,
    )


def translate_ascii(text: str, offset: Point) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        match = VERTEX_RE.match(line)
        if match is None:
            lines.append(line)
            continue
        x = float(match.group(2)) + offset[0]
        y = float(match.group(3)) + offset[1]
        z = float(match.group(4)) + offset[2]
        lines.append(f"{match.group(1)}{x:.8f} {y:.8f} {z:.8f}{match.group(5)}")
    return "\n".join(lines) + "\n"


def place_sprocket(size: str, target_center: Point, dest: Path) -> dict[str, object]:
    src = source_stl(size)
    text = src.read_text(encoding="utf-8", errors="replace")
    if "facet" not in text.lower():
        die(f"{src} 不是 ASCII STL，当前布局脚本只平移现成 ASCII 网格")
    center = bbox_center(collect_vertices(text))
    offset = (
        target_center[0] - center[0],
        target_center[1] - center[1],
        target_center[2] - center[2],
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(translate_ascii(text, offset), encoding="utf-8")
    placed_center = bbox_center(collect_vertices(dest.read_text(encoding="utf-8")))
    return {
        "size": size,
        "source": str(src),
        "dest": str(dest),
        "sourceCenterMm": [round(value, 4) for value in center],
        "targetCenterMm": [round(value, 4) for value in target_center],
        "placedCenterMm": [round(value, 4) for value in placed_center],
        "bytes": dest.stat().st_size,
    }


# ===== 分区：公开 API =====
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--center-distance",
        type=float,
        default=CENTER_DISTANCE_MM,
        help="1x 中心到 2x 中心的 X 向距离，默认 200 mm",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=LAYOUT_DIR,
        help="布局 STL 输出目录",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.center_distance <= 0:
        die("--center-distance 必须大于 0")
    out_dir = args.out_dir.expanduser().resolve()
    left = place_sprocket(
        LEFT_SIZE,
        (0.0, 0.0, 0.0),
        out_dir / "ch1_03c_sprocket_1x_left.stl",
    )
    right = place_sprocket(
        RIGHT_SIZE,
        (args.center_distance, 0.0, 0.0),
        out_dir / "ch1_03c_sprocket_2x_right.stl",
    )
    left_x = float(left["placedCenterMm"][0])  # type: ignore[index]
    right_x = float(right["placedCenterMm"][0])  # type: ignore[index]
    report = {
        "units": "mm",
        "note": "复用已导出链轮 STL，不重新跑 OpenSCAD。200 mm 是布局中心距，不是节圆相切啮合距。",
        "centerDistanceMm": round(right_x - left_x, 4),
        "parts": [left, right],
    }
    report_path = out_dir / "layout.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if abs(report["centerDistanceMm"] - args.center_distance) > 0.05:
        die(
            f"中心距 {report['centerDistanceMm']} mm 偏离目标 {args.center_distance} mm"
        )
    return 0


# ===== 分区：业务逻辑 =====
# 1x 放 X=0，2x 放 X=center-distance；平移包围盒中心，不改齿形或缩放。

# ===== 分区：方法/工具 =====
if __name__ == "__main__":
    raise SystemExit(main())
