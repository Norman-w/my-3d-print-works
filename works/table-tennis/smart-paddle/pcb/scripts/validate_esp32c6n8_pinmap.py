#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""校验 main.ato / step3 映射 / config.h / .kicad_mod 与校本 pinmap 一致。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb"))

from lib.esp32c6n8.pinmap import (  # noqa: E402
    FIRMWARE_GPIO,
    ORIENTATION,
    PROJECT_BINDINGS,
    pad_xy,
)

# ===== 分区：常量/配置 =====

ATO = ROOT / "pcb" / "main.ato"
MOD = (
    ROOT
    / "pcb"
    / "layouts"
    / "lib"
    / "footprints.pretty"
    / "SGFK_ESP32-C6-N8_CUTOUT.kicad_mod"
)
CONFIG_H = ROOT / "firmware" / "main" / "config.h"
STEP3 = ROOT / "pcb" / "scripts" / "step3_import_netlist.py"

# ===== 分区：方法/工具 =====


def check_ato() -> list[str]:
    errs: list[str] = []
    text = ATO.read_text(encoding="utf-8")
    # 抽取 SGFK 组件块内的 `NAME ~ pin N`
    m = re.search(
        r"component SGFK_ESP32C6N8_Cutout:.*?footprint\s*=",
        text,
        re.S,
    )
    if not m:
        return ["main.ato: 找不到 SGFK_ESP32C6N8_Cutout 组件"]
    block = m.group(0)
    found = {
        name: int(num)
        for name, num in re.findall(r"(\w+)\s*~\s*pin\s+(\d+)", block)
    }
    for pad, name in PROJECT_BINDINGS.items():
        if found.get(name) != pad:
            errs.append(
                f"main.ato: {name} 应为 pin {pad}，实际 {found.get(name)!r}"
            )
    # 注释朝向：顶视 pin1–14 = 拍柄(+Y)；pin15–28 = 拍头/IMU(−Y)
    if "pin1–14 在 −Y" in block or "pin1-14 在 −Y" in block:
        errs.append(
            "main.ato: 仍写 pin1–14 在 −Y（那是底视）；顶视应为 +Y 拍柄"
        )
    if "拍柄" not in block or ("拍头" not in block and "IMU" not in block):
        errs.append("main.ato: 组件注释未标明顶视两长边（拍柄 / 拍头·IMU）")
    return errs


def check_orientation() -> list[str]:
    errs: list[str] = []
    if ORIENTATION.get("view") != "top_component_side":
        errs.append("pinmap: ORIENTATION.view 必须为 top_component_side")
    if pad_xy(1)[1] <= 0 or pad_xy(28)[1] >= 0:
        errs.append(
            f"pinmap: 顶视应为 pad1 y>0、pad28 y<0；实际 "
            f"pad1={pad_xy(1)} pad28={pad_xy(28)}"
        )
    return errs


def check_mod() -> list[str]:
    errs: list[str] = []
    if not MOD.is_file():
        return [f"缺少 {MOD}"]
    text = MOD.read_text(encoding="utf-8")
    pads = {
        int(n): (float(x), float(y))
        for n, x, y in re.findall(
            r'\(pad "(\d+)"[^\n]*\(at ([-\d.]+) ([-\d.]+)', text
        )
    }
    if len(pads) != 28:
        errs.append(f".kicad_mod: pad 数 {len(pads)} != 28")
    for n in range(1, 29):
        if n not in pads:
            errs.append(f".kicad_mod: 缺 pad {n}")
            continue
        exp = pad_xy(n)
        got = pads[n]
        if abs(got[0] - exp[0]) > 0.02 or abs(got[1] - exp[1]) > 0.02:
            errs.append(f".kicad_mod: pad {n}={got} 期望 {exp}")
    if "generate_sgfk_esp32c6n8_mod.py" not in text and "pinmap" not in text:
        errs.append(".kicad_mod: 非校本生成器产物（请重新 generate）")
    return errs


def check_config_h() -> list[str]:
    errs: list[str] = []
    text = CONFIG_H.read_text(encoding="utf-8")
    for name, gpio in FIRMWARE_GPIO.items():
        m = re.search(rf"#define\s+{name}\s+GPIO_NUM_(\d+)", text)
        if not m:
            # IMU_UART_TX 等
            m = re.search(rf"#define\s+{name}\s+GPIO_NUM_(\d+)", text)
        if not m:
            errs.append(f"config.h: 缺少 {name}")
            continue
        if int(m.group(1)) != gpio:
            errs.append(
                f"config.h: {name}=GPIO{m.group(1)} 校本期望 GPIO{gpio}"
            )
    return errs


def check_step3_imports_pinmap() -> list[str]:
    text = STEP3.read_text(encoding="utf-8")
    if "esp32c6n8" not in text and "PROJECT_BINDINGS" not in text:
        return ["step3_import_netlist.py: 未从校本 pinmap 导入 MCU 脚名"]
    return []


# ===== 分区：公开 API =====


def main() -> int:
    errs: list[str] = []
    errs.extend(check_orientation())
    errs.extend(check_ato())
    errs.extend(check_mod())
    errs.extend(check_config_h())
    errs.extend(check_step3_imports_pinmap())
    if errs:
        print("ESP32-C6-N8 pinmap 校验失败：")
        for e in errs:
            print(f"  ✗ {e}")
        return 1
    print("✓ ESP32-C6-N8 pinmap 与 ato / mod / config.h / step3 一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
