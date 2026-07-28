#pragma once
#include <cstdint>

// --- Piezo TDOA sensor pins ---
// 4 piezo discs on blade corners, each through clamp → GPIO
// ESP32-C6 仅 2 路 RMT RX，4 通道用 GPIO ISR + CPU cycle 锁存
// 脚位真理源：pcb/lib/esp32c6n8/pinmap.py（顶视/元件面、天线 −X）
// 拍柄(+Y)=pad1–14=GND/3V3/EN/IO4…；拍头/IMU(−Y)=pad15–28=IO9…IO2/UART0
// IMU UART1 → IO23/IO22（pad21/20，面对面平行交叉）；PZT TL/TR → IO2/IO3；BL/BR → IO6/IO7
#define PIEZO_PIN_1 GPIO_NUM_2   // Top-left blade corner
#define PIEZO_PIN_2 GPIO_NUM_3   // Top-right blade corner
#define PIEZO_PIN_3 GPIO_NUM_6   // Bottom-left blade corner
#define PIEZO_PIN_4 GPIO_NUM_7   // Bottom-right blade corner

// --- IMU pins (IM948, UART1) ---
#define IMU_UART_NUM   UART_NUM_1
#define IMU_UART_TX    GPIO_NUM_23  // pad 21 → IMU RXD
#define IMU_UART_RX    GPIO_NUM_22  // pad 20 ← IMU TXD
#define IMU_UART_BAUD  115200       // 固定 115200（升 230400 会在软复位后错位）
#define IMU_UART_BAUD_HIGH 230400   // 保留常量；当前固件不再自动升级
// 诊断：1=跳过 init_imu / imu_task；确认后改回 0
#define SKIP_IMU_INIT  0
// 诊断：UART 低频打印 IMU（0=关；5≈每 200ms 一行，便于串口观察姿态）
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
#define LED_PIN GPIO_NUM_8  // WS2812C RGB LED

// --- 电源自锁 + 唯一用户键 SW_PWR（ESP32-C6-WROOM-1）---
// pad 11 = GPIO10 → PWR_LATCH（高电平保持开机）
// pad 16 = GPIO18 → SW_PWR 读回（经 1k，MCU 内部上拉）
// 产品只暴露 SW_PWR：长按关机；短按后再长按 → 恢复出厂（见 power_control）
// SW_BOOT(GPIO9/pad15) 与 SW_EN 仅维护烧录/复位，固件不监测
#define PWR_LATCH_GPIO              GPIO_NUM_10
#define USER_BTN_GPIO               GPIO_NUM_18
#define USER_BTN_ACTIVE_LEVEL       0
#define POWER_OFF_HOLD_MS           2000
#define FACTORY_RESET_SHORT_MAX_MS  500
#define FACTORY_RESET_HOLD_MS       10000
#define FACTORY_RESET_COMBO_WINDOW_MS 3000

#define BOOT_BTN_GPIO        GPIO_NUM_9  // 硬件下载模式脚；勿当用户键
