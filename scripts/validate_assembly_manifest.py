#!/usr/bin/env python3
"""Validate the SCAD -> manifest -> Three.js assembly coordinate contract.

This checks source/preview coordinate ownership only. It does not claim that
an STL is printed, physically assembled, or load-tested.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"装配坐标清单检查失败: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if not args.manifest.is_file():
        fail(f"找不到 manifest: {args.manifest}")

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    assembly = payload.get("assembly")
    if not isinstance(assembly, dict):
        fail("缺少 assembly 坐标树")
    if assembly.get("schemaVersion") != 1:
        fail(f"assembly schemaVersion 无效: {assembly.get('schemaVersion')!r}")
    coordinate = assembly.get("coordinateSystem")
    if not isinstance(coordinate, dict) or coordinate.get("units") != "mm":
        fail("assembly 必须明确使用 mm")
    frames = assembly.get("frames")
    if not isinstance(frames, list) or not frames:
        fail("assembly.frames 为空")
    frame_by_id = {}
    for frame in frames:
        frame_id = str(frame.get("id", ""))
        if not frame_id:
            fail("存在空 frame id")
        if frame_id in frame_by_id:
            fail(f"frame id 重复: {frame_id}")
        frame_by_id[frame_id] = frame
    root_id = str(assembly.get("rootFrameId", ""))
    if root_id not in frame_by_id:
        fail(f"rootFrameId 不存在: {root_id}")
    if frame_by_id[root_id].get("parentFrameId") is not None:
        fail("根 frame 不能有父级")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(frame_id: str) -> None:
        if frame_id in visiting:
            fail(f"frame 父级存在环: {frame_id}")
        if frame_id in visited:
            return
        visiting.add(frame_id)
        parent_id = frame_by_id[frame_id].get("parentFrameId")
        if parent_id is not None:
            parent_id = str(parent_id)
            if parent_id not in frame_by_id:
                fail(f"frame {frame_id} 的父级不存在: {parent_id}")
            visit(parent_id)
        visiting.remove(frame_id)
        visited.add(frame_id)

    for frame_id in frame_by_id:
        visit(frame_id)

    parts = payload.get("parts")
    if not isinstance(parts, list) or not parts:
        fail("parts 为空")
    part_ids: set[str] = set()
    instance_total = 0
    motion_total = 0
    for part in parts:
        part_id = str(part.get("id", ""))
        if not part_id:
            fail("存在空 part id")
        if part_id in part_ids:
            fail(f"part id 重复: {part_id}")
        part_ids.add(part_id)
        placement = part.get("placement")
        if not isinstance(placement, dict):
            fail(f"{part_id} 缺少 placement")
        geometry_space = placement.get("geometrySpace")
        if geometry_space not in {"world", "local-template", "source-adapter"}:
            fail(f"{part_id} geometrySpace 无效: {geometry_space!r}")
        parent_id = str(placement.get("parentFrameId", ""))
        if parent_id not in frame_by_id:
            fail(f"{part_id} 的 parentFrameId 不存在: {parent_id}")
        mode = placement.get("mode")
        instances = part.get("instances")
        if mode == "instances":
            if not isinstance(instances, list) or not instances:
                fail(f"{part_id} 声明 instances 但没有实例")
            if part.get("instanceCount") != len(instances):
                fail(f"{part_id} instanceCount 与实例数量不一致")
            for instance in instances:
                instance_parent = str(instance.get("parentFrameId", ""))
                if instance_parent not in frame_by_id:
                    fail(f"{part_id}/{instance.get('id')} 的实例父级不存在: {instance_parent}")
                transform = instance.get("localTransform")
                if not isinstance(transform, dict):
                    fail(f"{part_id}/{instance.get('id')} 缺少 localTransform")
                instance_total += 1
        elif instances:
            fail(f"{part_id} 有 instances 但 placement.mode 不是 instances")

        motion = part.get("motion")
        motion_frame = placement.get("motionFrameId")
        if motion is not None:
            if not isinstance(motion, dict):
                fail(f"{part_id} motion 不是对象")
            motion_frame = motion.get("frameId", motion_frame)
        if motion_frame is not None:
            motion_frame = str(motion_frame)
            if motion_frame not in frame_by_id:
                fail(f"{part_id} 的运动 frame 不存在: {motion_frame}")
            motion_total += 1
        if geometry_space == "local-template" and mode != "instances":
            fail(f"{part_id} 局部模板必须使用 instances 模式")

    expected_frames = {"world", "cabinet-fixed", "power-bus-fixed", "drawer-drive-fixed", "chain-source"}
    missing = sorted(expected_frames - frame_by_id.keys())
    if missing:
        fail("缺少基础 frame: " + ", ".join(missing))

    print(
        "装配坐标清单检查通过: "
        f"frames={len(frame_by_id)} parts={len(parts)} "
        f"instances={instance_total} motions={motion_total} root={root_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
