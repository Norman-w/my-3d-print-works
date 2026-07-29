#include "piezo_capture.h"

#include "config.h"
#include "esp_adc/adc_oneshot.h"
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
static std::atomic<uint32_t> s_edge_total[kChannelCount];

#if PZT_ADC_PEEK_ENABLE
static adc_oneshot_unit_handle_t s_adc = nullptr;
static adc_channel_t s_adc_ch[4] = {};
#endif
static bool s_adc_ch_ok[4] = {};
static int s_peak_mv[4] = {};
static constexpr gpio_num_t kAdcPins[kChannelCount] = {
    PZT_ADC_PIN_1,
    PZT_ADC_PIN_2,
    PZT_ADC_PIN_3,
    PZT_ADC_PIN_4,
};

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

    s_edge_total[channel].fetch_add(1, std::memory_order_relaxed);

    const uint32_t bit = 1u << channel;
    uint32_t armed = s_armed_mask.load(std::memory_order_relaxed);
    if ((armed & bit) == 0) {
        s_edge_counts[channel].fetch_add(1, std::memory_order_relaxed);
        return;
    }

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

static void init_adc_diag() {
#if !PZT_ADC_PEEK_ENABLE
    ESP_LOGI(TAG, "ADC peeks disabled; leave JP_ADC_TL/TR/BL/BR DNP");
    return;
#else
    if (s_adc) {
        return;
    }

    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = ADC_UNIT_1,
    };
    if (adc_oneshot_new_unit(&unit_cfg, &s_adc) != ESP_OK) {
        ESP_LOGW(TAG, "ADC oneshot init failed（仅影响峰值诊断）");
        s_adc = nullptr;
        return;
    }

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    for (uint32_t i = 0; i < kChannelCount; ++i) {
        adc_unit_t unit = ADC_UNIT_1;
        adc_channel_t ch = ADC_CHANNEL_0;
        const gpio_num_t pin = kAdcPins[i];
        if (adc_oneshot_io_to_channel(static_cast<int>(pin), &unit, &ch) != ESP_OK) {
            ESP_LOGW(TAG, "ADC peek ch%" PRIu32 " GPIO%d has no ADC channel", i,
                     static_cast<int>(pin));
            continue;
        }
        if (unit != ADC_UNIT_1) {
            ESP_LOGW(TAG, "ADC peek ch%" PRIu32 " GPIO%d is not ADC1", i,
                     static_cast<int>(pin));
            continue;
        }
        if (adc_oneshot_config_channel(s_adc, ch, &chan_cfg) != ESP_OK) {
            continue;
        }
        s_adc_ch[i] = ch;
        s_adc_ch_ok[i] = true;
    }
    ESP_LOGI(TAG, "ADC peeks: TL=IO%d TR=IO%d BL=IO%d BR=IO%d",
             static_cast<int>(kAdcPins[0]), static_cast<int>(kAdcPins[1]),
             static_cast<int>(kAdcPins[2]), static_cast<int>(kAdcPins[3]));
#endif
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
        s_edge_total[i].store(0, std::memory_order_relaxed);
        s_peak_mv[i] = 0;
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
    io_conf.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io_conf.intr_type = GPIO_INTR_POSEDGE;
    esp_err_t err = gpio_config(&io_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "gpio_config failed: %s", esp_err_to_name(err));
        return err;
    }

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
        gpio_intr_enable(PINS[i]);
    }

    init_adc_diag();

    initialized = true;
    ESP_LOGI(TAG,
             "Comparator edges ready: TL=IO%d TR=IO%d BL=IO%d BR=IO%d POSEDGE (~%dns)",
             static_cast<int>(PINS[0]), static_cast<int>(PINS[1]),
             static_cast<int>(PINS[2]), static_cast<int>(PINS[3]),
             1000 / kCpuMhz);
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

void PiezoCapture::sample_adc_peaks() {
#if PZT_ADC_PEEK_ENABLE
    if (!s_adc) {
        return;
    }
    for (uint32_t i = 0; i < kChannelCount; ++i) {
        if (!s_adc_ch_ok[i]) {
            continue;
        }
        for (int n = 0; n < 40; ++n) {
            int raw = 0;
            if (adc_oneshot_read(s_adc, s_adc_ch[i], &raw) != ESP_OK) {
                continue;
            }
            const int mv = (raw * 3300) / 4095;
            if (mv > s_peak_mv[i]) {
                s_peak_mv[i] = mv;
            }
        }
    }
#endif
}

void PiezoCapture::log_diag() {
    static const char* kName[4] = {"TL", "TR", "BL", "BR"};
    printf("PZT diag armed=0x%X |", (unsigned)s_armed_mask.load());
    for (uint32_t i = 0; i < kChannelCount; ++i) {
        const int level = gpio_get_level(PINS[i]);
        const uint32_t total = s_edge_total[i].load(std::memory_order_relaxed);
        printf(" %s(IO%d)=%d edges=%" PRIu32, kName[i], static_cast<int>(PINS[i]),
               level, total);
        if (PZT_ADC_PEEK_ENABLE && s_adc_ch_ok[i]) {
            printf(" peak=%dmV", s_peak_mv[i]);
        } else {
            printf(" peak=off");
        }
    }
    printf("\n");
    for (uint32_t i = 0; i < kChannelCount; ++i) {
        s_peak_mv[i] = 0;
    }
}
