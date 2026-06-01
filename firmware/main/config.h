#pragma once
#include <cstdint>

// --- Piezo TDOA sensor pins ---
// 4 piezo discs on blade corners, each through zener clamp → GPIO → RMT
#define PIEZO_PIN_1 GPIO_NUM_4   // Top-left blade corner
#define PIEZO_PIN_2 GPIO_NUM_5   // Top-right blade corner
#define PIEZO_PIN_3 GPIO_NUM_6   // Bottom-left blade corner
#define PIEZO_PIN_4 GPIO_NUM_7   // Bottom-right blade corner

// --- RMT config ---
#define RMT_CLK_DIV 1            // 80MHz APB / 1 = 80MHz = 12.5ns resolution
#define RMT_MAX_EDGES 256        // Max edges captured per trigger window

// --- IMU pins (ICM-42688-P, SPI2) ---
#define IMU_SCLK    GPIO_NUM_12
#define IMU_MOSI    GPIO_NUM_11
#define IMU_MISO    GPIO_NUM_13
#define IMU_CS      GPIO_NUM_10
#define IMU_INT     GPIO_NUM_14  // FIFO watermark interrupt

// --- WiFi defaults (override via WebSocket config later) ---
#define WIFI_SSID_DEFAULT   "SmartPaddle"
#define WIFI_PASS_DEFAULT   "paddle123"

// --- WebSocket server ---
#define WS_SERVER_HOST      "192.168.4.1"  // Default: phone hotspot or local server
#define WS_SERVER_PORT      8000
#define WS_PATH             "/ws/paddle"

// --- Timing ---
// Shared microsecond timer: esp_timer_get_time() used for both IMU and piezo timestamps
#define IMU_SAMPLE_RATE_HZ  1000
#define IMU_FIFO_WATERMARK  8     // Read FIFO every 8 samples (8ms)

// --- Ring buffer ---
#define RING_BUF_SIZE       65536  // ~27 seconds at 1kHz IMU + impact events

// --- LED ---
#define LED_PIN GPIO_NUM_8  // WS2812C RGB LED
