#pragma once
#include <cstdint>

// --- C4 ESP32-S3-WROOM-1-N16R8 pin map ---
// Truth source: pcb/lib/esp32s3wroom1/pinmap.py (top view, antenna -X).
// GPIO35..37 are reserved by octal PSRAM. GPIO0/3/45/46 are straps; only
// GPIO0 is used, exclusively for the BOOT switch.

// --- Piezo comparator edges (TLV1814 push-pull outputs) ---
#define PIEZO_PIN_1 GPIO_NUM_16  // Top-left; TLV1814 channel 2
#define PIEZO_PIN_2 GPIO_NUM_15  // Top-right; TLV1814 channel 1
#define PIEZO_PIN_3 GPIO_NUM_6   // Bottom-left blade corner
#define PIEZO_PIN_4 GPIO_NUM_7   // Bottom-right blade corner

// Optional high-impedance ADC peeks. Fit the matching JP_ADC_* 0R and set
// PZT_ADC_PEEK_ENABLE=1 for diagnostics; leave all jumpers DNP in production.
#define PZT_ADC_PIN_1 GPIO_NUM_1
#define PZT_ADC_PIN_2 GPIO_NUM_2
#define PZT_ADC_PIN_3 GPIO_NUM_4
#define PZT_ADC_PIN_4 GPIO_NUM_8
#define PZT_ADC_PEEK_ENABLE 0

// MCP4728 programmable thresholds (internal 2.048V reference, gain x1).
#define PZT_I2C_SDA GPIO_NUM_17
#define PZT_I2C_SCL GPIO_NUM_18
#define PZT_DAC_I2C_ADDRESS 0x60
#define PZT_THRESHOLD_MV_TL 220
#define PZT_THRESHOLD_MV_TR 220
#define PZT_THRESHOLD_MV_BL 220
#define PZT_THRESHOLD_MV_BR 220

// --- IMU pins (IM948, UART1) ---
#define IMU_UART_NUM   UART_NUM_1
#define IMU_UART_TX    GPIO_NUM_41  // pad 34 → IMU RXD
#define IMU_UART_RX    GPIO_NUM_40  // pad 33 ← IMU TXD
#define IMU_UART_BAUD  115200       // 固定 115200（升 230400 会在软复位后错位）
#define IMU_UART_BAUD_HIGH 230400   // 保留常量；当前固件不再自动升级
// 诊断：1=跳过 init_imu / imu_task；确认后改回 0
#define SKIP_IMU_INIT  0
// 诊断：串口打印 IMU 姿态（0=关；1=开）。IMU 未修好前保持关闭，避免刷屏；PZT 敲击日志不受影响
#define IMU_UART_LOG_ENABLE 0
// 开启后的打印频率（Hz）；仅当 IMU_UART_LOG_ENABLE=1 时生效
#define IMU_UART_REPORT_HZ  5

// --- WiFi defaults (override via WebSocket config later) ---
#define WIFI_SSID_DEFAULT   "SmartPaddle"
#define WIFI_PASS_DEFAULT   "paddle123"

// --- WebSocket server ---
#define WS_SERVER_HOST      "192.168.4.1"  // Default: phone hotspot or local server
#define WS_SERVER_PORT      8000
#define WS_PATH             "/ws/paddle"

// --- IM948 Timing ---
#define IMU_REPORT_HZ       100    // 115200 + 精简订阅；TAG_ALL@250 需 230400
#define IMU_RX_BUF_SIZE     4096   // UART 接收缓冲区

// --- Ring buffer ---
#define RING_BUF_SIZE       65536  // 通用环缓冲区

// --- LED ---
#define LED_PIN GPIO_NUM_21  // WS2812C RGB LED

// Battery divider (BAT_CELL_P / 2) is also wired to IM948 ADIN.
#define BAT_SENSE_GPIO GPIO_NUM_9

// --- 电源自锁 + 唯一用户键 SW_PWR（ESP32-S3-WROOM-1）---
// pad 24 = GPIO47 → PWR_LATCH（高电平保持开机）
// pad 25 = GPIO48 → SW_PWR 读回（经 1k，MCU 内部上拉）
// 产品只暴露 SW_PWR：长按关机；短按后再长按 → 恢复出厂（见 power_control）
// SW_BOOT(GPIO0/pad27) 与 SW_EN 仅维护烧录/复位，固件不监测
#define PWR_LATCH_GPIO              GPIO_NUM_47
#define USER_BTN_GPIO               GPIO_NUM_48
#define USER_BTN_ACTIVE_LEVEL       0
#define POWER_OFF_HOLD_MS           2000
#define FACTORY_RESET_SHORT_MAX_MS  500
#define FACTORY_RESET_HOLD_MS       10000
#define FACTORY_RESET_COMBO_WINDOW_MS 3000

#define BOOT_BTN_GPIO        GPIO_NUM_0  // 硬件下载模式脚；勿当用户键
