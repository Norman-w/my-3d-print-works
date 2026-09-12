#!/usr/bin/env python3
"""蛇形同步带弧长路径：20T 节圆包角 + U 弧导靴 + 回程惰轮，带长取 N×3mm。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math
from typing import Any

from fc_config import (
    DEFAULT_SELECTOR_SPEED_MM_S,
    HTD_BELT_THICKNESS_MM,
    HTD_BELT_WIDTH_MM,
    HTD_DRIVE_TEETH,
    HTD_PITCH_MM,
    drive_pitch_radius_mm,
    pulley_rpm,
)
from fc_htd import no_slip_deg

# ===== 分区：常量/配置 =====
PHASE_LABELS = (
    "INDEX / 选格",
    "ENGAGE / 啮合",
    "DRIVE / 推拉",
    "RELEASE / 释放",
    "RETURN / 回HOME",
    "HOME / 安全",
)
PHASE_HOLD_S = (None, 0.62, 1.18, 0.48, None, 0.62)
ARC_STEP_MM = 0.9
LINE_STEP_MM = 4.0
BACK_CLEAR_MM = 28.0
MOTOR_EXTRA_MM = 24.0
BELT_BODY_MM = max(2.4, HTD_BELT_THICKNESS_MM)
WRAP_CLEAR_MM = 0.8

# ===== 分区：模型/类型 =====
# 节段：line / arc；arc 上 wrap=drive|return|shoe 表示皮带贴在轮或导靴上。

# ===== 分区：私有成员 =====
def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def _ease(value: float) -> float:
    t = _clamp(value, 0.0, 1.0)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0

def _cell_center(cfg, col: int, layer: int) -> tuple[float, float]:
    x = cfg.margin_x + col * (cfg.cell_width + cfg.cell_gap_x) + cfg.cell_width * 0.5
    y = cfg.margin_y + layer * (cfg.cell_depth + cfg.cell_gap_y) + cfg.cell_depth * 0.5
    return x, y

def _serpentine_order(columns: int, layers: int) -> list[int]:
    order: list[int] = []
    for row in range(layers):
        reverse = row % 2 == 1
        for step in range(columns):
            col = columns - 1 - step if reverse else step
            order.append(row * columns + col)
    return order

def _push_point(points: list[tuple[float, float, float]], x: float, y: float, z: float) -> None:
    if points:
        px, py, _ = points[-1]
        if math.hypot(x - px, y - py) < 0.05:
            return
    points.append((x, y, z))

def _add_line(points: list[tuple[float, float, float]], x1: float, y1: float, z: float) -> None:
    if not points:
        _push_point(points, x1, y1, z)
        return
    x0, y0, _ = points[-1]
    dist = math.hypot(x1 - x0, y1 - y0)
    steps = max(1, int(math.ceil(dist / LINE_STEP_MM)))
    for step in range(1, steps + 1):
        t = step / steps
        _push_point(points, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z)

def _add_arc(points: list[tuple[float, float, float]], cx: float, cy: float, radius: float, a0: float, a1: float, z: float) -> None:
    sweep = abs(a1 - a0)
    steps = max(6, int(math.ceil(radius * sweep / ARC_STEP_MM)))
    for step in range(1, steps + 1):
        ang = a0 + (a1 - a0) * step / steps
        _push_point(points, cx + math.cos(ang) * radius, cy + math.sin(ang) * radius, z)

def _decorate(raw: list[tuple[float, float, float]]) -> list[dict[str, float]]:
    samples: list[dict[str, float]] = []
    acc = 0.0
    for index, point in enumerate(raw):
        if index > 0:
            acc += math.hypot(point[0] - raw[index - 1][0], point[1] - raw[index - 1][1])
        if index < len(raw) - 1:
            tx = raw[index + 1][0] - point[0]
            ty = raw[index + 1][1] - point[1]
        elif index > 0:
            tx = point[0] - raw[index - 1][0]
            ty = point[1] - raw[index - 1][1]
        else:
            tx, ty = 1.0, 0.0
        mag = math.hypot(tx, ty) or 1.0
        samples.append({
            "x": round(point[0], 4),
            "y": round(point[1], 4),
            "z": round(point[2], 4),
            "s": round(acc, 4),
            "tx": round(tx / mag, 6),
            "ty": round(ty / mag, 6),
        })
    return samples

def _add_outward(samples: list[dict[str, float]]) -> list[dict[str, float]]:
    if not samples:
        return samples
    cx = sum(p["x"] for p in samples) / len(samples)
    cy = sum(p["y"] for p in samples) / len(samples)
    for point in samples:
        ox, oy = point["x"] - cx, point["y"] - cy
        rx, ry = point["ty"], -point["tx"]
        if rx * ox + ry * oy < 0.0:
            rx, ry = -rx, -ry
        mag = math.hypot(rx, ry) or 1.0
        point["nx"] = round(rx / mag, 6)
        point["ny"] = round(ry / mag, 6)
    return samples

def _point_at(samples: list[dict[str, float]], distance: float) -> dict[str, float]:
    if not samples:
        return {"x": 0.0, "y": 0.0, "z": 0.0, "s": 0.0, "tx": 1.0, "ty": 0.0}
    length = samples[-1]["s"]
    target = _clamp(distance, 0.0, length) if length > 0 else 0.0
    for index in range(1, len(samples)):
        if target <= samples[index]["s"]:
            span = samples[index]["s"] - samples[index - 1]["s"]
            t = 0.0 if span == 0 else (target - samples[index - 1]["s"]) / span
            prev = samples[index - 1]
            nxt = samples[index]
            tx = prev["tx"] + (nxt["tx"] - prev["tx"]) * t
            ty = prev["ty"] + (nxt["ty"] - prev["ty"]) * t
            mag = math.hypot(tx, ty) or 1.0
            return {
                "x": prev["x"] + (nxt["x"] - prev["x"]) * t,
                "y": prev["y"] + (nxt["y"] - prev["y"]) * t,
                "z": prev["z"] + (nxt["z"] - prev["z"]) * t,
                "s": target,
                "tx": tx / mag,
                "ty": ty / mag,
                "nx": prev.get("nx", ty / mag),
                "ny": prev.get("ny", -tx / mag),
            }
    last = dict(samples[-1])
    last["s"] = target
    return last

def point_at_distance(samples: list[dict[str, float]], distance: float, closed_length: float = 0.0) -> dict[str, float]:
    length = closed_length or (samples[-1]["s"] if samples else 0.0)
    if length > 0:
        distance = distance % length
    return _point_at(samples, distance)

def _raw_from_segments(segments: list[dict[str, Any]]) -> list[tuple[float, float, float]]:
    raw: list[tuple[float, float, float]] = []
    for seg in segments:
        if seg["kind"] == "line":
            if not raw:
                _push_point(raw, seg["x0"], seg["y0"], seg["z"])
            _add_line(raw, seg["x1"], seg["y1"], seg["z"])
        else:
            if not raw:
                a0 = seg["a0"]
                _push_point(raw, seg["cx"] + math.cos(a0) * seg["radius"], seg["cy"] + math.sin(a0) * seg["radius"], seg["z"])
            _add_arc(raw, seg["cx"], seg["cy"], seg["radius"], seg["a0"], seg["a1"], seg["z"])
    return raw

def _working_segments(cells: list[dict], order: list[int], first: dict, turn_r: float, z: float) -> tuple[list[dict], list[dict]]:
    segments: list[dict[str, Any]] = []
    shoes: list[dict[str, Any]] = []
    for seq, cell_index in enumerate(order[1:], start=1):
        prev = cells[order[seq - 1]]
        nxt = cells[cell_index]
        if abs(prev["y"] - nxt["y"]) < 0.05:
            segments.append({"kind": "line", "x0": prev["x"], "y0": prev["y"], "x1": nxt["x"], "y1": nxt["y"], "z": z})
            continue
        cx = prev["x"]
        cy = (prev["y"] + nxt["y"]) / 2.0
        outward = 1.0 if prev["x"] > first["x"] + 1.0 else -1.0
        going_plus_y = nxt["y"] > prev["y"]
        if going_plus_y:
            a0 = -math.pi / 2.0
            a1 = math.pi / 2.0 if outward > 0 else -math.pi * 1.5
        else:
            a0 = math.pi / 2.0
            a1 = -math.pi / 2.0 if outward > 0 else math.pi * 1.5
        segments.append({"kind": "arc", "cx": cx, "cy": cy, "radius": turn_r, "a0": a0, "a1": a1, "z": z, "wrap": "shoe"})
        shoes.append({"x": cx, "y": cy, "z": z, "radius": turn_r, "a0": a0, "a1": a1})
    return segments, shoes

def _closed_segments(cfg, first: dict, last: dict, motor_x: float, motor_y: float, pitch_r: float, wrap_r: float, working_segs: list[dict], z: float, back_extra: float) -> tuple[list[dict], list[dict]]:
    back_y = last["y"] + cfg.cell_depth * 0.5 + BACK_CLEAR_MM + back_extra
    idler_a = {"name": "SelectorIdler_20T_A", "x": last["x"], "y": back_y - wrap_r, "z": z, "teeth": HTD_DRIVE_TEETH, "pitchRadius": pitch_r, "kind": "return", "sign": -1.0, "width": HTD_BELT_WIDTH_MM + 3.0}
    idler_b = {"name": "SelectorIdler_20T_B", "x": motor_x - wrap_r, "y": back_y - wrap_r, "z": z, "teeth": HTD_DRIVE_TEETH, "pitchRadius": pitch_r, "kind": "return", "sign": -1.0, "width": HTD_BELT_WIDTH_MM + 3.0}
    drive = {"name": "SelectorDrivePulley_20T", "x": motor_x, "y": motor_y, "z": z, "teeth": HTD_DRIVE_TEETH, "pitchRadius": pitch_r, "kind": "drive", "sign": 1.0, "width": HTD_BELT_WIDTH_MM + 3.0}
    segs: list[dict[str, Any]] = [
        {"kind": "arc", "cx": motor_x, "cy": motor_y, "radius": wrap_r, "a0": math.pi, "a1": math.pi * 2.0, "z": z, "wrap": "drive", "pulley": drive["name"]},
        {"kind": "line", "x0": motor_x + wrap_r, "y0": motor_y, "x1": first["x"], "y1": first["y"], "z": z},
    ]
    segs.extend(working_segs)
    segs.append({"kind": "line", "x0": last["x"], "y0": last["y"], "x1": last["x"], "y1": idler_a["y"] - wrap_r, "z": z})
    segs.append({"kind": "arc", "cx": idler_a["x"], "cy": idler_a["y"], "radius": wrap_r, "a0": -math.pi / 2.0, "a1": -math.pi, "z": z, "wrap": "return", "pulley": idler_a["name"]})
    segs.append({"kind": "line", "x0": last["x"] - wrap_r, "y0": idler_a["y"], "x1": idler_b["x"] + wrap_r, "y1": idler_b["y"], "z": z})
    segs.append({"kind": "arc", "cx": idler_b["x"], "cy": idler_b["y"], "radius": wrap_r, "a0": 0.0, "a1": -math.pi / 2.0, "z": z, "wrap": "return", "pulley": idler_b["name"]})
    segs.append({"kind": "line", "x0": idler_b["x"], "y0": idler_b["y"] - wrap_r, "x1": motor_x - wrap_r, "y1": motor_y, "z": z})
    return segs, [drive, idler_a, idler_b]

def _wrap_ranges(segments: list[dict]) -> list[tuple[float, float]]:
    ranges = []
    cursor = 0.0
    for seg in segments:
        if seg["kind"] == "line":
            length = math.hypot(seg["x1"] - seg["x0"], seg["y1"] - seg["y0"])
        else:
            length = abs(seg["a1"] - seg["a0"]) * seg["radius"]
        if seg.get("wrap"):
            ranges.append((cursor, cursor + length))
        cursor += length
    return ranges

def _on_wrap(distance: float, ranges: list[tuple[float, float]]) -> bool:
    for lo, hi in ranges:
        if lo - 2.0 <= distance <= hi + 2.0:
            return True
    return False

# ===== 分区：公开 API =====
def belt_z(cfg) -> float:
    return cfg.base_height + cfg.shell_height + 12.0

def build_snake_path(cfg) -> dict[str, Any]:
    z = belt_z(cfg)
    pitch_r = drive_pitch_radius_mm()
    wrap_r = pitch_r + BELT_BODY_MM * 0.5 + WRAP_CLEAR_MM
    turn_r = (cfg.cell_depth + cfg.cell_gap_y) * 0.5
    order = _serpentine_order(cfg.columns, cfg.layers)
    cells = []
    for index in range(cfg.columns * cfg.layers):
        col = index % cfg.columns
        layer = index // cfg.columns
        cx, cy = _cell_center(cfg, col, layer)
        cells.append({"index": index, "col": col, "layer": layer, "x": cx, "y": cy, "z": z})
    first = cells[order[0]]
    last = cells[order[-1]]
    motor_x = max(28.0, first["x"] - turn_r - wrap_r - MOTOR_EXTRA_MM)
    motor_y = first["y"]
    working_segs, shoes = _working_segments(cells, order, first, turn_r, z)
    closed_segs, pulleys = _closed_segments(cfg, first, last, motor_x, motor_y, pitch_r, wrap_r, working_segs, z, 0.0)
    loop_samples = _add_outward(_decorate(_raw_from_segments(closed_segs)))
    loop_len = loop_samples[-1]["s"] if loop_samples else 0.0
    teeth_n = max(20, int(round(loop_len / HTD_PITCH_MM)))
    delta = teeth_n * HTD_PITCH_MM - loop_len
    if abs(delta) > 0.05:
        closed_segs, pulleys = _closed_segments(cfg, first, last, motor_x, motor_y, pitch_r, wrap_r, working_segs, z, delta * 0.5)
        loop_samples = _add_outward(_decorate(_raw_from_segments(closed_segs)))
        loop_len = loop_samples[-1]["s"] if loop_samples else 0.0
        teeth_n = max(20, int(round(loop_len / HTD_PITCH_MM)))
    working_raw = [(first["x"], first["y"], z)]
    for seg in working_segs:
        if seg["kind"] == "line":
            _add_line(working_raw, seg["x1"], seg["y1"], z)
        else:
            _add_arc(working_raw, seg["cx"], seg["cy"], seg["radius"], seg["a0"], seg["a1"], z)
    working_samples = _decorate(working_raw)
    anchors = {str(order[0]): 0.0}
    for cell_index in order[1:]:
        cell = cells[cell_index]
        best = min(working_samples, key=lambda p: math.hypot(p["x"] - cell["x"], p["y"] - cell["y"]))
        anchors[str(cell_index)] = best["s"]
    drive = pulleys[0]
    return {
        "mode": "snake",
        "kind": "snake-htd-closed",
        "closed": True,
        "z": z,
        "drive": {
            "x": drive["x"],
            "y": drive["y"],
            "z": drive["z"],
            "teeth": HTD_DRIVE_TEETH,
            "pitchMm": HTD_PITCH_MM,
            "pitchRadius": pitch_r,
            "beltWidth": HTD_BELT_WIDTH_MM,
            "beltThickness": HTD_BELT_THICKNESS_MM,
            "rpmAtDefault": pulley_rpm(DEFAULT_SELECTOR_SPEED_MM_S),
            "name": drive["name"],
            "width": drive["width"],
            "sign": drive["sign"],
        },
        "order": order,
        "cells": cells,
        "anchors": anchors,
        "pulleys": pulleys,
        "shoes": shoes,
        "idlers": [item for item in pulleys if item["kind"] == "return"],
        "working": working_samples,
        "loop": loop_samples,
        "segments": closed_segs,
        "wrapRanges": _wrap_ranges(closed_segs),
        "workingLength": working_samples[-1]["s"] if working_samples else 0.0,
        "loopLength": loop_len,
        "beltTeeth": teeth_n,
        "turnRadius": turn_r,
    }

def selector_timeline(path: dict[str, Any], target_index: int, speed_mm_s: float) -> dict[str, Any]:
    anchors = path.get("anchors") or {}
    target_s = float(anchors.get(str(target_index), 0.0))
    travel = max(0.8, target_s / max(1.0, speed_mm_s))
    durations = [travel, PHASE_HOLD_S[1], PHASE_HOLD_S[2], PHASE_HOLD_S[3], travel, PHASE_HOLD_S[5]]
    return {
        "durations": durations,
        "total": sum(durations),
        "targetDistance": target_s,
        "speedMmS": speed_mm_s,
        "rpm": pulley_rpm(speed_mm_s),
    }

def visible_tooth_samples(path: dict[str, Any], distance: float, pool: int = 36) -> list[dict[str, float]]:
    loop = path.get("loop") or []
    length = float(path.get("loopLength") or 0.0)
    teeth_n = int(path.get("beltTeeth") or 0)
    ranges = path.get("wrapRanges") or []
    if not loop or length <= 0 or teeth_n < 1:
        return []
    pitch = length / teeth_n
    picked = []
    for index in range(teeth_n):
        station = (index * pitch + distance) % length
        if _on_wrap(station, ranges):
            sample = dict(_point_at(loop, station))
            sample["station"] = station
            picked.append(sample)
        if len(picked) >= pool:
            break
    return picked

def selector_pose(path: dict[str, Any], target_index: int, elapsed: float, speed_mm_s: float) -> dict[str, Any]:
    timeline = selector_timeline(path, target_index, speed_mm_s)
    cycle = elapsed % timeline["total"] if timeline["total"] else 0.0
    accumulated = 0.0
    phase_index = 5
    progress = 1.0
    for index, duration in enumerate(timeline["durations"]):
        if cycle <= accumulated + duration or index == len(timeline["durations"]) - 1:
            phase_index = index
            progress = 1.0 if duration == 0 else _clamp((cycle - accumulated) / duration, 0.0, 1.0)
            break
        accumulated += duration
    eased = _ease(progress)
    target_s = timeline["targetDistance"]
    if phase_index == 0:
        distance = target_s * eased
    elif phase_index in (1, 2, 3):
        distance = target_s
    elif phase_index == 4:
        distance = target_s * (1.0 - eased)
    else:
        distance = 0.0
    position = _point_at(path["working"], distance)
    drive_r = float(path.get("drive", {}).get("pitchRadius") or drive_pitch_radius_mm())
    spools = []
    for pulley in path.get("pulleys") or [path.get("drive")]:
        if not pulley:
            continue
        spools.append({
            "name": pulley.get("name") or "SelectorDrivePulley_20T",
            "x": pulley["x"],
            "y": pulley["y"],
            "z": pulley["z"],
            "width": pulley.get("width") or (HTD_BELT_WIDTH_MM + 3.0),
            "deg": no_slip_deg(distance, pulley.get("pitchRadius") or drive_r, pulley.get("sign") or 1.0),
        })
    return {
        "phaseIndex": phase_index,
        "phaseLabel": PHASE_LABELS[phase_index],
        "progress": progress,
        "cycle": cycle,
        "position": position,
        "distance": distance,
        "engaged": phase_index in (1, 2) or (phase_index == 3 and progress < 0.5),
        "busOn": phase_index == 2,
        "selecting": phase_index in (0, 4),
        "pulleyDeg": no_slip_deg(distance, drive_r, 1.0),
        "spools": spools,
        "timeline": timeline,
        "targetIndex": target_index,
        "rollerDeg": no_slip_deg(distance, 4.0, 1.0),
    }

def loop_pose(path: dict[str, Any], elapsed: float, speed_mm_s: float) -> dict[str, Any]:
    loop = path.get("loop") or path.get("working") or []
    length = float(path.get("loopLength") or (loop[-1]["s"] if loop else 0.0))
    speed = max(1.0, float(speed_mm_s))
    distance = (elapsed * speed) % length if length > 0 else 0.0
    position = _point_at(loop, distance)
    drive_r = float(path.get("drive", {}).get("pitchRadius") or drive_pitch_radius_mm())
    spools = []
    for pulley in path.get("pulleys") or [path.get("drive")]:
        if not pulley:
            continue
        spools.append({
            "name": pulley.get("name") or "SelectorDrivePulley_20T",
            "x": pulley["x"],
            "y": pulley["y"],
            "z": pulley["z"],
            "width": pulley.get("width") or (HTD_BELT_WIDTH_MM + 3.0),
            "deg": no_slip_deg(distance, pulley.get("pitchRadius") or drive_r, pulley.get("sign") or 1.0),
        })
    rpm = pulley_rpm(speed)
    return {
        "phaseIndex": 0,
        "phaseLabel": "LOOP / 循环",
        "progress": 0.0 if length <= 0 else distance / length,
        "cycle": elapsed,
        "position": position,
        "distance": distance,
        "engaged": False,
        "busOn": False,
        "selecting": True,
        "pulleyDeg": no_slip_deg(distance, drive_r, 1.0),
        "spools": spools,
        "timeline": {"durations": [length / speed if speed else 1.0], "total": length / speed if speed else 1.0, "targetDistance": length, "speedMmS": speed, "rpm": rpm},
        "targetIndex": int(path.get("targetIndex") or 0),
        "rollerDeg": 0.0,
        "loopLength": length,
    }

# ===== 分区：业务逻辑 =====
def motion_profile_from_path(path: dict[str, Any], steps: int) -> dict[str, Any]:
    samples = []
    length = path.get("workingLength") or 0.0
    count = max(8, int(steps))
    for index in range(count + 1):
        t = index / max(1, count)
        point = _point_at(path["working"], length * t)
        samples.append({"t": round(t, 6), "x": point["x"], "y": point["y"], "z": point["z"], "s": point["s"]})
    return {
        "mode": "snake",
        "kind": "snake-htd-closed",
        "samples": samples,
        "steps": count,
        "closed": True,
        "workingLength": length,
        "loopLength": path.get("loopLength", 0.0),
        "bounds": {
            "xMin": min((p["x"] for p in samples), default=0.0),
            "xMax": max((p["x"] for p in samples), default=0.0),
            "yMin": min((p["y"] for p in samples), default=0.0),
            "yMax": max((p["y"] for p in samples), default=0.0),
            "zMin": min((p["z"] for p in samples), default=0.0),
            "zMax": max((p["z"] for p in samples), default=0.0),
        },
    }

# ===== 分区：方法/工具 =====
def yaw_deg(tx: float, ty: float) -> float:
    return math.degrees(math.atan2(ty, tx))
