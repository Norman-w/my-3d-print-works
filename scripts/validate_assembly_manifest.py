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

    station_frames = sorted(
        frame_id for frame_id in frame_by_id if frame_id.startswith("station:R")
    )
    if len(station_frames) != 15:
        fail(f"站点 frame 数量必须为 15: {len(station_frames)}")
    expected_non_center_stations = {
        frame_id.removeprefix("station:")
        for frame_id in station_frames
        if frame_id != "station:R2C3"
    }
    if "tensioner-shaft-adjustment" not in frame_by_id:
        fail("缺少张紧轮共享 X 向调节 frame")
    tensioner_frame = frame_by_id["tensioner-shaft-adjustment"]
    if tensioner_frame.get("kind") != "prismatic" or tensioner_frame.get("axis") != [1, 0, 0]:
        fail("张紧轮共享 frame 必须是 +X prismatic")
    for support_id in ("tensioner-lower", "tensioner-upper"):
        if frame_by_id.get(support_id, {}).get("parentFrameId") != "tensioner-shaft-adjustment":
            fail(f"{support_id} 没有挂到共享张紧轮 X 调节 frame")

    template_parts = [part for part in parts if part.get("templateSourceId")]
    if not template_parts:
        fail("缺少共享 STL 模板实例")
    expected_roles = {
        "clutch-input-rotor",
        "clutch-output-rotor",
        "drawer-belt",
        "drawer-rotary",
        "drawer-moving",
    }
    roles = {str(part.get("animationRole")) for part in template_parts}
    missing_roles = sorted(expected_roles - roles)
    if missing_roles:
        fail("共享模板缺少动画角色: " + ", ".join(missing_roles))
    for part in template_parts:
        if part.get("placement", {}).get("mode") != "instances":
            fail(f"共享模板必须使用 instances: {part.get('id')}")
        if part.get("instanceCount") != 14:
            fail(f"共享模板实例数必须为 14: {part.get('id')}")
        if part.get("templateSourceId") not in part_ids:
            fail(f"共享模板来源不存在: {part.get('id')}")
        instance_ids = {
            str(instance.get("id"))
            for instance in part.get("instances", [])
            if instance.get("id")
        }
        if instance_ids != expected_non_center_stations:
            fail(f"共享模板站点实例必须覆盖除 R2C3 外的 14 格: {part.get('id')}")

    tensioner_id = "cabinet-clutch/cabinet_clutch_column_sync_tensioner_integral"
    tensioner_part = next((part for part in parts if part.get("id") == tensioner_id), None)
    if tensioner_part is None or tensioner_part.get("instanceCount") != 2:
        fail("张紧机构必须由一个 STL 源挂载上下两个实例")
    if not all(
        isinstance(instance.get("position"), list)
        and len(instance.get("position")) == 3
        for instance in (tensioner_part or {}).get("instances", [])
    ):
        fail("张紧机构上下实例缺少三维世界定位")
    if tensioner_part.get("componentMode") != "connected-islands":
        fail("张紧机构必须声明一份 STL 的 connected-islands 分岛装配")
    if tensioner_part.get("componentCount") != 2:
        fail("张紧机构必须恰好有固定 C 与移动 T 两个连接岛")
    bindings = tensioner_part.get("componentBindings")
    if not isinstance(bindings, list) or len(bindings) != 2:
        fail("张紧机构缺少固定 C/移动 T 两个 componentBindings")
    binding_by_id = {str(binding.get("id")): binding for binding in bindings}
    if set(binding_by_id) != {"fixed-capture", "moving-housing"}:
        fail("张紧机构 componentBindings 名称不完整")
    fixed_binding = binding_by_id["fixed-capture"]
    moving_binding = binding_by_id["moving-housing"]
    if (
        fixed_binding.get("selection") != "largest-bounds-y"
        or fixed_binding.get("parentFrameId") != "power-bus-fixed"
        or fixed_binding.get("transform") != "instance-world-position"
    ):
        fail("张紧机构固定 C 岛没有按每个实例世界位置挂到箱体固定 frame")
    if (
        moving_binding.get("selection") != "remaining"
        or moving_binding.get("parentFrameId") != "instance-parent"
        or moving_binding.get("transform") != "instance-local-transform"
    ):
        fail("张紧机构移动 T 岛没有挂到上下张紧滑台 frame")
    rotor_id = "cabinet-clutch/cabinet_clutch_column_sync_tensioner_rotor"
    rotor_part = next((part for part in parts if part.get("id") == rotor_id), None)
    if rotor_part is None or rotor_part.get("placement", {}).get("motionFrameId") != "tensioner-shaft-adjustment":
        fail("张紧轮转子没有绑定共享 X 向调节 frame")

    print(
        "装配坐标清单检查通过: "
        f"frames={len(frame_by_id)} parts={len(parts)} "
        f"instances={instance_total} motions={motion_total} stations={len(station_frames)} "
        f"sharedTemplates={len(template_parts)} root={root_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
