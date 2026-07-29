#!/usr/bin/env python3
"""Cross-check the C4 S3 pin map across ato, footprint, firmware and importer."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb"))

from lib.esp32s3wroom1.pinmap import (  # noqa: E402
    FIRMWARE_GPIO,
    ORIENTATION,
    PROJECT_BINDINGS,
    pad_xy,
)

ATO = ROOT / "pcb" / "main.ato"
MOD = ROOT / "pcb" / "layouts" / "lib" / "footprints.pretty" / "ESP32-S3-WROOM-1_CUTOUT.kicad_mod"
CONFIG_H = ROOT / "firmware" / "main" / "config.h"
STATUS_LED_CPP = ROOT / "firmware" / "main" / "status_led.cpp"
MAIN_CPP = ROOT / "firmware" / "main" / "main.cpp"
PZT_FRONTEND_CPP = ROOT / "firmware" / "main" / "pzt_frontend.cpp"
PIEZO_CAPTURE_CPP = ROOT / "firmware" / "main" / "piezo_capture.cpp"
COMPONENT_CMAKE = ROOT / "firmware" / "main" / "CMakeLists.txt"
SDKCONFIG_DEFAULTS = ROOT / "firmware" / "sdkconfig.defaults"
SDKCONFIG = ROOT / "firmware" / "sdkconfig"
PARTITIONS = ROOT / "firmware" / "partitions.csv"
STEP3 = ROOT / "pcb" / "scripts" / "step3_import_netlist.py"

REQUIRED_S3_CONFIG = {
    'CONFIG_IDF_TARGET="esp32s3"',
    "CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y",
    'CONFIG_ESPTOOLPY_FLASHSIZE="16MB"',
    "CONFIG_ESPTOOLPY_FLASHMODE_QIO=y",
    "CONFIG_ESPTOOLPY_FLASHFREQ_80M=y",
    "CONFIG_SPIRAM=y",
    "CONFIG_SPIRAM_MODE_OCT=y",
    "CONFIG_SPIRAM_SPEED_80M=y",
    "CONFIG_SPIRAM_BOOT_INIT=y",
    "CONFIG_SPIRAM_USE_MALLOC=y",
    "CONFIG_PARTITION_TABLE_CUSTOM=y",
    'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"',
}
REQUIRED_GENERATED_CONFIG = {
    # ESP-IDF 5.5 intentionally flashes the QIO bootloader in DIO mode; the
    # second-stage bootloader switches the module to quad mode at startup.
    'CONFIG_ESPTOOLPY_FLASHMODE="dio"',
    'CONFIG_ESPTOOLPY_FLASHFREQ="80m"',
}

EXPECTED_PARTITIONS = {
    "nvs": (0x9000, 0x6000),
    "phy_init": (0xF000, 0x1000),
    "factory": (0x10000, 0x200000),
    "ota_0": (0x210000, 0x400000),
    "ota_1": (0x610000, 0x400000),
    "storage": (0xA10000, 0x5F0000),
}


def check_ato() -> list[str]:
    text = ATO.read_text(encoding="utf-8")
    match = re.search(
        r"component ESP32S3WROOM1_Cutout:.*?footprint\s*=", text, re.S
    )
    if not match:
        return ["main.ato: missing ESP32S3WROOM1_Cutout"]
    found = {
        name: int(number)
        for name, number in re.findall(r"(\w+)\s*~\s*pin\s+(\d+)", match.group(0))
    }
    return [
        f"main.ato: {name} expected pin {pad}, got {found.get(name)!r}"
        for pad, name in PROJECT_BINDINGS.items()
        if found.get(name) != pad
    ]


def check_mod() -> list[str]:
    if not MOD.is_file():
        return [f"missing {MOD}"]
    text = MOD.read_text(encoding="utf-8")
    pads = {
        int(number): (float(x), float(y))
        for number, x, y in re.findall(
            r'\(pad "(\d+)"[^\n]*\(at ([-\d.]+) ([-\d.]+)', text
        )
    }
    errors: list[str] = []
    if sorted(pads) != list(range(1, 41)):
        errors.append(f"footprint pads are {sorted(pads)}, expected 1..40")
    for pad in range(1, 41):
        expected = pad_xy(pad)
        actual = pads.get(pad)
        if actual is None:
            continue
        if abs(actual[0] - expected[0]) > 0.01 or abs(actual[1] - expected[1]) > 0.01:
            errors.append(f"footprint pad {pad}={actual}, expected {expected}")
    return errors


def check_config() -> list[str]:
    text = CONFIG_H.read_text(encoding="utf-8")
    errors: list[str] = []
    for name, gpio in FIRMWARE_GPIO.items():
        match = re.search(rf"#define\s+{name}\s+GPIO_NUM_(\d+)", text)
        if not match:
            errors.append(f"config.h: missing {name}")
        elif int(match.group(1)) != gpio:
            errors.append(f"config.h: {name}=GPIO{match.group(1)}, expected GPIO{gpio}")
    return errors


def check_consumers() -> list[str]:
    status_led = STATUS_LED_CPP.read_text(encoding="utf-8")
    errors: list[str] = []
    if "strip_config.strip_gpio_num = LED_PIN;" not in status_led:
        errors.append("status_led.cpp does not consume config.h LED_PIN")
    if re.search(r"strip_gpio_num\s*=\s*\d+", status_led):
        errors.append("status_led.cpp contains a hard-coded LED GPIO")
    return errors


def check_firmware_target() -> list[str]:
    """Check the reproducible N16R8 build settings, not only generated sdkconfig."""
    errors: list[str] = []
    for path in (SDKCONFIG_DEFAULTS, SDKCONFIG):
        text = path.read_text(encoding="utf-8")
        missing = sorted(token for token in REQUIRED_S3_CONFIG if token not in text)
        if missing:
            errors.append(f"{path.name}: missing required C4 settings {missing}")
    sdkconfig_text = SDKCONFIG.read_text(encoding="utf-8")
    missing_generated = sorted(
        token for token in REQUIRED_GENERATED_CONFIG if token not in sdkconfig_text
    )
    if missing_generated:
        errors.append(
            f"sdkconfig: generated flash settings conflict with C4: {missing_generated}"
        )

    rows: dict[str, tuple[int, int]] = {}
    for raw_line in PARTITIONS.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 5:
            errors.append(f"partitions.csv: malformed row {raw_line!r}")
            continue
        name, offset, size = fields[0], fields[3], fields[4]
        try:
            rows[name] = (int(offset, 0), int(size, 0))
        except ValueError:
            errors.append(f"partitions.csv: invalid offset/size in {raw_line!r}")
    if rows != EXPECTED_PARTITIONS:
        errors.append(
            f"partitions.csv: expected N16 layout {EXPECTED_PARTITIONS}, got {rows}"
        )
    elif max(offset + size for offset, size in rows.values()) != 0x1000000:
        errors.append("partitions.csv: layout does not end at the 16 MB boundary")

    cmake = COMPONENT_CMAKE.read_text(encoding="utf-8")
    for source in ('"piezo_capture.cpp"', '"pzt_frontend.cpp"'):
        if source not in cmake:
            errors.append(f"main/CMakeLists.txt: missing {source}")
    return errors


def check_pzt_firmware() -> list[str]:
    """Prove that C4 uses DAC thresholds, GPIO edges and optional ADC peeks."""
    errors: list[str] = []
    frontend = PZT_FRONTEND_CPP.read_text(encoding="utf-8")
    for token in (
        "PZT_DAC_I2C_ADDRESS",
        "PZT_THRESHOLD_MV_TL",
        "PZT_THRESHOLD_MV_TR",
        "PZT_THRESHOLD_MV_BL",
        "PZT_THRESHOLD_MV_BR",
        "i2c_master_transmit",
    ):
        if token not in frontend:
            errors.append(f"pzt_frontend.cpp: missing {token}")

    capture = PIEZO_CAPTURE_CPP.read_text(encoding="utf-8")
    for token in (
        "GPIO_INTR_POSEDGE",
        "gpio_isr_handler_add",
        "esp_cpu_get_cycle_count",
        "#if PZT_ADC_PEEK_ENABLE",
        "adc_oneshot_read",
    ):
        if token not in capture:
            errors.append(f"piezo_capture.cpp: missing {token}")
    pins_match = re.search(
        r"PiezoCapture::PINS\[4\]\s*=\s*\{(.*?)\};", capture, re.S
    )
    expected_edge_pins = {f"PIEZO_PIN_{index}" for index in range(1, 5)}
    actual_edge_pins = (
        set(re.findall(r"(?:PIEZO|PZT_ADC)_PIN_\d", pins_match.group(1)))
        if pins_match else set()
    )
    if actual_edge_pins != expected_edge_pins:
        errors.append(
            "piezo_capture.cpp: edge inputs must be exactly comparator outputs "
            f"{sorted(expected_edge_pins)}, got {sorted(actual_edge_pins)}"
        )

    main = MAIN_CPP.read_text(encoding="utf-8")
    frontend_init = main.find("pzt_frontend::init()")
    capture_init = main.find("PiezoCapture::init()")
    if frontend_init < 0 or capture_init < 0:
        errors.append("main.cpp: missing PZT frontend/capture initialization")
    elif frontend_init > capture_init:
        errors.append("main.cpp: comparator capture starts before DAC thresholds")
    return errors


def main() -> int:
    errors: list[str] = []
    if ORIENTATION["view"] != "top_component_side":
        errors.append("pinmap orientation must be top_component_side")
    errors.extend(check_ato())
    errors.extend(check_mod())
    errors.extend(check_config())
    errors.extend(check_consumers())
    errors.extend(check_firmware_target())
    errors.extend(check_pzt_firmware())
    if "esp32s3wroom1" not in STEP3.read_text(encoding="utf-8"):
        errors.append("step3_import_netlist.py does not import the C4 S3 pin map")
    if errors:
        print("ESP32-S3-WROOM-1 C4 pin-map validation failed:")
        for error in errors:
            print(f"  x {error}")
        return 1
    print(
        "ESP32-S3-WROOM-1 C4 OK: ato / footprint / pin map / importer; "
        "ESP-IDF target, N16 partition map, octal PSRAM and PZT firmware"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
