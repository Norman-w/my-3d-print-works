#include "piezo_capture.h"
#include "config.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

static const char* TAG = "piezo";

// Queue for impact events from ISR to main task
static QueueHandle_t event_queue = nullptr;

// --- RMT ISR ---
// Fires when any channel's RX buffer is half-full or done.
// We read the first edge timestamp and push a PiezoEvent.

static bool IRAM_ATTR rmt_isr_handler(rmt_channel_t channel, const rmt_item32_t* items, size_t item_num, void* arg) {
    if (item_num == 0) return false;

    uint32_t channel_idx = (uint32_t)(uintptr_t)arg;

    // Find the first positive edge
    uint32_t first_edge_duration = 0;
    for (size_t i = 0; i < item_num; i++) {
        if (items[i].level0 == 1) {  // Positive edge detected
            first_edge_duration = items[i].duration0;
            break;
        }
        if (items[i].level1 == 1) {
            first_edge_duration = items[i].duration0 + items[i].duration1;
            break;
        }
    }

    PiezoEvent event;
    event.channel = channel_idx;
    event.timestamp_us = esp_timer_get_time();
    event.edge_count = (uint32_t)item_num;

    // Non-blocking send from ISR
    BaseType_t higher_priority_woken = pdFALSE;
    xQueueSendFromISR(event_queue, &event, &higher_priority_woken);
    return higher_priority_woken == pdTRUE;
}

const rmt_channel_t PiezoCapture::CHANNELS[4] = {
    RMT_CHANNEL_0,
    RMT_CHANNEL_1,
    RMT_CHANNEL_2,
    RMT_CHANNEL_3,
};

const gpio_num_t PiezoCapture::PINS[4] = {
    PIEZO_PIN_1,
    PIEZO_PIN_2,
    PIEZO_PIN_3,
    PIEZO_PIN_4,
};

bool PiezoCapture::initialized = false;

esp_err_t PiezoCapture::init() {
    if (initialized) return ESP_OK;

    event_queue = xQueueCreate(32, sizeof(PiezoEvent));
    if (!event_queue) {
        ESP_LOGE(TAG, "Failed to create event queue");
        return ESP_ERR_NO_MEM;
    }

    // Install RMT driver for RX on all 4 channels
    rmt_config_t config;
    config.rmt_mode = RMT_MODE_RX;
    config.channel = RMT_CHANNEL_0;  // We'll re-configure per channel
    config.clk_div = RMT_CLK_DIV;
    config.gpio_num = PINS[0];
    config.mem_block_num = 2;  // 2 blocks × 64 entries = 128 entries
    config.rx_config.idle_threshold = 12000;  // 12k × 12.5ns = 150µs timeout
    config.rx_config.filter_ticks_thresh = 8;  // Filter pulses < 100ns
    config.rx_config.filter_en = true;

    for (int i = 0; i < 4; i++) {
        config.channel = CHANNELS[i];
        config.gpio_num = PINS[i];
        esp_err_t err = rmt_config(&config);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "RMT config failed for channel %d: %d", i, err);
            return err;
        }
        err = rmt_driver_install(CHANNELS[i], 512, 0);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "RMT driver install failed for channel %d: %d", i, err);
            return err;
        }
        err = rmt_set_rx_intr_en(CHANNELS[i], true);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "RMT interrupt enable failed for channel %d: %d", i, err);
            return err;
        }
    }

    // Register ISR to catch first edge per channel
    // Note: RMT RX ISR is shared; we register per-channel context via arg
    for (int i = 0; i < 4; i++) {
        rmt_rx_start(CHANNELS[i], true);
        // Poll-based approach is simpler for Phase 0;
        // ISR-based refinement comes in Phase 1
    }

    initialized = true;
    ESP_LOGI(TAG, "Piezo capture initialized: 4 channels, 80MHz, 12.5ns resolution");
    return ESP_OK;
}

esp_err_t PiezoCapture::start_capture() {
    for (int i = 0; i < 4; i++) {
        rmt_rx_start(CHANNELS[i], true);
    }
    return ESP_OK;
}

esp_err_t PiezoCapture::wait_for_impact(PiezoEvent& event, uint32_t timeout_ms) {
    TickType_t ticks = (timeout_ms == 0) ? portMAX_DELAY : pdMS_TO_TICKS(timeout_ms);
    if (xQueueReceive(event_queue, &event, ticks) == pdTRUE) {
        return ESP_OK;
    }
    return ESP_ERR_TIMEOUT;
}

bool PiezoCapture::has_pending_event() {
    return uxQueueMessagesWaiting(event_queue) > 0;
}

size_t PiezoCapture::drain_events(PiezoEvent* buf, size_t max_count) {
    size_t count = 0;
    while (count < max_count && xQueueReceive(event_queue, &buf[count], 0) == pdTRUE) {
        count++;
    }
    return count;
}

esp_err_t PiezoCapture::read_raw(rmt_item32_t* items[4], size_t* counts) {
    for (int i = 0; i < 4; i++) {
        size_t rx_size = 256;
        esp_err_t err = rmt_get_ringbuf_handle(CHANNELS[i], nullptr);
        if (err != ESP_OK) {
            counts[i] = 0;
            continue;
        }

        // Read available items from ring buffer
        // rmt_get_ringbuf_handle gets the handle; then use ring buffer peek
        // For Phase 0, we read via the ISR queue instead of raw RMT data
        counts[i] = 0;
    }
    return ESP_OK;
}
