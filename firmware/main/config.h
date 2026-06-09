#pragma once
#include <cstdint>

// --- Piezo TDOA sensor pins ---
// 4 piezo discs on blade corners, each through zener clamp → GPIO → RMT
// GPIO4/5 被 IMU UART1 占用，压电传感器迁至 GPIO2/3
#define PIEZO_PIN_1 GPIO_NUM_2   // Top-left blade corner
#define PIEZO_PIN_2 GPIO_NUM_3   // Top-right blade corner
#define PIEZO_PIN_3 GPIO_NUM_6   // Bottom-left blade corner
#define PIEZO_PIN_4 GPIO_NUM_7   // Bottom-right blade corner

// --- RMT config ---
#define RMT_CLK_DIV 1            // 80MHz APB / 1 = 80MHz = 12.5ns resolution
#define RMT_MAX_EDGES 256        // Max edges captured per trigger window

// --- IMU pins (IM948, UART1) ---
#define IMU_UART_NUM   UART_NUM_1
#define IMU_UART_TX    GPIO_NUM_4
#define IMU_UART_RX    GPIO_NUM_5
#define IMU_UART_BAUD  115200       // 初始波特率，上电后升级到 230400
#define IMU_UART_BAUD_HIGH 230400   // 升级后的波特率

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
