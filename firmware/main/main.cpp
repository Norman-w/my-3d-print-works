#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "piezo_capture.h"
#include "config.h"

static const char* TAG = "main";

// Phase 0: Serial-only TDOA data logger.
// Captures piezo impact events and prints raw timing data to serial.
// Format: "IMPACT,<ch>,<ts_us>,<edge_count>\n" for each channel that fires.

extern "C" void app_main() {
    // Init NVS (needed for WiFi later, harmless now)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    ESP_LOGI(TAG, "SmartPaddle Phase 0 - Piezo TDOA Capture");
    ESP_LOGI(TAG, "RMT resolution: 12.5ns @ 80MHz APB");

    // Init piezo capture
    ret = PiezoCapture::init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "PiezoCapture init failed: %d", ret);
        return;
    }

    ESP_LOGI(TAG, "Waiting for impacts. Tap the blade to see TDOA data...");
    ESP_LOGI(TAG, "Format: IMPACT,<ch>,<ts_us>,<edges>");

    // --- Phase 0 loop: wait for impact, dump all related events ---
    while (true) {
        PiezoEvent first;
        ret = PiezoCapture::wait_for_impact(first, portMAX_DELAY);
        if (ret != ESP_OK) continue;

        // Collect all events that arrive within a 10ms window (impact wave propagation)
        uint64_t window_start = first.timestamp_us;
        uint64_t window_end = window_start + 10000;  // 10ms window

        PiezoEvent batch[16];
        size_t count = 1;
        batch[0] = first;

        // Drain any already-queued events
        PiezoEvent pending[16];
        size_t pending_count = PiezoCapture::drain_events(pending, 16);
        for (size_t i = 0; i < pending_count && count < 16; i++) {
            if (pending[i].timestamp_us <= window_end) {
                batch[count++] = pending[i];
            }
        }

        // Print TDOA data: channel, timestamp, edge count
        printf("=== IMPACT === ts_base=%llu\n", window_start);
        for (size_t i = 0; i < count; i++) {
            printf("  ch%u: ts=%llu (+%llu ns) edges=%u\n",
                batch[i].channel,
                batch[i].timestamp_us,
                (batch[i].timestamp_us - window_start) * 1000,  // us → ns
                batch[i].edge_count);
        }

        // TDOA calculation (relative to first channel, in nanoseconds)
        if (count >= 2) {
            printf("  TDOA (ns):");
            for (size_t i = 1; i < count; i++) {
                int64_t diff = (int64_t)(batch[i].timestamp_us - batch[0].timestamp_us) * 1000;
                if (batch[i].channel != batch[0].channel) {
                    printf(" ch%u=%+lld", batch[i].channel, diff);
                }
            }
            printf("\n");
        }

        // Re-arm capture
        PiezoCapture::start_capture();
    }
}
