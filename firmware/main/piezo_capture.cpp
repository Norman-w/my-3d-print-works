#include "piezo_capture.h"

#include "config.h"
#include "esp_cpu.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "sdkconfig.h"

#include <atomic>
#include <cinttypes>

// ===== 分区：常量/配置 =====

static const char* TAG = "piezo";

static constexpr uint32_t kChannelCount = 4;
static constexpr uint32_t kAllArmedMask = (1u << kChannelCount) - 1u;
static constexpr int kCpuMhz =
#if defined(CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ)
    CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ;
#else
    160;
#endif

// ===== 分区：私有成员 =====

static QueueHandle_t s_event_queue = nullptr;
static std::atomic<uint32_t> s_armed_mask{kAllArmedMask};
static std::atomic<uint32_t> s_edge_counts[kChannelCount];

const gpio_num_t PiezoCapture::PINS[4] = {
    PIEZO_PIN_1,
    PIEZO_PIN_2,
    PIEZO_PIN_3,
    PIEZO_PIN_4,
};

bool PiezoCapture::initialized = false;

static void IRAM_ATTR piezo_gpio_isr(void* arg) {
    const uint32_t channel = static_cast<uint32_t>(reinterpret_cast<uintptr_t>(arg));
    if (channel >= kChannelCount) {
        return;
    }

    const uint32_t bit = 1u << channel;
    uint32_t armed = s_armed_mask.load(std::memory_order_relaxed);
    if ((armed & bit) == 0) {
        s_edge_counts[channel].fetch_add(1, std::memory_order_relaxed);
        return;
    }

    // 仅首边沿入队；后续边沿只计数，直到 start_capture 重新武装
    while (!s_armed_mask.compare_exchange_weak(
            armed, armed & ~bit, std::memory_order_relaxed)) {
        if ((armed & bit) == 0) {
            s_edge_counts[channel].fetch_add(1, std::memory_order_relaxed);
            return;
        }
    }

    PiezoEvent event = {};
    event.channel = channel;
    event.timestamp_cycles = esp_cpu_get_cycle_count();
    event.timestamp_us = esp_timer_get_time();
    event.edge_count = 1;
    s_edge_counts[channel].store(1, std::memory_order_relaxed);

    BaseType_t higher_priority_woken = pdFALSE;
    xQueueSendFromISR(s_event_queue, &event, &higher_priority_woken);
    if (higher_priority_woken == pdTRUE) {
        portYIELD_FROM_ISR();
    }
}

// ===== 分区：公开 API =====

esp_err_t PiezoCapture::init() {
    if (initialized) {
        return ESP_OK;
    }

    s_event_queue = xQueueCreate(32, sizeof(PiezoEvent));
    if (!s_event_queue) {
        ESP_LOGE(TAG, "Failed to create event queue");
        return ESP_ERR_NO_MEM;
    }

    for (uint32_t i = 0; i < kChannelCount; ++i) {
        s_edge_counts[i].store(0, std::memory_order_relaxed);
    }
    s_armed_mask.store(kAllArmedMask, std::memory_order_relaxed);

    uint64_t pin_mask = 0;
    for (uint32_t i = 0; i < kChannelCount; ++i) {
        pin_mask |= (1ULL << PINS[i]);
    }

    gpio_config_t io_conf = {};
    io_conf.pin_bit_mask = pin_mask;
    io_conf.mode = GPIO_MODE_INPUT;
    io_conf.pull_up_en = GPIO_PULLUP_DISABLE;
    io_conf.pull_down_en = GPIO_PULLDOWN_ENABLE;
    io_conf.intr_type = GPIO_INTR_POSEDGE;
    esp_err_t err = gpio_config(&io_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "gpio_config failed: %s", esp_err_to_name(err));
        return err;
    }

    // 其他模块可能已安装 ISR 服务；先确保服务存在再挂 handler
    err = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "gpio_install_isr_service failed: %s", esp_err_to_name(err));
        return err;
    }
    for (uint32_t i = 0; i < kChannelCount; ++i) {
        err = gpio_isr_handler_add(
            PINS[i], piezo_gpio_isr, reinterpret_cast<void*>(static_cast<uintptr_t>(i)));
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "gpio_isr_handler_add ch%" PRIu32 " failed: %s", i,
                     esp_err_to_name(err));
            return err;
        }
    }

    initialized = true;
    ESP_LOGI(TAG,
             "Piezo capture ready: 4 GPIO channels, CPU cycle TDOA (~%dns @ %dMHz)",
             1000 / kCpuMhz, kCpuMhz);
    return ESP_OK;
}

esp_err_t PiezoCapture::start_capture() {
    for (uint32_t i = 0; i < kChannelCount; ++i) {
        s_edge_counts[i].store(0, std::memory_order_relaxed);
    }
    s_armed_mask.store(kAllArmedMask, std::memory_order_relaxed);
    return ESP_OK;
}

esp_err_t PiezoCapture::wait_for_impact(PiezoEvent& event, uint32_t timeout_ms) {
    if (!s_event_queue) {
        return ESP_ERR_INVALID_STATE;
    }
    TickType_t ticks = (timeout_ms == 0) ? portMAX_DELAY : pdMS_TO_TICKS(timeout_ms);
    if (xQueueReceive(s_event_queue, &event, ticks) == pdTRUE) {
        event.edge_count = s_edge_counts[event.channel].load(std::memory_order_relaxed);
        return ESP_OK;
    }
    return ESP_ERR_TIMEOUT;
}

bool PiezoCapture::has_pending_event() {
    return s_event_queue && uxQueueMessagesWaiting(s_event_queue) > 0;
}

size_t PiezoCapture::drain_events(PiezoEvent* buf, size_t max_count) {
    size_t count = 0;
    while (count < max_count && xQueueReceive(s_event_queue, &buf[count], 0) == pdTRUE) {
        buf[count].edge_count =
            s_edge_counts[buf[count].channel].load(std::memory_order_relaxed);
        ++count;
    }
    return count;
}

int64_t PiezoCapture::delta_ns(uint64_t cycles_a, uint64_t cycles_b) {
    const int64_t delta_cycles = static_cast<int64_t>(cycles_a - cycles_b);
    return (delta_cycles * 1000) / kCpuMhz;
}
