#pragma once

#include <cstddef>
#include <cstdint>

#include "driver/gpio.h"
#include "esp_err.h"

// ===== 分区：模型/类型 =====

struct PiezoEvent {
    uint32_t channel;           // 0-3
    uint64_t timestamp_us;      // esp_timer 墙钟（µs），用于窗口归并
    uint64_t timestamp_cycles;  // CPU cycle，用于通道间 TDOA
    uint32_t edge_count;        // 本窗口该通道累计边沿数（首边沿事件为 1）
};

// ===== 分区：公开 API =====

class PiezoCapture {
public:
    // C5 listens to four TLV9034 push-pull outputs. GPIO rising-edge ISR +
    // CPU cycle timestamps remain the production TDOA source.
    static esp_err_t init();

    static esp_err_t wait_for_impact(PiezoEvent& event, uint32_t timeout_ms = 0);
    static bool has_pending_event();
    static size_t drain_events(PiezoEvent* buf, size_t max_count);

    // 重新武装 4 路：允许下一击的首边沿入队
    static esp_err_t start_capture();

    // 将两事件的 cycle 差转为纳秒（相对 TDOA）
    static int64_t delta_ns(uint64_t cycles_a, uint64_t cycles_b);

    /** 诊断：累计边沿 + 当前 GPIO 电平（敲击排查用） */
    static void log_diag();

    /** Sample four dedicated ADC peeks when PZT_ADC_PEEK_ENABLE=1. */
    static void sample_adc_peaks();

private:
    static const gpio_num_t PINS[4];
    static bool initialized;
};
