#!/usr/bin/env python3
"""从 OpenSCAD 的中心离合参数回显生成唯一机械契约。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

# ===== 分区：常量/配置 =====
MARKER = "CENTER_CLUTCH_CONTRACT_DYNAMIC"
REQUIRED = {
    "axis",
    "role",
    "openGapMm",
    "dogInsertionMm",
    "strokeMm",
    "pocketDepthMm",
    "bottomClearanceMm",
    "magnetNonContactClearanceMm",
    "femaleMagnetProjectionMm",
    "magnetNominalDiameterMm",
    "actuation",
    "engageOnlyWhenStopped",
    "releaseBeforeReturn",
}
FLOAT_KEYS = {
    "axisXMm",
    "axisZMm",
    "inputBaseYMm",
    "outputBaseYMm",
    "openGapMm",
    "dogInsertionMm",
    "strokeMm",
    "pocketDepthMm",
    "bottomClearanceMm",
    "magnetNonContactClearanceMm",
    "femaleMagnetProjectionMm",
    "magnetNominalDiameterMm",
    "gearCenterDistanceMm",
    "longPitchRadiusMm",
    "inputPitchRadiusMm",
    "gearMeshClearanceMm",
    "longTipRadiusMm",
    "inputTipRadiusMm",
    "beltEnvelopeRadiusMm",
    "beltGuideRadiusMm",
    "motherOuterRadiusMm",
    "selectorTriggerSpacingMm",
    "guideRunningClearanceMm",
    "railY0Mm",
    "railY1Mm",
    "openStopY0Mm",
    "openStopY1Mm",
    "engagedStopY0Mm",
    "engagedStopY1Mm",
    "openTabY0Mm",
    "openTabY1Mm",
    "engagedTabY0Mm",
    "engagedTabY1Mm",
    "bearingSeatDiameterMm",
    "bearingSeatDepthMm",
    "bearingBackShoulderMm",
    "shaftDiameterMm",
    "shaftCollarOdMm",
    "shaftCollarBoreMm",
}
INT_KEYS = {
    "version",
    "bearingCount",
    "shaftCount",
    "matingMagnetCount",
    "selectorMagnetCount",
    "totalMagnetCount",
    "centerCol",
    "centerRow",
}
BOOL_KEYS = {"engageOnlyWhenStopped", "releaseBeforeReturn"}

# ===== 分区：私有成员 =====
def parse_echo(output: str) -> dict[str, str]:
    for line in output.splitlines():
        if MARKER not in line:
            continue
        tokens = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        if not tokens or tokens[0] != MARKER:
            continue
        values: dict[str, str] = {}
        for token in tokens[1:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            values[key] = value
        missing = REQUIRED - values.keys()
        if missing:
            raise RuntimeError(
                f"中心离合契约缺少字段: {', '.join(sorted(missing))}"
            )
        return values
    raise RuntimeError("OpenSCAD 输出中没有 CENTER_CLUTCH_CONTRACT 回显")


def coerce(values: dict[str, str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values.items():
        if key in FLOAT_KEYS:
            result[key] = float(value)
        elif key in INT_KEYS:
            result[key] = int(float(value))
        elif key in BOOL_KEYS:
            if value not in {"true", "false"}:
                raise RuntimeError(f"契约布尔字段无效: {key}={value}")
            result[key] = value == "true"
        else:
            result[key] = value
    return result


def validate_contract(contract: dict[str, object]) -> None:
    if contract.get("axis") != "+Y" or contract.get("role") != "input/output":
        raise RuntimeError("中心离合契约轴向/角色不匹配")
    if contract.get("actuation") != "permanent-magnet":
        raise RuntimeError("中心离合契约不是纯永磁动作")
    if contract.get("engageOnlyWhenStopped") is not True:
        raise RuntimeError("中心离合必须停稳后接合")
    if contract.get("releaseBeforeReturn") is not True:
        raise RuntimeError("中心离合必须释放后返回")

    def number(key: str) -> float:
        value = contract.get(key)
        if not isinstance(value, (int, float)):
            raise RuntimeError(f"中心离合契约缺少数值字段: {key}")
        return float(value)

    frozen = {
        "openGapMm": 0.60,
        "dogInsertionMm": 2.40,
        "strokeMm": 3.00,
        "pocketDepthMm": 3.25,
        "bottomClearanceMm": 0.85,
        "magnetNonContactClearanceMm": 0.40,
        "femaleMagnetProjectionMm": 0.45,
        "magnetNominalDiameterMm": 2.00,
        "selectorTriggerSpacingMm": 12.00,
        "guideRunningClearanceMm": 0.30,
        "bearingSeatDiameterMm": 6.10,
        "bearingSeatDepthMm": 2.60,
        "bearingBackShoulderMm": 0.60,
    }
    for key, expected in frozen.items():
        if abs(number(key) - expected) > 0.001:
            raise RuntimeError(
                f"中心离合冻结值错误: {key}={number(key)}，期望 {expected}"
            )
    if abs(number("strokeMm")
            - number("openGapMm")
            - number("dogInsertionMm")) > 0.001:
        raise RuntimeError("中心离合行程必须等于开位间隙加有效插入")
    if abs(number("pocketDepthMm")
            - number("dogInsertionMm")
            - number("bottomClearanceMm")) > 0.001:
        raise RuntimeError("中心母槽深度必须等于插入量加槽底余量")
    if abs(number("bottomClearanceMm")
            - number("femaleMagnetProjectionMm")
            - number("magnetNonContactClearanceMm")) > 0.001:
        raise RuntimeError("中心磁铁非接触余量推导失败")
    if number("bearingSeatDepthMm") < number("bearingBackShoulderMm") + 2.0:
        raise RuntimeError("轴承座深度不足以容纳 3x6x2 轴承和后肩")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# ===== 分区：公开 API =====
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True, type=Path)
    parser.add_argument("--scad", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--motion", type=Path)
    args = parser.parse_args()
    scad_path = args.scad.resolve()
    output_path = args.output.resolve()
    motion_path = args.motion.resolve() if args.motion else None

    with tempfile.NamedTemporaryFile(suffix=".stl") as temp:
        command = [
            str(args.openscad),
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            'CLUTCH_PART="contract"',
            "-o",
            temp.name,
            str(scad_path),
        ]
        completed = subprocess.run(
            command,
            cwd=scad_path.parent,
            capture_output=True,
            text=True,
            check=False,
        )
    output = f"{completed.stdout}\n{completed.stderr}"
    try:
        # OpenSCAD returns 1 for an intentionally empty top-level object on
        # some releases. The contract marker is the success criterion here;
        # a non-empty diagnostic output without the marker is still a failure.
        contract = coerce(parse_echo(output))
        validate_contract(contract)
    except RuntimeError:
        if completed.returncode != 0:
            raise RuntimeError(
                f"OpenSCAD 契约模式失败（{completed.returncode}）:\n{output[-4000:]}"
            ) from None
        raise
    contract["source"] = "cad/openscad/parts/ch1_03c_gt2_clutch_pair_params.scad"
    contract["geometrySource"] = "cad/openscad/enclosure/cabinet_clutch.scad"
    write_json(output_path, {"centerClutch": contract})

    if motion_path:
        motion = json.loads(motion_path.read_text(encoding="utf-8"))
        motion["centerClutch"] = contract
        write_json(motion_path, motion)

    print(
        "centerClutch contract: "
        f"gap={contract['openGapMm']} insertion={contract['dogInsertionMm']} "
        f"stroke={contract['strokeMm']} bottom={contract['bottomClearanceMm']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
