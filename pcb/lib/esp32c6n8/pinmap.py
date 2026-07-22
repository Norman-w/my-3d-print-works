# ===== 分区：导入/依赖 =====
"""ESP32-C6-N8 / SGFK 半孔真理源（校本）。

依据：docs/ESP32C6N8/pinout-and-dimensions.md + 商家商品图（与乐鑫 WROOM-1 一致）。
改脚位只改本模块，再跑：

    python3 pcb/scripts/generate_sgfk_esp32c6n8_mod.py
    python3 pcb/scripts/validate_esp32c6n8_pinmap.py
"""

from __future__ import annotations

# ===== 分区：常量/配置 =====

BODY_MM = (25.5, 18.0)  # 长(含天线端) × 宽(两长边间距)
PITCH_MM = 1.27
END_INSET_MM = 1.5
ANTENNA_OVERHANG_MM = 5.99  # 天线端额外占位 → 首孔距板端 ≈ 7.5mm
DRILL_MM = 0.85
PAD_SIZE_MM = 1.12

# 顶视 = 元件面朝上（与商品图 / 乐鑫 datasheet top view 一致）。
# 天线在图纸上方时：左列 pin1–14、右列 pin15–28。
# 旋到板坐标天线 −X 后：pin1–14 在 +Y（拍柄），pin15–28 在 −Y（拍头/IMU）。
# 旧版曾把两长边写成底视（无元件面看丝印），导致 pad25↔IO4；勿再镜像。
ORIENTATION = {
    "view": "top_component_side",
    "antenna": "-X",
    "pin1_to_14_edge": "+Y",  # 拍柄：GND/3V3/EN/IO4…
    "pin15_to_28_edge": "-Y",  # 拍头/IMU：IO9/BOOT…IO2/UART0/GND
    "note": (
        "顶视、天线 −X：拍柄(+Y)=pin1–14；拍头/IMU(−Y)=pin15–28。"
        "勿按模块背面丝印直接抄坐标（会上下排对调）。"
    ),
}

# pad → 模块丝印 / 芯片功能
PADS: dict[int, dict[str, str]] = {
    1: {"silk": "GND", "function": "GND"},
    2: {"silk": "3V3", "function": "3V3"},
    3: {"silk": "EN", "function": "CHIP_EN"},
    4: {"silk": "IO4", "function": "GPIO4"},
    5: {"silk": "IO5", "function": "GPIO5"},
    6: {"silk": "IO6", "function": "GPIO6"},
    7: {"silk": "IO7", "function": "GPIO7"},
    8: {"silk": "IO0", "function": "GPIO0"},
    9: {"silk": "IO1", "function": "GPIO1"},
    10: {"silk": "IO8", "function": "GPIO8"},
    11: {"silk": "IO10", "function": "GPIO10"},
    12: {"silk": "IO11", "function": "GPIO11"},
    13: {"silk": "IO12", "function": "USB_D-"},
    14: {"silk": "IO13", "function": "USB_D+"},
    15: {"silk": "IO9", "function": "GPIO9_BOOT"},
    16: {"silk": "IO18", "function": "GPIO18"},
    17: {"silk": "IO19", "function": "GPIO19"},
    18: {"silk": "IO20", "function": "GPIO20"},
    19: {"silk": "IO21", "function": "GPIO21"},
    20: {"silk": "IO22", "function": "GPIO22"},
    21: {"silk": "IO23", "function": "GPIO23"},
    22: {"silk": "NC", "function": "NC"},
    23: {"silk": "IO15", "function": "GPIO15"},
    24: {"silk": "RXD0", "function": "U0RXD"},
    25: {"silk": "TXD0", "function": "U0TXD"},
    26: {"silk": "IO3", "function": "GPIO3"},
    27: {"silk": "IO2", "function": "GPIO2"},
    28: {"silk": "GND", "function": "GND"},
}

# footprint pad 号 → main.ato 组件 pin 名（仅已接线脚）
PROJECT_BINDINGS: dict[int, str] = {
    1: "GND_1",
    2: "VCC_3V3",
    3: "EN",
    6: "GPIO6_PZT_BL",
    7: "GPIO7_PZT_BR",
    10: "GPIO8_LED_DATA",
    11: "PWR_LATCH",
    13: "USB_DN",
    14: "USB_DP",
    15: "GPIO9_BOOT",
    16: "GPIO18_USER_BTN",
    20: "GPIO22_IMU_RX",
    21: "GPIO23_IMU_TX",
    24: "UART_RX",
    25: "UART_TX",
    26: "GPIO3_PZT_TR",
    27: "GPIO2_PZT_TL",
    28: "GND_28",
}

# 固件 GPIO 号（校验 config.h）
FIRMWARE_GPIO: dict[str, int] = {
    "PIEZO_PIN_1": 2,
    "PIEZO_PIN_2": 3,
    "PIEZO_PIN_3": 6,
    "PIEZO_PIN_4": 7,
    "IMU_UART_TX": 23,  # pad 21 IO23 → IMU RXD（面对面左，平行交叉）
    "IMU_UART_RX": 22,  # pad 20 IO22 ← IMU TXD（面对面右）
    "LED_PIN": 8,
    "PWR_LATCH_GPIO": 10,
    "USER_BTN_GPIO": 18,
    "BOOT_BTN_GPIO": 9,
}

# ===== 分区：公开 API =====


def drill_mm() -> float:
    return DRILL_MM


def pad_xy(pad: int) -> tuple[float, float]:
    """返回 footprint 局部坐标 (x, y)。

    顶视（元件面）、天线 −X：pad1–14 在 +Y；pad15–28 在 −Y。
    """
    if pad < 1 or pad > 28:
        raise ValueError(f"pad out of range: {pad}")
    length, width = BODY_MM
    y_edge = width / 2 + 0.20  # 半孔中心略外探
    # 非天线端 (+X) 内缩 END_INSET；天线端由 overhang+inset 决定首孔
    x_first = -length / 2 + ANTENNA_OVERHANG_MM + END_INSET_MM
    if pad <= 14:
        return (round(x_first + (pad - 1) * PITCH_MM, 3), round(+y_edge, 2))
    # 15 在 +X 远端，向天线端递增到 28
    idx = pad - 15  # 0..13
    x_far = length / 2 - END_INSET_MM
    return (round(x_far - idx * PITCH_MM, 3), round(-y_edge, 2))
