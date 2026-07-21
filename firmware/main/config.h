#pragma once
#include <cstdint>

// --- Piezo TDOA sensor pins ---
// 4 piezo discs on blade corners, each through clamp → GPIO
// ESP32-C6 仅 2 路 RMT RX，4 通道用 GPIO ISR + CPU cycle 锁存
// 实物：拍柄侧 GND/3V3/EN/IO4…；对侧 IO2/IO3。
// IMU UART1 → IO4/IO5（贴 IMU）；PZT TL/TR → IO2/IO3；BL/BR → IO6/IO7
#define PIEZO_PIN_1 GPIO_NUM_2   // Top-left blade corner
#define PIEZO_PIN_2 GPIO_NUM_3   // Top-right blade corner
#define PIEZO_PIN_3 GPIO_NUM_6   // Bottom-left blade corner
#define PIEZO_PIN_4 GPIO_NUM_7   // Bottom-right blade corner

// --- IMU pins (IM948, UART1) ---
#define IMU_UART_NUM   UART_NUM_1
#define IMU_UART_TX    GPIO_NUM_4
#define IMU_UART_RX    GPIO_NUM_5
#define IMU_UART_BAUD  115200       // 初始波特率，上电后升级到 230400
#define IMU_UART_BAUD_HIGH 230400   // 升级后的波特率
// 诊断：1=跳过 init_imu / imu_task（排查 rst:0x1 @ GPIO4/5）；确认后改回 0
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
#define IMU_REPORT_HZ       250    // IM948 主动上报频率
#define IMU_RX_BUF_SIZE     4096   // UART 接收缓冲区

// --- Ring buffer ---
#define RING_BUF_SIZE       65536  // 通用环缓冲区

// --- LED ---
#define LED_PIN GPIO_NUM_8  // WS2812C RGB LED

// --- 电源自锁 + 尾部用户键（ESP32-C6-WROOM-1）---
// pad 11 = GPIO10 → PWR_LATCH（高电平保持开机）
// pad 16 = GPIO18 → 尾键读回（经 1k，MCU 内部上拉）
#define PWR_LATCH_GPIO       GPIO_NUM_10
#define USER_BTN_GPIO        GPIO_NUM_18
#define USER_BTN_ACTIVE_LEVEL 0
#define POWER_OFF_HOLD_MS    2000

// BOOT 键（pad 15 = GPIO9）仍用于工程恢复出厂等，见 reset_button.cpp
#define BOOT_BTN_GPIO        GPIO_NUM_9
