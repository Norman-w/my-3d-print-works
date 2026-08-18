"""ESP32-S3-WROOM-1-N16R8 C4 pin-map truth source.

The package coordinates and pin numbers follow Espressif's
ESP32-S3-WROOM-1/1U datasheet v1.8, top view.  SmartPaddle rotates the module
90 degrees clockwise so that the PCB antenna points toward board -X.  The
host PCB uses plated half-hole landing pads around the module cutout, as the
C3 embedded-module assembly did.

GPIO35..37 are deliberately unused: on the selected N16R8 octal-PSRAM
variant they are consumed by the in-package memory interface.
"""

from __future__ import annotations

BODY_MM = (25.5, 18.0)  # rotated: antenna-axis length x module width
PITCH_MM = 1.27
DRILL_MM = 0.60
PAD_SIZE_MM = 1.00

ORIENTATION = {
    "view": "top_component_side",
    "antenna": "-X",
    "pin1_to_14_edge": "+Y",
    "pin15_to_26_edge": "+X",
    "pin27_to_40_edge": "-Y",
}

# pad -> module marking / chip function (Espressif datasheet table 3-1)
PADS: dict[int, dict[str, str]] = {
    1: {"silk": "GND", "function": "GND"},
    2: {"silk": "3V3", "function": "3V3"},
    3: {"silk": "EN", "function": "CHIP_PU"},
    4: {"silk": "IO4", "function": "GPIO4/ADC1_CH3"},
    5: {"silk": "IO5", "function": "GPIO5/ADC1_CH4"},
    6: {"silk": "IO6", "function": "GPIO6"},
    7: {"silk": "IO7", "function": "GPIO7"},
    8: {"silk": "IO15", "function": "GPIO15"},
    9: {"silk": "IO16", "function": "GPIO16"},
    10: {"silk": "IO17", "function": "GPIO17"},
    11: {"silk": "IO18", "function": "GPIO18"},
    12: {"silk": "IO8", "function": "GPIO8/ADC1_CH7"},
    13: {"silk": "IO19", "function": "GPIO19/USB_D-"},
    14: {"silk": "IO20", "function": "GPIO20/USB_D+"},
    15: {"silk": "IO3", "function": "GPIO3/STRAP"},
    16: {"silk": "IO46", "function": "GPIO46/STRAP"},
    17: {"silk": "IO9", "function": "GPIO9/ADC1_CH8"},
    18: {"silk": "IO10", "function": "GPIO10/ADC1_CH9"},
    19: {"silk": "IO11", "function": "GPIO11"},
    20: {"silk": "IO12", "function": "GPIO12"},
    21: {"silk": "IO13", "function": "GPIO13"},
    22: {"silk": "IO14", "function": "GPIO14"},
    23: {"silk": "IO21", "function": "GPIO21"},
    24: {"silk": "IO47", "function": "GPIO47"},
    25: {"silk": "IO48", "function": "GPIO48"},
    26: {"silk": "IO45", "function": "GPIO45/STRAP"},
    27: {"silk": "IO0", "function": "GPIO0/BOOT_STRAP"},
    28: {"silk": "IO35", "function": "GPIO35/OPI_PSRAM"},
    29: {"silk": "IO36", "function": "GPIO36/OPI_PSRAM"},
    30: {"silk": "IO37", "function": "GPIO37/OPI_PSRAM"},
    31: {"silk": "IO38", "function": "GPIO38"},
    32: {"silk": "IO39", "function": "GPIO39/JTAG"},
    33: {"silk": "IO40", "function": "GPIO40/JTAG"},
    34: {"silk": "IO41", "function": "GPIO41/JTAG"},
    35: {"silk": "IO42", "function": "GPIO42/JTAG"},
    36: {"silk": "RXD0", "function": "GPIO44/U0RXD"},
    37: {"silk": "TXD0", "function": "GPIO43/U0TXD"},
    38: {"silk": "IO2", "function": "GPIO2/ADC1_CH1"},
    39: {"silk": "IO1", "function": "GPIO1/ADC1_CH0"},
    40: {"silk": "GND", "function": "GND"},
}

# Only electrically used perimeter pads are exposed in main.ato.  Pad 41 is
# the underside thermal/ground pad and is not reachable in the embedded
# cutout assembly; pads 1 and 40 are therefore both bonded to the ground net.
PROJECT_BINDINGS: dict[int, str] = {
    1: "GND_1",
    2: "VCC_3V3",
    3: "EN",
    4: "GPIO4_PZT_ADC_BL",
    6: "GPIO6_PZT_EDGE_BL",
    7: "GPIO7_PZT_EDGE_BR",
    # TLV9034 channel 1 is TR and channel 2 is TL so the top CMP_IN traces
    # approach pins 5/7 without crossing.
    8: "GPIO15_PZT_EDGE_TR",
    9: "GPIO16_PZT_EDGE_TL",
    10: "GPIO17_I2C_SDA",
    11: "GPIO18_I2C_SCL",
    # BR ADC moves right to avoid the long return across the MCU edge.
    12: "GPIO8_PZT_ADC_BR",
    13: "USB_DN",
    14: "USB_DP",
    17: "GPIO9_BAT_SENSE",
    23: "GPIO21_LED_DATA",
    24: "GPIO47_PWR_LATCH",
    25: "GPIO48_USER_BTN",
    27: "GPIO0_BOOT",
    # Swap the MCU UART roles so the two short IMU links do not cross.
    33: "GPIO40_IMU_RX",
    34: "GPIO41_IMU_TX",
    36: "UART_RX",
    37: "UART_TX",
    38: "GPIO2_PZT_ADC_TR",
    39: "GPIO1_PZT_ADC_TL",
    40: "GND_40",
}

FIRMWARE_GPIO: dict[str, int] = {
    # Firmware channel order remains TL/TR/BL/BR.
    "PIEZO_PIN_1": 16,
    "PIEZO_PIN_2": 15,
    "PIEZO_PIN_3": 6,
    "PIEZO_PIN_4": 7,
    "PZT_ADC_PIN_1": 1,
    "PZT_ADC_PIN_2": 2,
    "PZT_ADC_PIN_3": 4,
    "PZT_ADC_PIN_4": 8,
    "PZT_I2C_SDA": 17,
    "PZT_I2C_SCL": 18,
    "IMU_UART_TX": 41,
    "IMU_UART_RX": 40,
    "LED_PIN": 21,
    "BAT_SENSE_GPIO": 9,
    "PWR_LATCH_GPIO": 47,
    "USER_BTN_GPIO": 48,
    "BOOT_BTN_GPIO": 0,
}


def drill_mm() -> float:
    return DRILL_MM


def pad_xy(pad: int) -> tuple[float, float]:
    """Return host half-hole center after clockwise rotation.

    Positions along each row are the official module land centers.  The
    normal coordinate is moved 0.45 mm outward so each plated host hole
    straddles the generated body cutout and overlaps the module land.
    """
    if pad < 1 or pad > 40:
        raise ValueError(f"pad out of range: {pad}")
    if pad <= 14:
        return (round(-5.26 + (pad - 1) * PITCH_MM, 3), 9.20)
    if pad <= 26:
        return (13.00, round(6.985 - (pad - 15) * PITCH_MM, 3))
    return (round(11.25 - (pad - 27) * PITCH_MM, 3), -9.20)
