#!/usr/bin/env python3
"""Validate the non-negotiable ESP32 control topology against current CAD parameters."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/control/esp32-control-contract.json"
SCAD_PATH = ROOT / "cad/openscad/enclosure/cabinet_params.scad"


def read_scad_number(source: str, name: str) -> float:
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*;", source, re.MULTILINE)
    if not match:
        raise ValueError(f"找不到 SCAD 参数: {name}")
    return float(match.group(1))


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    scad = SCAD_PATH.read_text(encoding="utf-8")
    grid = contract["stationGrid"]
    expected = {
        "columns": read_scad_number(scad, "N_COL"),
        "rows": read_scad_number(scad, "N_ROW"),
        "serviceBayWidthMm": read_scad_number(scad, "SERVICE_W"),
    }
    actual = {key: float(grid[key]) for key in expected}
    if actual != expected:
        raise SystemExit(f"控制契约与 SCAD 不一致: contract={actual}, scad={expected}")
    if int(grid["drawerStationCount"]) != int(grid["columns"] * grid["rows"]):
        raise SystemExit("drawerStationCount 必须等于 columns × rows")
    if int(grid["drawerStationCount"]) != 15:
        raise SystemExit("当前控制契约必须保持 15 个抽屉站点")
    if contract["controller"]["firmwarePresent"]:
        raise SystemExit("固件尚未进入本仓库，firmwarePresent 不能伪报为 true")
    if contract["clutch"]["drawerStationCount"] != grid["drawerStationCount"]:
        raise SystemExit("离合站点数量与抽屉站点数量不一致")
    required_states = {"BOOT", "SELF_TEST", "HOME_SELECTOR", "VERIFY_CLUTCH", "FAULT"}
    if not required_states.issubset(set(contract["states"])):
        raise SystemExit("控制状态机缺少安全关键状态")
    print("control contract OK: 5×3 / 15 stations / firmware boundary explicit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
