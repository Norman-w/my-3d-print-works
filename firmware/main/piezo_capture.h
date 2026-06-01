#pragma once
#include <cstdint>
#include "driver/rmt.h"
#include "driver/gpio.h"
#include "esp_timer.h"

struct PiezoEvent {
    uint32_t channel;          // 0-3: which piezo triggered
    uint64_t timestamp_us;     // esp_timer_get_time() at first edge
    uint32_t edge_count;       // number of edges captured in window
};

class PiezoCapture {
public:
    // Initialize 4 RMT channels for piezo edge capture
    // Each channel captures on posedge, 80MHz resolution, 256-edge buffer
    static esp_err_t init();

    // Block until an impact event is detected on any channel.
    // Returns the first channel to trigger and its timestamp.
    // "Impact" = any channel sees a positive edge (piezo voltage crosses GPIO threshold)
    static esp_err_t wait_for_impact(PiezoEvent& event, uint32_t timeout_ms = 0);

    // Non-blocking: check if any impact events are queued
    static bool has_pending_event();

    // Read all pending events into buffer, returns count
    static size_t drain_events(PiezoEvent* buf, size_t max_count);

    // For raw capture: start all 4 RMT channels listening
    static esp_err_t start_capture();

    // Stop all channels, read raw RMT data for debugging
    static esp_err_t read_raw(rmt_item32_t* items[4], size_t* counts);

private:
    static const rmt_channel_t CHANNELS[4];
    static const gpio_num_t PINS[4];
    static bool initialized;
};
