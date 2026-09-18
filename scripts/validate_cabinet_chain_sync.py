#!/usr/bin/env python3
"""Verify that the chain motion contract and exported chain meshes are one build.

This is intentionally a build/provenance check, not a physical chain-load test.
It catches the failure mode where a new motion JSON is paired with older STL
meshes in the browser preview.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


REQUIRED_STL_NAMES = (
    "cabinet_chain_plates.stl",
    "cabinet_chain_rollers.stl",
    "cabinet_chain_pins.stl",
    "cabinet_chain_sprockets.stl",
    "cabinet_chain_idlers.stl",
    "cabinet_chain_bearings.stl",
)


def fail(message: str) -> None:
    raise SystemExit(f"链条预览同步检查失败: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--stl-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.motion.is_file():
        fail(f"找不到运动契约: {args.motion}")
    payload = json.loads(args.motion.read_text(encoding="utf-8"))
    pins = payload.get("pins")
    wheels = payload.get("wheels")
    if not isinstance(pins, list) or len(pins) < 2 or len(pins) % 2:
        fail(f"销路径数量无效: {len(pins) if isinstance(pins, list) else pins!r}")
    if not isinstance(wheels, list) or not wheels:
        fail("没有导出轮位")

    pitch = float(payload.get("p", 0))
    if pitch <= 0:
        fail(f"节距无效: {pitch}")
    distances = []
    for index, point in enumerate(pins):
        try:
            x0, z0 = map(float, point[:2])
            x1, z1 = map(float, pins[(index + 1) % len(pins)][:2])
        except (TypeError, ValueError, IndexError) as exc:
            fail(f"销路径点 {index} 无效: {exc}")
        distances.append(math.hypot(x1 - x0, z1 - z0))
    tolerance = max(0.02, pitch * 0.02)
    if min(distances) < pitch - tolerance or max(distances) > pitch + tolerance:
        fail(
            "销间距不是统一节距: "
            f"min={min(distances):.6f} max={max(distances):.6f} P={pitch:.6f}"
        )

    drive_teeth = int(payload.get("driveTeeth", 0))
    guide_teeth = int(payload.get("guideTeeth", 0))
    sprockets = [wheel for wheel in wheels if wheel.get("kind") == "sprocket"]
    idlers = [wheel for wheel in wheels if wheel.get("kind") == "idler"]
    if len(pins) != 274:
        fail(f"当前 5×3 蛇链应有 274 个销，实际为 {len(pins)}")
    if abs(float(payload.get("chainY", 0)) - 75.0) > 0.01:
        fail(f"后仓链条层位应为 chainY=75.000，实际为 {payload.get('chainY')!r}")
    if abs(pitch - 4.7625) > 0.001:
        fail(f"03C 链条节距应为 4.7625 mm，实际为 {pitch:.6f} mm")
    if len(sprockets) != 1:
        fail(f"主动轮数量应为 1，实际为 {len(sprockets)}")
    if sprockets[0].get("teeth") != drive_teeth:
        fail("主动轮齿数与运动契约不一致")
    if len(idlers) != 8 or any(wheel.get("teeth") != guide_teeth for wheel in idlers):
        if len(idlers) != 8:
            fail(f"当前 5×3 蛇链应有 8 个导向轮，实际为 {len(idlers)}")
        fail("导向轮齿数与运动契约不一致")

    motion_mtime = args.motion.stat().st_mtime_ns
    stale = []
    for name in REQUIRED_STL_NAMES:
        path = args.stl_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"缺少链条 STL: {path}")
        if path.stat().st_mtime_ns < motion_mtime:
            stale.append(name)
    if stale:
        fail("STL 早于运动契约，疑似旧几何: " + ", ".join(stale))

    print(
        "链条预览同步通过: "
        f"pins={len(pins)} wheels={len(wheels)} "
        f"drive={drive_teeth}T idlers={len(idlers)}×{guide_teeth}T "
        f"chainY={float(payload.get('chainY', 0)):.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
